# Protecting electoral roll personal details (R06)
# AES-256-GCM, based on the Week 2 EncryptionUtil (shared/encryption.py).
# Fix to the sample: the 32-byte key comes from ROLL_KEY in .env, not a hard-coded SHARED_SECRET.
import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

NONCE_SIZE = 12  # 96-bit random IV, stored in front of the ciphertext


def _load_key():
    """Read the 32-byte AES key from the ROLL_KEY environment variable (base64)."""
    encoded = os.environ.get('ROLL_KEY')
    if not encoded or encoded == 'change-me':
        raise RuntimeError('ROLL_KEY is not set: run python scripts/setup_dev.py')
    key = base64.b64decode(encoded)
    if len(key) != 32:
        raise RuntimeError('ROLL_KEY must be 32 bytes (AES-256)')
    return key


def encrypt_field(value):
    """str -> bytes stored in the database: nonce (12 bytes) + ciphertext + GCM tag"""
    nonce = os.urandom(NONCE_SIZE)
    ciphertext = AESGCM(_load_key()).encrypt(nonce, value.encode('utf-8'), None)
    return nonce + ciphertext


def decrypt_field(data):
    """bytes from the database -> str. Raises InvalidTag if the data was changed."""
    nonce, ciphertext = data[:NONCE_SIZE], data[NONCE_SIZE:]
    return AESGCM(_load_key()).decrypt(nonce, ciphertext, None).decode('utf-8')
