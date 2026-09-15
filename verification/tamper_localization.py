"""
Block-level tamper localization.

The hash + signature check already tells you *whether* a file differs
from what was issued. This module tells you *where*: it splits the
protected image into a grid of blocks, fingerprints each block at
protect/transfer time (stored in the manifest), and at verification time
recomputes the same fingerprints and flags any block whose fingerprint
drifted past a tolerance.

This is a semi-fragile, perceptual check (block mean/std + a few low
frequency DCT coefficients) rather than a bit-exact hash of pixels, so it
tolerates the watermark embedding itself (which is applied before the
baseline fingerprint is captured) and very light re-encoding noise, while
still catching localized edits (splicing, blur/paint patches, text
overlays, redaction blocks, etc.).
"""

import cv2
import numpy as np


DEFAULT_BLOCK_SIZE = 16
DEFAULT_THRESHOLD = 6.0  # tolerance on the descriptor distance


def _block_descriptor(block):
    """Cheap perceptual fingerprint for one block: mean, std, and the two
    lowest-frequency (non-DC) DCT coefficients, rounded for stability."""
    block_f = block.astype(np.float32)
    mean = float(np.mean(block_f))
    std = float(np.std(block_f))
    dct = cv2.dct(block_f)
    low_freq_a = float(dct[0, 1])
    low_freq_b = float(dct[1, 0])
    return [round(mean, 2), round(std, 2), round(low_freq_a, 2), round(low_freq_b, 2)]


def compute_block_grid(image_path_or_array, block_size=DEFAULT_BLOCK_SIZE):
    """Return (descriptors, rows, cols) for an image split into block_size blocks.
    Accepts either a path or an already-loaded grayscale numpy array."""
    if isinstance(image_path_or_array, np.ndarray):
        image = image_path_or_array
    else:
        image = cv2.imread(str(image_path_or_array), cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise FileNotFoundError(f"Unable to read image: {image_path_or_array}")

    height, width = image.shape
    rows = height // block_size
    cols = width // block_size
    descriptors = []
    for row in range(rows):
        for col in range(cols):
            y0, x0 = row * block_size, col * block_size
            block = image[y0 : y0 + block_size, x0 : x0 + block_size]
            descriptors.append(_block_descriptor(block))
    return descriptors, rows, cols


def attach_block_descriptors(manifest, protected_file, block_size=DEFAULT_BLOCK_SIZE):
    """Compute and store the baseline block fingerprints in the manifest."""
    descriptors, rows, cols = compute_block_grid(protected_file, block_size)
    manifest["tamper_grid"] = {
        "block_size": block_size,
        "rows": rows,
        "cols": cols,
        "descriptors": descriptors,
    }
    return manifest


def _block_label(row, col):
    # Matches the "B6, B7" style used in the project's forensic report:
    # row-col so blocks are easy to locate on the grid, e.g. "B6-9".
    return f"B{row}-{col}"


def localize_tamper(current_file, manifest, threshold=DEFAULT_THRESHOLD):
    """
    Compare the current file's block fingerprints against the manifest
    baseline. Returns a report with the list of tampered blocks (if any)
    and an overall verdict.
    """
    grid_info = manifest.get("tamper_grid")
    if not grid_info:
        return {
            "supported": False,
            "reason": "manifest has no baseline tamper grid",
            "tampered": False,
            "blocks": [],
        }

    block_size = grid_info["block_size"]
    baseline = grid_info["descriptors"]
    baseline_rows = grid_info["rows"]
    baseline_cols = grid_info["cols"]

    current_desc, rows, cols = compute_block_grid(current_file, block_size)

    if rows != baseline_rows or cols != baseline_cols:
        # Geometry changed outright (crop/scale/etc.) — block-level
        # localization is not meaningful without re-registration first.
        return {
            "supported": False,
            "reason": "geometry mismatch (image was cropped/resized); "
                      "re-align before localization",
            "tampered": None,
            "blocks": [],
        }

    tampered_blocks = []
    for index, (base_desc, cur_desc) in enumerate(zip(baseline, current_desc)):
        row, col = divmod(index, cols)
        distance = float(np.linalg.norm(np.array(base_desc) - np.array(cur_desc)))
        if distance > threshold:
            tampered_blocks.append(
                {
                    "row": row,
                    "col": col,
                    "label": _block_label(row, col),
                    "distance": round(distance, 2),
                    "pixel_region": [
                        col * block_size,
                        row * block_size,
                        (col + 1) * block_size,
                        (row + 1) * block_size,
                    ],
                }
            )

    total_blocks = rows * cols
    percent_tampered = round(100.0 * len(tampered_blocks) / total_blocks, 2) if total_blocks else 0.0

    return {
        "supported": True,
        "tampered": len(tampered_blocks) > 0,
        "blocks": tampered_blocks,
        "block_labels": [b["label"] for b in tampered_blocks],
        "total_blocks": total_blocks,
        "percent_tampered": percent_tampered,
        "block_size": block_size,
        "grid": [rows, cols],
        "threshold": threshold,
    }


def render_tamper_overlay(current_file, localization_result, output_path):
    """Draw red boxes over flagged blocks so the result can be shown on the
    Raspberry Pi monitor / saved into the forensic report."""
    image = cv2.imread(str(current_file), cv2.IMREAD_COLOR)
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {current_file}")

    for block in localization_result.get("blocks", []):
        x0, y0, x1, y1 = block["pixel_region"]
        cv2.rectangle(image, (x0, y0), (x1, y1), (0, 0, 255), 2)

    cv2.imwrite(str(output_path), image)
    return str(output_path)
