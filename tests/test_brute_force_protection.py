
from tests.helpers import make_client, PASSWORD
from app import db
from app.models import User
from app.utils.helpers import utcnow
from datetime import timedelta


def test_account_locks_after_five_failed_attempts():
    client = make_client()

    for _ in range(5):
        response = client.post(
            "/login",
            data={"username": "voter1", "password": "wrong"},
        )
        assert response.status_code == 401

    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        assert user.failed_logins == 5
        assert user.locked_until is not None
        assert user.locked_until > utcnow()


def test_correct_password_rejected_during_lockout():
    client = make_client()

    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        user.failed_logins = 5
        user.locked_until = utcnow() + __import__(
            "datetime"
        ).timedelta(minutes=15)
        db.session.commit()

    response = client.post(
        "/login",
        data={"username": "voter1", "password": PASSWORD},
    )

    assert response.status_code == 401

    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        assert user.locked_until is not None
        assert user.failed_logins == 5


def test_successful_login_resets_failed_attempts():
    client = make_client()

    for _ in range(3):
        client.post(
            "/login",
            data={"username": "voter1", "password": "wrong"},
        )

    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        assert user.failed_logins == 3

    response = client.post(
        "/login",
        data={"username": "voter1", "password": PASSWORD},
    )
    assert response.status_code == 302

    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        assert user.failed_logins == 0
        assert user.locked_until is None


def test_unknown_username_and_wrong_password_same_message():
    client = make_client()

    wrong_password = client.post(
        "/login",
        data={"username": "voter1", "password": "wrong"},
    )
    unknown_user = client.post(
        "/login",
        data={"username": "unknown-test-user", "password": "wrong"},
    )

    assert wrong_password.status_code == unknown_user.status_code == 401
    assert wrong_password.data == unknown_user.data


def test_web_login_rate_limit_returns_429():
    client = make_client()

    responses = [
        client.post(
            "/login",
            data={"username": "unknown-test-user", "password": "wrong"},
        )
        for _ in range(6)
    ]

    assert any(response.status_code == 429 for response in responses)
def test_api_login_rate_limit_returns_429():
    client = make_client()

    responses = [
        client.post(
            "/api/v1/auth/login",
            json={"username": "unknown-test-user", "password": "wrong"},
        )
        for _ in range(6)
    ]

    assert any(response.status_code == 429 for response in responses)

def test_login_allowed_after_lockout_expires():
    client = make_client()

    # Simulate an account whose lockout expired.
    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        user.failed_logins = 5
        user.locked_until = utcnow() - timedelta(minutes=1)
        db.session.commit()

    # Correct password should work after lockout expiry.
    response = client.post(
        "/login",
        data={"username": "voter1", "password": PASSWORD},
    )

    assert response.status_code == 302

    # Verify the lockout information was cleared.
    with client.application.app_context():
        user = User.query.filter_by(username="voter1").first()
        assert user.failed_logins == 0
        assert user.locked_until is None