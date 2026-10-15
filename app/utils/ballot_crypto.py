# Sealing and opening ballots
# PLACEHOLDER (R11): plain JSON. R11 encrypts with the election public key (Week 7 lecture s19).
# prefs maps candidate id -> preference number, e.g. {"3": 1, "1": 2, "2": 3}
import json


def seal_ballot(prefs):
    """dict -> bytes stored in the ballots table"""
    return json.dumps(prefs, sort_keys=True).encode('utf-8')


def open_ballot(sealed, private_key=None):
    """bytes from the ballots table -> dict. Only the count needs this."""
    return json.loads(sealed.decode('utf-8'))
