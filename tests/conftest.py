# Test-only settings shared by every test file
import base64
import os
import tempfile
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

# R06: a throwaway AES key for tests (CI has no .env). Never used outside tests.
os.environ.setdefault('ROLL_KEY', base64.b64encode(b'0' * 32).decode())

# R11: a throwaway election key pair for tests, because CI has no keys/ folder.
key_dir = tempfile.mkdtemp()
election_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)

priv_path = os.path.join(key_dir, 'election_private.pem')
with open(priv_path, 'wb') as f:
    f.write(election_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))

pub_path = os.path.join(key_dir, 'election_public.pem')
with open(pub_path, 'wb') as f:
    f.write(election_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))

os.environ.setdefault('ELECTION_PUBLIC_KEY', pub_path)
os.environ.setdefault('ELECTION_PRIVATE_KEY', priv_path)