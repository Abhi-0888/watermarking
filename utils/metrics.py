import difflib
import time

import cv2
import numpy as np

from watermark.embed import MAX_WATERMARK_CHARS, packet_bit_length


def measure_psnr(original_path, watermarked_path):
    orig = cv2.imread(original_path, cv2.IMREAD_GRAYSCALE).astype(np.float64)
    wm = cv2.imread(watermarked_path, cv2.IMREAD_GRAYSCALE).astype(np.float64)
    mse = np.mean((orig - wm) ** 2)
    if mse == 0:
        return float("inf")
    psnr = 10 * np.log10((255 ** 2) / mse)
    return round(psnr, 2)


def measure_encryption_time(func, *args):
    start = time.time()
    result = func(*args)
    end = time.time()
    elapsed_ms = round((end - start) * 1000, 2)
    return result, elapsed_ms


def measure_embedding_capacity(image_path):
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    h, w = img.shape
    num_blocks = (h // 8) * (w // 8)
    capacity_bits = num_blocks
    capacity_chars = capacity_bits // 8
    usable_chars = min(MAX_WATERMARK_CHARS, capacity_chars)
    return {
        "blocks": num_blocks,
        "capacity_bits": capacity_bits,
        "capacity_chars": capacity_chars,
        "usable_chars": usable_chars,
        "packet_bits": packet_bit_length(),
    }


def measure_extraction_accuracy(expected_text, extracted_text):
    if expected_text == extracted_text:
        return 1.0
    return round(difflib.SequenceMatcher(a=expected_text, b=extracted_text).ratio(), 4)


def measure_false_positive_rate(results):
    if not results:
        return 0.0
    false_positives = sum(1 for item in results if item.get("valid"))
    return round(false_positives / len(results), 4)


def print_metrics(summary):
    print("\n" + "=" * 58)
    print("SYSTEM METRICS")
    print("=" * 58)
    print(f"PSNR (image quality)   : {summary['psnr']} dB")
    print(f"Encryption time        : {summary['encryption_ms']} ms")
    print(f"Embedding capacity     : {summary['capacity_chars']} characters")
    print(f"Packet size            : {summary['packet_bits']} bits")
    print(f"Extraction accuracy    : {summary['extraction_accuracy']}")
    print(f"False positive rate    : {summary['false_positive_rate']}")
    print(f"Attack pass rate       : {summary['attack_pass_rate']}")
    print("=" * 58 + "\n")
