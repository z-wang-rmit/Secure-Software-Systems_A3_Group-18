
from app.utils.helpers import validate_password
from app.models import User, Elector
from app import db
from app.utils.roll_crypto import encrypt_field
from tests.helpers import make_client


def test_password_policy_accepts_valid_password():
    valid, error = validate_password("Secure-voter-2026")
    assert valid is True
    assert error is None


def test_password_policy_rejects_short_password():
    valid, error = validate_password("Short123")
    assert valid is False
    assert error is not None


def test_password_policy_rejects_password_without_digits():
    valid, error = validate_password("OnlyLettersHere")
    assert valid is False
    assert error is not None


def test_password_policy_rejects_password_without_letters():
    valid, error = validate_password("123456789012")
    assert valid is False
    assert error is not None


def test_password_policy_rejects_common_password():
    valid, error = validate_password("Password123")
    assert valid is False
    assert error is not None


def test_password_is_stored_as_bcrypt_hash():
    client = make_client()

    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()

        assert user is not None
        assert user.password_hash != "test-password-123"
        assert user.password_hash.startswith("$2b$")
        assert user.check_password("test-password-123")


def test_registration_rejects_weak_password_without_creating_account():
    client = make_client()

    with client.application.app_context():
        elector = Elector(
            enrolment_no="E123456789",
            given_name=encrypt_field("Test"),
            family_name=encrypt_field("Voter"),
            dob=encrypt_field("1990-01-01"),
            address=encrypt_field("1 Test Street"),
            division_id=1,
        )
        db.session.add(elector)
        db.session.commit()
        users_before = User.query.count()

    response = client.post(
        "/register",
        data={
            "enrolment_no": "E123456789",
            "username": "weakpassworduser",
            "password": "Short123",
        },
    )

    assert response.status_code == 400

    with client.application.app_context():
        assert User.query.count() == users_before
        assert User.query.filter_by(
            username="weakpassworduser"
        ).first() is None
