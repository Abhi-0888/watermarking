from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256

def sign_document(data: bytes, private_key) -> bytes:
    h = SHA256.new(data)
    return pkcs1_15.new(private_key).sign(h)

def verify_signature(data: bytes, signature: bytes, public_key) -> bool:
    h = SHA256.new(data)
    try:
        pkcs1_15.new(public_key).verify(h, signature)
        return True
    except (ValueError, TypeError):
        return False