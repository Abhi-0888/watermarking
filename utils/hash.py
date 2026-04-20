import base64
import hashlib

from Crypto.Hash import SHA256
from Crypto.Signature import pkcs1_15


def generate_hash(file_path):
    sha = hashlib.sha256()
    with open(file_path, "rb") as file_handle:
        while chunk := file_handle.read(4096):
            sha.update(chunk)
    return sha.hexdigest()


def _hash_file_for_signature(file_path):
    digest = SHA256.new()
    with open(file_path, "rb") as file_handle:
        while chunk := file_handle.read(4096):
            digest.update(chunk)
    return digest


def sign_document(file_path, private_key):
    return pkcs1_15.new(private_key).sign(_hash_file_for_signature(file_path))


def verify_signature(file_path, signature, public_key):
    try:
        pkcs1_15.new(public_key).verify(_hash_file_for_signature(file_path), signature)
        return True
    except (ValueError, TypeError):
        return False


def signature_to_text(signature):
    return base64.b64encode(signature).decode("ascii")


def signature_from_text(signature_text):
    return base64.b64decode(signature_text.encode("ascii"))
