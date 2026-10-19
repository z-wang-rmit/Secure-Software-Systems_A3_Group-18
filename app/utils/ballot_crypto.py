# Sealing and opening ballots
# Uses RSA-OAEP with the election key (Week 7 lecture s19)
# prefs maps candidate id -> preference number, e.g. {"3": 1, "1": 2, "2": 3}

import json
import os
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

OAEP = padding.OAEP(
    mgf=padding.MGF1(algorithm=hashes.SHA256()),
    algorithm=hashes.SHA256(),
    label=None,
)


def seal_ballot(prefs):
    """dict -> bytes stored in the ballots table"""
    # turn prefs dict into sorted json bytes
    raw_bytes = json.dumps(prefs, sort_keys=True).encode("utf-8")

    # get public key path from env or use default
    pub_path = os.environ.get("ELECTION_PUBLIC_KEY", "keys/election_public.pem")

    # load the public key file
    with open(pub_path, "rb") as f:
        pub_key = serialization.load_pem_public_key(f.read())

    # encrypt with RSA-OAEP and return
    sealed = pub_key.encrypt(raw_bytes, OAEP)
    return sealed


def open_ballot(sealed, private_key=None):
    """bytes from the ballots table -> dict. Only the count needs this."""
    # load the private key from file if one wasn't passed in
    if private_key is None:
        priv_path = os.environ.get("ELECTION_PRIVATE_KEY", "keys/election_private.pem")
        with open(priv_path, "rb") as f:
            private_key = serialization.load_pem_private_key(f.read(), password=None)

    # decrypt the ballot bytes
    plain_bytes = private_key.decrypt(sealed, OAEP)

    # convert json bytes back to a dict
    prefs = json.loads(plain_bytes)
    return prefs