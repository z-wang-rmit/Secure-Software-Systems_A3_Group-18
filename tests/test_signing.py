# R18: results are signed with Ed25519 and anyone with the public key can check them
from cryptography.hazmat.primitives.asymmetric import ed25519
from app.utils.signing import sign_results, verify_results

PAYLOAD = {'election': 'Federal 2026', 'division': 'Melbourne',
           'ballots_total': 2, 'first_preferences': {'Alice': 2, 'Bob': 0},
           'elected': 'Alice'}


def test_signature_verifies():
    assert verify_results(PAYLOAD, sign_results(PAYLOAD)) is True


def test_changed_payload_fails():
    signature = sign_results(PAYLOAD)
    changed = dict(PAYLOAD, elected='Bob')
    assert verify_results(changed, signature) is False


def test_key_order_does_not_matter():
    # The database may return the JSON keys in another order
    reordered = dict(reversed(list(PAYLOAD.items())))
    assert verify_results(reordered, sign_results(PAYLOAD)) is True


def test_wrong_key_fails():
    other_key = ed25519.Ed25519PrivateKey.generate()
    signature = sign_results(PAYLOAD, private_key=other_key)
    assert verify_results(PAYLOAD, signature) is False


def test_garbage_signature_fails():
    assert verify_results(PAYLOAD, 'unsigned') is False
    assert verify_results(PAYLOAD, '') is False
