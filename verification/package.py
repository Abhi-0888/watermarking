import base64
import json
from pathlib import Path

import cv2

from utils.hash import generate_hash, sign_document, signature_to_text


def write_manifest(manifest_path, manifest_data):
    path = Path(manifest_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(manifest_data, file_handle, indent=2)


def update_registry(registry_path, manifest_data):
    path = Path(registry_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    registry = {}
    if path.exists():
        with open(path, "r", encoding="utf-8") as file_handle:
            registry = json.load(file_handle)

    registry[manifest_data["document_id"]] = {
        "issuer_id": manifest_data["issuer_id"],
        "receiver_identity": manifest_data["receiver_identity"],
        "protected_hash": manifest_data["protected_hash"],
        "timestamp": manifest_data["timestamp"],
    }

    with open(path, "w", encoding="utf-8") as file_handle:
        json.dump(registry, file_handle, indent=2)


def build_manifest(
    original_file,
    protected_file,
    watermark_text,
    private_key,
    public_key,
    issuer_id,
    receiver_identity,
    document_id,
    timestamp,
    encrypted_aes_key,
    image_shape,
):
    protected_image = cv2.imread(protected_file, cv2.IMREAD_GRAYSCALE)
    signature = sign_document(protected_file, private_key)
    thumbnail = cv2.resize(protected_image, (96, 96), interpolation=cv2.INTER_AREA)
    _, encoded = cv2.imencode(".png", thumbnail)
    return {
        "issuer_id": issuer_id,
        "receiver_identity": receiver_identity,
        "document_id": document_id,
        "timestamp": timestamp,
        "watermark_text": watermark_text,
        "original_hash": generate_hash(original_file),
        "protected_hash": generate_hash(protected_file),
        "signature_b64": signature_to_text(signature),
        "public_key_pem": public_key.export_key().decode("ascii"),
        "encrypted_aes_key_b64": encrypted_aes_key.hex(),
        "image_shape": list(image_shape),
        "reference_thumbnail_b64": base64.b64encode(encoded.tobytes()).decode("ascii"),
        "verification_modes": ["offline", "online"],
    }
