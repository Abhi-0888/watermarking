from pathlib import Path

import cv2
import numpy as np


def ensure_parent(path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def create_attack_set(source_image, output_dir):
    ensure_parent(str(Path(output_dir) / "placeholder.txt"))
    image = cv2.imread(source_image, cv2.IMREAD_GRAYSCALE)
    if image is None:
        raise FileNotFoundError(f"Unable to read image: {source_image}")

    attacks = {}

    compressed_path = str(Path(output_dir) / "compressed.jpg")
    cv2.imwrite(compressed_path, image, [int(cv2.IMWRITE_JPEG_QUALITY), 60])
    attacks["compression"] = compressed_path

    crop = image[16:-16, 16:-16]
    cropped_path = str(Path(output_dir) / "cropped.png")
    cv2.imwrite(cropped_path, crop)
    attacks["cropping"] = cropped_path

    scaled = cv2.resize(image, None, fx=1.35, fy=1.35, interpolation=cv2.INTER_CUBIC)
    scaled = cv2.resize(scaled, (image.shape[1], image.shape[0]), interpolation=cv2.INTER_AREA)
    scaled_path = str(Path(output_dir) / "scaled.png")
    cv2.imwrite(scaled_path, scaled)
    attacks["scaling"] = scaled_path

    # Screenshot-style redistribution: document captured within a larger screen canvas.
    canvas = np.full((image.shape[0] + 120, image.shape[1] + 120), 245, dtype=np.uint8)
    start_y = (canvas.shape[0] - image.shape[0]) // 2
    start_x = (canvas.shape[1] - image.shape[1]) // 2
    canvas[start_y : start_y + image.shape[0], start_x : start_x + image.shape[1]] = image
    screenshot_path = str(Path(output_dir) / "screenshot.png")
    cv2.imwrite(screenshot_path, canvas)
    attacks["screenshot"] = screenshot_path

    edited = cv2.GaussianBlur(image, (3, 3), 0)
    edited = cv2.convertScaleAbs(edited, alpha=1.01, beta=2)
    edited_path = str(Path(output_dir) / "minor_edit.png")
    cv2.imwrite(edited_path, edited)
    attacks["minor_edit"] = edited_path

    return attacks
