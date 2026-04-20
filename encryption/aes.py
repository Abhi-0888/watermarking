from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

# Generate AES key
def generate_key():
    return get_random_bytes(16)

# Encrypt file
def encrypt_file(input_file, output_file, key):
    cipher = AES.new(key, AES.MODE_EAX)

    with open(input_file, 'rb') as f:
        data = f.read()

    ciphertext, tag = cipher.encrypt_and_digest(data)

    with open(output_file, 'wb') as f:
        f.write(cipher.nonce)
        f.write(tag)
        f.write(ciphertext)

# Decrypt file
def decrypt_file(input_file, output_file, key):
    with open(input_file, 'rb') as f:
        nonce = f.read(16)
        tag = f.read(16)
        ciphertext = f.read()

    cipher = AES.new(key, AES.MODE_EAX, nonce=nonce)
    data = cipher.decrypt_and_verify(ciphertext, tag)

    with open(output_file, 'wb') as f:
        f.write(data)