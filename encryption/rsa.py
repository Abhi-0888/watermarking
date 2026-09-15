from pathlib import Path

from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

# Generate RSA keys
def generate_keys():
    key = RSA.generate(2048)
    private_key = key
    public_key = key.publickey()
    return private_key, public_key


# Persist keys so later transfer/verification steps (and the Raspberry Pi
# terminal) can reuse the same issuer keypair instead of generating a new
# one on every run.
def save_keys(private_key, public_key, key_dir):
    path = Path(key_dir)
    path.mkdir(parents=True, exist_ok=True)
    private_path = path / "private.pem"
    public_path = path / "public.pem"
    private_path.write_bytes(private_key.export_key())
    public_path.write_bytes(public_key.export_key())
    try:
        # Best-effort "secure storage": restrict the private key to the
        # owner only. On Windows this is a no-op.
        private_path.chmod(0o600)
    except (NotImplementedError, PermissionError):
        pass
    return str(private_path), str(public_path)


def load_keys(key_dir):
    path = Path(key_dir)
    private_path = path / "private.pem"
    public_path = path / "public.pem"
    if not private_path.exists() or not public_path.exists():
        raise FileNotFoundError(
            f"No keypair found in {path}. Run the issuer/protect step first."
        )
    private_key = RSA.import_key(private_path.read_bytes())
    public_key = RSA.import_key(public_path.read_bytes())
    return private_key, public_key


# Encrypt AES key using public key
def encrypt_key(aes_key, public_key):
    cipher = PKCS1_OAEP.new(public_key)
    encrypted_key = cipher.encrypt(aes_key)
    return encrypted_key


# Decrypt AES key using private key
def decrypt_key(encrypted_key, private_key):
    cipher = PKCS1_OAEP.new(private_key)
    decrypted_key = cipher.decrypt(encrypted_key)
    return decrypted_key