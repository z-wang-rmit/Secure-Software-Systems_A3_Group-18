# R06 tests: electoral roll details are encrypted with AES-256-GCM
import pytest
from cryptography.exceptions import InvalidTag

from app.models.elector import Elector
from app.utils.roll_crypto import decrypt_field, encrypt_field
from tests.helpers import make_client


def test_round_trip_gives_original_back():
    assert decrypt_field(encrypt_field('12 Swanston St, Melbourne')) == '12 Swanston St, Melbourne'


def test_ciphertext_does_not_contain_plain_text():
    sealed = encrypt_field('Voter1')
    assert b'Voter1' not in sealed


def test_same_value_encrypts_differently_each_time():
    # random nonce: two encryptions of the same name must not match
    assert encrypt_field('Smith') != encrypt_field('Smith')


def test_tampered_ciphertext_is_rejected():
    sealed = bytearray(encrypt_field('1 Test St'))
    sealed[-1] ^= 1  # flip one bit
    with pytest.raises(InvalidTag):
        decrypt_field(bytes(sealed))


def test_database_column_is_not_plain_text():
    client = make_client()
    with client.application.app_context():
        elector = Elector.query.first()
        plain = elector.to_dict()['given_name']
        assert plain.encode() not in elector.given_name
