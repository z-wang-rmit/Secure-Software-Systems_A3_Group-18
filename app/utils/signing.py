# Signing published results (R18)
# Ed25519 digital signature (Week 7 lecture s34): proves the results came from us
# and were not changed. Anyone can check them with keys/results_public.pem.
import base64
import binascii
import json
import os

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


def canonical_bytes(payload):
    """The exact bytes that get signed: sorted keys, no spaces, so key order doesn't matter"""
    return json.dumps(payload, sort_keys=True, separators=(',', ':')).encode('utf-8')


def public_key_pem():
    """The public key as PEM bytes, published so other systems can verify results"""
    pub_path = os.environ.get('RESULTS_PUBLIC_KEY', 'keys/results_public.pem')
    with open(pub_path, 'rb') as f:
        return f.read()


def sign_results(payload, private_key=None):
    """dict -> base64 signature string"""
    # load the signing key from file if one wasn't passed in
    if private_key is None:
        priv_path = os.environ.get('RESULTS_SIGNING_KEY', 'keys/results_signing.pem')
        with open(priv_path, 'rb') as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)
    if not isinstance(private_key, ed25519.Ed25519PrivateKey):
        raise TypeError('results signing key must be Ed25519')

    signature = private_key.sign(canonical_bytes(payload))
    return base64.b64encode(signature).decode('ascii')


def verify_results(payload, signature):
    """True if the signature matches the payload"""
    public_key = serialization.load_pem_public_key(public_key_pem())
    if not isinstance(public_key, ed25519.Ed25519PublicKey):
        raise TypeError('results public key must be Ed25519')
    try:
        public_key.verify(base64.b64decode(signature, validate=True), canonical_bytes(payload))
        return True
    except (InvalidSignature, binascii.Error, ValueError):
        return False
