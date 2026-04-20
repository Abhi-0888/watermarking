import base64

import cv2
import numpy as np

from watermark.embed import (
    CHECKSUM_BITS,
    COEFFICIENT_PAIRS,
    END_MARKER_BITS,
    LENGTH_BITS,
    MACRO_BLOCK_SIZE,
    MAX_WATERMARK_CHARS,
    PREAMBLE_BITS,
    packet_bit_length,
)


def _bits_to_int(bits):
    return int(bits, 2) if bits else 0


def _bits_to_text(bits, char_count):
    useful_bits = bits[: char_count * 8]
    payload = bytearray()
    for index in range(0, len(useful_bits), 8):
        payload.append(int(useful_bits[index : index + 8], 2))
    return payload.decode("utf-8", errors="ignore")


def _checksum_bits(text):
    checksum = sum(text.encode("utf-8")) & 0xFFFFFFFF
    return format(checksum, f"0{CHECKSUM_BITS}b")


def _parse_packet(packet_bits, support_scores):
    preamble_end = len(PREAMBLE_BITS)
    length_end = preamble_end + LENGTH_BITS
    data_end = length_end + (MAX_WATERMARK_CHARS * 8)
    checksum_end = data_end + CHECKSUM_BITS

    if packet_bits[:preamble_end] != PREAMBLE_BITS:
        return None
    if packet_bits[checksum_end:] != END_MARKER_BITS:
        return None

    char_count = _bits_to_int(packet_bits[preamble_end:length_end])
    if char_count < 0 or char_count > MAX_WATERMARK_CHARS:
        return None

    text = _bits_to_text(packet_bits[length_end:data_end], char_count)
    if _checksum_bits(text) != packet_bits[data_end:checksum_end]:
        return None

    used_scores = support_scores[:preamble_end] + support_scores[preamble_end:length_end]
    used_scores += support_scores[length_end : length_end + (char_count * 8)]
    used_scores += support_scores[data_end:checksum_end] + support_scores[checksum_end:]
    confidence = round(float(np.mean(used_scores)) if used_scores else 0.0, 4)

    return {
        "watermark": text,
        "valid": True,
        "confidence": confidence,
    }


def _decode_from_image_array(image, max_shift_window=32):
    img = image.astype(np.float32)
    raw_bits = []

    for row in range(0, img.shape[0] - 7, 8):
        for col in range(0, img.shape[1] - 7, 8):
            block = img[row : row + 8, col : col + 8]
            dct_block = cv2.dct(block)
            pair_votes = []
            for coeff_a_pos, coeff_b_pos in COEFFICIENT_PAIRS:
                pair_votes.append(1 if float(dct_block[coeff_a_pos]) >= float(dct_block[coeff_b_pos]) else 0)
            raw_bits.append(1 if sum(pair_votes) >= (len(pair_votes) / 2.0) else 0)

    packet_length = packet_bit_length()
    if len(raw_bits) < packet_length:
        return {"watermark": None, "valid": False, "confidence": 0.0, "reason": "insufficient_blocks"}

    best_match = None
    shift_candidates = [0]
    for shift in range(1, min(max_shift_window, packet_length)):
        shift_candidates.extend([shift, packet_length - shift])

    seen_shifts = set()
    ordered_shifts = []
    for shift in shift_candidates:
        normalized = shift % packet_length
        if normalized not in seen_shifts:
            seen_shifts.add(normalized)
            ordered_shifts.append(normalized)

    for shift in ordered_shifts:
        votes = np.zeros((packet_length, 2), dtype=np.int32)
        for index, bit in enumerate(raw_bits):
            votes[(index + shift) % packet_length, bit] += 1

        majority = ["1" if vote[1] >= vote[0] else "0" for vote in votes]
        packet_bits = "".join(majority)
        totals = votes.sum(axis=1)
        support_scores = np.divide(votes.max(axis=1), totals, out=np.zeros(packet_length, dtype=float), where=totals > 0)
        parsed = _parse_packet(packet_bits, support_scores.tolist())
        if parsed and (best_match is None or parsed["confidence"] > best_match["confidence"]):
            best_match = parsed

    if best_match is None:
        return {"watermark": None, "valid": False, "confidence": 0.0, "reason": "checksum_or_marker_failed"}

    return best_match


def _decode_macro_from_image_array(image, max_shift_window=32):
    img = image.astype(np.float32)
    raw_bits = []
    block_size = MACRO_BLOCK_SIZE

    for row in range(0, img.shape[0] - block_size + 1, block_size):
        for col in range(0, img.shape[1] - block_size + 1, block_size):
            block = img[row : row + block_size, col : col + block_size]
            left_mean = float(np.mean(block[:, : block_size // 2]))
            right_mean = float(np.mean(block[:, block_size // 2 :]))
            raw_bits.append(1 if left_mean >= right_mean else 0)

    packet_length = packet_bit_length()
    if len(raw_bits) < packet_length:
        return {"watermark": None, "valid": False, "confidence": 0.0, "reason": "insufficient_macro_blocks"}

    best_match = None
    shift_candidates = [0]
    for shift in range(1, min(max_shift_window, packet_length)):
        shift_candidates.extend([shift, packet_length - shift])

    seen_shifts = set()
    ordered_shifts = []
    for shift in shift_candidates:
        normalized = shift % packet_length
        if normalized not in seen_shifts:
            seen_shifts.add(normalized)
            ordered_shifts.append(normalized)

    for shift in ordered_shifts:
        votes = np.zeros((packet_length, 2), dtype=np.int32)
        for index, bit in enumerate(raw_bits):
            votes[(index + shift) % packet_length, bit] += 1

        majority = ["1" if vote[1] >= vote[0] else "0" for vote in votes]
        packet_bits = "".join(majority)
        totals = votes.sum(axis=1)
        support_scores = np.divide(votes.max(axis=1), totals, out=np.zeros(packet_length, dtype=float), where=totals > 0)
        parsed = _parse_packet(packet_bits, support_scores.tolist())
        if parsed and (best_match is None or parsed["confidence"] > best_match["confidence"]):
            best_match = parsed

    if best_match is None:
        return {"watermark": None, "valid": False, "confidence": 0.0, "reason": "checksum_or_marker_failed"}

    return best_match


def _trim_borders(image):
    mask = image < 245
    coordinates = np.argwhere(mask)
    if coordinates.size == 0:
        return image
    y0, x0 = coordinates.min(axis=0)
    y1, x1 = coordinates.max(axis=0) + 1
    trimmed = image[y0:y1, x0:x1]
    return trimmed if trimmed.size else image


def _pad_to_shape(image, expected_shape):
    target_h, target_w = expected_shape
    if image.shape[0] > target_h or image.shape[1] > target_w:
        return image

    background = int(np.median(image[: min(10, image.shape[0]), : min(10, image.shape[1])]))
    canvas = np.full((target_h, target_w), background, dtype=image.dtype)
    start_y = (target_h - image.shape[0]) // 2
    start_x = (target_w - image.shape[1]) // 2
    canvas[start_y : start_y + image.shape[0], start_x : start_x + image.shape[1]] = image
    return canvas


def decode_thumbnail_image(thumbnail_b64):
    if not thumbnail_b64:
        return None
    raw = base64.b64decode(thumbnail_b64.encode("ascii"))
    buffer = np.frombuffer(raw, dtype=np.uint8)
    return cv2.imdecode(buffer, cv2.IMREAD_GRAYSCALE)


def _recover_from_thumbnail(image, thumbnail, expected_shape):
    if thumbnail is None or expected_shape is None:
        return None

    best = None
    expected_h, expected_w = expected_shape
    for scale in np.linspace(0.9, 1.25, 8):
        template_w = max(24, int(thumbnail.shape[1] * scale))
        template_h = max(24, int(thumbnail.shape[0] * scale))
        template = cv2.resize(thumbnail, (template_w, template_h), interpolation=cv2.INTER_CUBIC)
        if image.shape[0] < template_h or image.shape[1] < template_w:
            continue

        result = cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        if best is None or max_val > best["score"]:
            best = {"score": float(max_val), "location": max_loc, "scale": float(scale)}

    if best is None or best["score"] < 0.35:
        return None

    crop_w = min(image.shape[1], int(expected_w * best["scale"]))
    crop_h = min(image.shape[0], int(expected_h * best["scale"]))
    x0 = max(0, min(best["location"][0], image.shape[1] - crop_w))
    y0 = max(0, min(best["location"][1], image.shape[0] - crop_h))
    crop = image[y0 : y0 + crop_h, x0 : x0 + crop_w]
    if crop.size == 0:
        return None
    return cv2.resize(crop, (expected_w, expected_h), interpolation=cv2.INTER_CUBIC)


def _build_candidates(image, expected_shape, fast_mode=False):
    candidates = [image]
    trimmed = _trim_borders(image)
    if trimmed.shape != image.shape:
        candidates.append(trimmed)

    if expected_shape:
        expanded = []
        for candidate in candidates:
            if candidate.shape != expected_shape:
                expanded.append(cv2.resize(candidate, (expected_shape[1], expected_shape[0]), interpolation=cv2.INTER_AREA))
                expanded.append(cv2.resize(candidate, (expected_shape[1], expected_shape[0]), interpolation=cv2.INTER_CUBIC))
                expanded.append(_pad_to_shape(candidate, expected_shape))
                if not fast_mode:
                    softened = cv2.GaussianBlur(candidate, (3, 3), 0)
                    expanded.append(cv2.resize(softened, (expected_shape[1], expected_shape[0]), interpolation=cv2.INTER_AREA))
            expanded.append(candidate)
        candidates = expanded
    deduped = []
    seen_shapes = set()
    for candidate in candidates:
        key = (candidate.shape[0], candidate.shape[1], int(np.mean(candidate)))
        if key not in seen_shapes:
            deduped.append(candidate)
            seen_shapes.add(key)
    return deduped


def extract_watermark_details(image_path, expected_shape=None, fast_mode=False, thumbnail_b64=None):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {image_path}")

    if expected_shape and tuple(image.shape[:2]) == tuple(expected_shape):
        direct_result = _decode_from_image_array(image, max_shift_window=8 if fast_mode else 16)
        if direct_result.get("valid"):
            return direct_result
        macro_result = _decode_macro_from_image_array(image, max_shift_window=8 if fast_mode else 16)
        if macro_result.get("valid"):
            return macro_result

    best = {"watermark": None, "valid": False, "confidence": 0.0, "reason": "checksum_or_marker_failed"}
    candidates = _build_candidates(image, expected_shape, fast_mode=fast_mode)
    thumbnail = decode_thumbnail_image(thumbnail_b64)
    recovered = _recover_from_thumbnail(image, thumbnail, expected_shape)
    if recovered is not None:
        candidates.insert(0, recovered)

    for candidate in candidates:
        candidate_mismatch = expected_shape and candidate.shape != expected_shape
        if fast_mode:
            offset_limit = 3 if candidate_mismatch else 1
            shift_window = 24 if candidate_mismatch else 8
        else:
            offset_limit = 8 if candidate_mismatch else 3
            shift_window = 96 if candidate_mismatch else 32
        for y_offset in range(0, min(offset_limit, candidate.shape[0] % 8 + 1)):
            for x_offset in range(0, min(offset_limit, candidate.shape[1] % 8 + 1)):
                cropped = candidate[y_offset:, x_offset:]
                primary = _decode_from_image_array(cropped, max_shift_window=shift_window)
                if primary.get("valid") and primary.get("confidence", 0.0) > best.get("confidence", 0.0):
                    best = primary
                macro = _decode_macro_from_image_array(cropped, max_shift_window=shift_window)
                if macro.get("valid") and macro.get("confidence", 0.0) > best.get("confidence", 0.0):
                    best = macro
    return best


def extract_watermark(image_path):
    details = extract_watermark_details(image_path)
    return details["watermark"] if details["valid"] else ""
