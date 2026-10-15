"""One-time setup on your machine. Run from the project folder:

    python scripts/setup_dev.py

Creates these if they're missing (existing files are kept; safe to re-run):
  .env    random SECRET_KEY, database passwords, demo password and ROLL_KEY (R06)
  certs/  a self-signed HTTPS certificate for nginx (browsers will show a warning)
  keys/   the election keypair (R11) and the results signing keypair (R18)

All three are listed in .gitignore, so git won't commit them.
DEV ONLY: the key files are made readable by everyone on this computer so the
Docker containers can read them. Real keys would live in a key store, not files.
"""
import base64
import datetime
import os
import secrets
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519, rsa
from cryptography.x509.oid import NameOID

ROOT = Path(__file__).resolve().parent.parent


def save_key(path, private_key):
    path.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()))


def save_public_key(path, private_key):
    path.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo))


# 1. .env with random secrets
env = ROOT / '.env'
if not env.exists():
    text = (ROOT / '.env.example').read_text()
    text = text.replace('ROLL_KEY=change-me', 'ROLL_KEY=' + base64.b64encode(os.urandom(32)).decode())
    text = text.replace('change-me', 'GENERATED')
    while 'GENERATED' in text:
        text = text.replace('GENERATED', secrets.token_urlsafe(24), 1)
    env.write_text(text)
    print('created .env (demo password = SEED_PASSWORD in .env)')

# Settings added to .env.example later are added to an existing .env too
existing = env.read_text()
existing_names = []
for line in existing.splitlines():
    existing_names.append(line.split('=')[0])
for line in (ROOT / '.env.example').read_text().splitlines():
    if '=' not in line or line.startswith('#'):
        continue
    name, value = line.split('=', 1)
    if name not in existing_names:
        if name == 'ROLL_KEY':
            value = base64.b64encode(os.urandom(32)).decode()   # 32 bytes = AES-256 (R06)
        elif value == 'change-me':
            value = secrets.token_urlsafe(24)
        existing = existing.rstrip('\n') + f'\n{name}={value}\n'
        print(f'added {name} to .env')
env.write_text(existing)

# 2. Self-signed HTTPS certificate for localhost
certs = ROOT / 'certs'
certs.mkdir(exist_ok=True)
if not (certs / 'dev.crt').exists():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'localhost')])
    now = datetime.datetime.now(datetime.timezone.utc)
    cert = (x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now).not_valid_after(now + datetime.timedelta(days=60))
            .add_extension(x509.SubjectAlternativeName([x509.DNSName('localhost')]), critical=False)
            .sign(key, hashes.SHA256()))
    save_key(certs / 'dev.key', key)
    (certs / 'dev.crt').write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    print('created certs/dev.crt and certs/dev.key')

# 3. Keys for ballot encryption (R11) and signing results (R18)
keys = ROOT / 'keys'
keys.mkdir(exist_ok=True)
if not (keys / 'election_private.pem').exists():
    election_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    save_key(keys / 'election_private.pem', election_key)
    save_public_key(keys / 'election_public.pem', election_key)
    print('created keys/election_private.pem and keys/election_public.pem')
if not (keys / 'results_signing.pem').exists():
    signing_key = ed25519.Ed25519PrivateKey.generate()
    save_key(keys / 'results_signing.pem', signing_key)
    save_public_key(keys / 'results_public.pem', signing_key)
    print('created keys/results_signing.pem and keys/results_public.pem')

# Containers run as a non-root user and need to read these files (dev setup only)
for f in list(certs.glob('*')) + list(keys.glob('*')):
    os.chmod(f, 0o644)

print('Done. Next: docker compose up --build   (or: podman compose up --build)')
