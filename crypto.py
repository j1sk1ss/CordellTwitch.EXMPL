import os
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.backends import default_backend


def encrypt_video(file_path, key):
    with open(file_path, "rb") as f:
        data = f.read()

    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()

    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(data) + padder.finalize()

    with open(file_path, "wb") as f:
        f.write(iv)
        f.write(encryptor.update(padded_data) + encryptor.finalize())


def decrypt_video(file_path, start, length, key):
    with open(file_path, "rb") as f:
        iv = f.read(16)  # Read IV from the start of the file
        cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
        decryptor = cipher.decryptor()

        f.seek(start + 16)  # Skip over the IV when seeking to the file position
        data = f.read(length)

        # If the length of the data is not a multiple of 16, pad it
        if len(data) % 16 != 0:
            padder = padding.PKCS7(128).padder()
            data = padder.update(data) + padder.finalize()

        decrypted_data = decryptor.update(data) + decryptor.finalize()

        # Unpadding after decryption
        unpadder = padding.PKCS7(128).unpadder()
        return unpadder.update(decrypted_data) + unpadder.finalize()