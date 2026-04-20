import cv2
import numpy as np


PREAMBLE_BITS = "10101011110011011110011010101010"
END_MARKER_BITS = "1111111111111110"
MAX_WATERMARK_CHARS = 80
LENGTH_BITS = 16
CHECKSUM_BITS = 32
COEFFICIENT_PAIRS = [
    ((2, 3), (3, 2)),
    ((3, 4), (4, 3)),
    ((2, 4), (4, 2)),
]
MACRO_BLOCK_SIZE = 16
MACRO_STRENGTH = 3.0


def _text_to_bits(text):
    return "".join(format(byte, "08b") for byte in text.encode("utf-8"))


def _int_to_bits(value, width):
    return format(value, f"0{width}b")


def _checksum_bits(text):
    checksum = sum(text.encode("utf-8")) & 0xFFFFFFFF
    return _int_to_bits(checksum, CHECKSUM_BITS)


def build_packet_bits(watermark_text):
    payload = watermark_text[:MAX_WATERMARK_CHARS]
    payload_bits = _text_to_bits(payload)
    padded_data = payload_bits.ljust(MAX_WATERMARK_CHARS * 8, "0")
    return (
        PREAMBLE_BITS
        + _int_to_bits(len(payload), LENGTH_BITS)
        + padded_data
        + _checksum_bits(payload)
        + END_MARKER_BITS
    )


def packet_bit_length():
    return len(PREAMBLE_BITS) + LENGTH_BITS + (MAX_WATERMARK_CHARS * 8) + CHECKSUM_BITS + len(END_MARKER_BITS)


def _embed_macro_watermark(img, packet_bits, strength):
    block_size = MACRO_BLOCK_SIZE
    block_index = 0
    packet_length = len(packet_bits)
    height, width = img.shape

    for row in range(0, height - block_size + 1, block_size):
        for col in range(0, width - block_size + 1, block_size):
            bit = int(packet_bits[block_index % packet_length])
            block = img[row : row + block_size, col : col + block_size]
            left = block[:, : block_size // 2]
            right = block[:, block_size // 2 :]
            left_mean = float(np.mean(left))
            right_mean = float(np.mean(right))
            midpoint = (left_mean + right_mean) / 2.0

            if bit:
                desired_left = midpoint + strength
                desired_right = midpoint - strength
            else:
                desired_left = midpoint - strength
                desired_right = midpoint + strength

            left += desired_left - left_mean
            right += desired_right - right_mean
            block_index += 1

    return block_index


def embed_watermark(image_path, output_path, watermark_text, strength=28):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {image_path}")

    img = image.astype(np.float32)
    packet_bits = build_packet_bits(watermark_text)
    packet_length = len(packet_bits)
    h, w = img.shape
    block_index = 0

    for row in range(0, h - 7, 8):
        for col in range(0, w - 7, 8):
            block = img[row : row + 8, col : col + 8]
            dct_block = cv2.dct(block)
            bit = int(packet_bits[block_index % packet_length])

            for coeff_a_pos, coeff_b_pos in COEFFICIENT_PAIRS:
                coeff_a = float(dct_block[coeff_a_pos])
                coeff_b = float(dct_block[coeff_b_pos])
                midpoint = (coeff_a + coeff_b) / 2.0
                guard_band = max(abs(coeff_a - coeff_b) / 2.0, strength)

                if bit:
                    dct_block[coeff_a_pos] = midpoint + guard_band
                    dct_block[coeff_b_pos] = midpoint - guard_band
                else:
                    dct_block[coeff_a_pos] = midpoint - guard_band
                    dct_block[coeff_b_pos] = midpoint + guard_band

            img[row : row + 8, col : col + 8] = cv2.idct(dct_block)
            block_index += 1

    macro_blocks = _embed_macro_watermark(img, packet_bits, MACRO_STRENGTH)
    watermarked = np.clip(img, 0, 255).astype(np.uint8)
    cv2.imwrite(output_path, watermarked)
    return {
        "embedded_blocks": block_index,
        "macro_blocks": macro_blocks,
        "packet_length": packet_length,
        "redundancy": round(block_index / packet_length, 2) if packet_length else 0,
        "payload_chars": min(len(watermark_text), MAX_WATERMARK_CHARS),
    }
