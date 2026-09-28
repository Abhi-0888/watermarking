"""
scripts/make_tampered.py — Create tampered/attacked variants of the current
protected image for Step 4 of the Pi verification test.

Four variants are produced:
  a) tampered_patch.png  — grey rectangle painted over a face/content area
                           (deliberate localised edit → TAMPERED expected)
  b) tampered_text.png   — small white text overlay
                           (deliberate localised edit → TAMPERED expected)
  c) tampered_jpeg.png   — JPEG lossy re-compression artefacts
                           (redistribution attack — geometry preserved but
                           pixel values change; honest behaviour: may PASS
                           or flag some blocks depending on threshold)
  d) tampered_crop.png   — 32-pixel crop on every side
                           (redistribution attack — geometry changes so
                           block-level localizer reports geometry mismatch;
                           hash/signature will fail too; honest: SUSPICIOUS)

Usage (from project root, venv active):
    python3 scripts/make_tampered.py
    python3 scripts/make_tampered.py --source samples/watermarked.png \
                                     --output samples/tampered

Then run each through the Pi terminal, e.g.:
    python3 raspberry_pi/pi_verify_terminal.py \
        --file samples/tampered/tampered_patch.png \
        --manifest samples/manifest.json \
        --registry samples/registry.json \
        --provenance samples/provenance.json \
        --mode online
"""

import argparse
import sys
from pathlib import Path

import cv2
import numpy as np

# Allow running as `python3 scripts/make_tampered.py` from project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _load_gray(path: str) -> np.ndarray:
    img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
    if img is None:
        raise FileNotFoundError(f"Cannot read image: {path}")
    return img


def make_patch(img: np.ndarray, output_path: str) -> None:
    """Paint a 60×60 grey rectangle near the centre — a classic splice/redaction edit."""
    out = img.copy()
    h, w = out.shape
    cy, cx = h // 2, w // 2
    # Slightly off-centre so it visibly overlaps content
    y0, y1 = cy - 40, cy + 20
    x0, x1 = cx - 30, cx + 30
    out[y0:y1, x0:x1] = 128  # mid-grey patch
    cv2.imwrite(output_path, out)
    print(f"  [patch]  {output_path}  ({y1-y0}×{x1-x0} px grey rectangle at centre)")


def make_text(img: np.ndarray, output_path: str) -> None:
    """Overlay small white text — simulates stamp / annotation tampering."""
    out = img.copy()
    h, w = out.shape
    # Write on a colour copy so putText works, then convert back
    colour = cv2.cvtColor(out, cv2.COLOR_GRAY2BGR)
    cv2.putText(
        colour,
        "COPY",
        (w // 4, h // 3),
        cv2.FONT_HERSHEY_SIMPLEX,
        fontScale=1.4,
        color=(255, 255, 255),
        thickness=3,
        lineType=cv2.LINE_AA,
    )
    cv2.putText(
        colour,
        "UNVERIFIED",
        (w // 4, h // 3 + 40),
        cv2.FONT_HERSHEY_SIMPLEX,
        fontScale=0.9,
        color=(255, 255, 255),
        thickness=2,
        lineType=cv2.LINE_AA,
    )
    gray_out = cv2.cvtColor(colour, cv2.COLOR_BGR2GRAY)
    cv2.imwrite(output_path, gray_out)
    print(f"  [text]   {output_path}  ('COPY UNVERIFIED' text overlay at ~({w//4},{h//3}))")


def make_jpeg(img: np.ndarray, output_path: str, quality: int = 50) -> None:
    """JPEG compression — redistribution attack, geometry unchanged.
    The output is saved as .png for a fair pixel comparison; the lossy
    damage is baked in by the JPEG encode/decode round-trip."""
    # Encode to JPEG in-memory at the chosen quality level
    ok, buf = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    # Decode back to numpy (lossy damage is now in the array)
    degraded = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    cv2.imwrite(output_path, degraded)
    print(
        f"  [jpeg]   {output_path}  (JPEG quality={quality} round-trip; "
        f"redistribution attack — geometry unchanged)"
    )


def make_crop(img: np.ndarray, output_path: str, margin: int = 32) -> None:
    """Crop margins — redistribution attack, geometry changes.
    Block-level localizer will report geometry mismatch (not localized)."""
    h, w = img.shape
    if h <= 2 * margin or w <= 2 * margin:
        raise ValueError(f"Image too small to crop by {margin}px on each side")
    cropped = img[margin : h - margin, margin : w - margin]
    cv2.imwrite(output_path, cropped)
    print(
        f"  [crop]   {output_path}  ({margin}px crop each side → "
        f"{cropped.shape[1]}×{cropped.shape[0]} from {w}×{h}; "
        f"redistribution attack — geometry mismatch expected)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create tampered/attacked variants of the protected document image."
    )
    parser.add_argument(
        "--source",
        default="samples/watermarked.png",
        help="Source protected image (default: samples/watermarked.png)",
    )
    parser.add_argument(
        "--output",
        default="samples/tampered",
        help="Output directory (default: samples/tampered)",
    )
    parser.add_argument(
        "--jpeg-quality",
        type=int,
        default=50,
        metavar="Q",
        help="JPEG quality for compression variant, 1-100 (default: 50)",
    )
    parser.add_argument(
        "--crop-margin",
        type=int,
        default=32,
        metavar="PX",
        help="Pixels to crop from each edge (default: 32)",
    )
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(
            f"ERROR: Source file not found: {source_path}\n"
            "Run `python3 main.py demo` first to generate samples/watermarked.png",
            file=sys.stderr,
        )
        sys.exit(1)

    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nCreating tampered variants from: {source_path}")
    print(f"Output directory              : {out_dir}\n")

    img = _load_gray(str(source_path))
    h, w = img.shape
    print(f"  Source image size: {w}×{h} px\n")

    make_patch(img, str(out_dir / "tampered_patch.png"))
    make_text(img, str(out_dir / "tampered_text.png"))
    make_jpeg(img, str(out_dir / "tampered_jpeg.png"), quality=args.jpeg_quality)
    make_crop(img, str(out_dir / "tampered_crop.png"), margin=args.crop_margin)

    print(
        f"\nAll variants written to {out_dir}/\n"
        "\nExpected verdicts when run through the Pi terminal:\n"
        "  tampered_patch.png  → TAMPERED  (painted patch detected by block fingerprints)\n"
        "  tampered_text.png   → TAMPERED  (text pixels alter block descriptors)\n"
        "  tampered_jpeg.png   → may PASS or raise some blocks (redistribution, not edit)\n"
        "  tampered_crop.png   → SUSPICIOUS (geometry mismatch; hash + sig fail)\n"
        "\nRun each with:\n"
        "  python3 raspberry_pi/pi_verify_terminal.py \\\n"
        f"      --file {out_dir}/tampered_<variant>.png \\\n"
        "      --manifest samples/manifest.json \\\n"
        "      --registry samples/registry.json \\\n"
        "      --provenance samples/provenance.json \\\n"
        "      --mode online"
    )


if __name__ == "__main__":
    main()
