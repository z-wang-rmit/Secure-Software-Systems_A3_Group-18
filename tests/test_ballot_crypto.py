import json
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from app.utils.ballot_crypto import seal_ballot, open_ballot


def test_seal_then_open_returns_same_prefs():
    prefs = {'3': 1, '1': 2, '2': 3}
    sealed = seal_ballot(prefs)
    opened = open_ballot(sealed)
    assert opened == prefs


def test_sealed_ballot_hides_the_prefs():
    prefs = {'3': 1, '1': 2, '2': 3}
    sealed = seal_ballot(prefs)
    plain_bytes = json.dumps(prefs, sort_keys=True).encode('utf-8')
    assert plain_bytes not in sealed
    with pytest.raises(ValueError):
        json.loads(sealed)


def test_sealing_same_prefs_twice_gives_different_bytes():
    prefs = {'3': 1, '1': 2, '2': 3}
    sealed1 = seal_ballot(prefs)
    sealed2 = seal_ballot(prefs)
    assert sealed1 != sealed2


def test_wrong_private_key_cannot_open_ballot():
    prefs = {'3': 1, '1': 2, '2': 3}
    sealed = seal_ballot(prefs)
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=3072)
    with pytest.raises(ValueError):
        open_ballot(sealed, other_key)


def test_tampered_ballot_is_rejected():
    prefs = {'3': 1, '1': 2, '2': 3}
    sealed = seal_ballot(prefs)
    tampered = bytearray(sealed)
    tampered[10] ^= 1
    tampered_bytes = bytes(tampered)
    with pytest.raises(ValueError):
        open_ballot(tampered_bytes)