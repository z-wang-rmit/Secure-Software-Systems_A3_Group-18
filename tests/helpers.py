# Helper functions shared by all the test files
import pyotp
from app import create_app, db
from app.models import User

PASSWORD = 'test-password-123'
TEST_TOTP_SECRET = 'JBSWY3DPEHPK3PXP'


def make_client(csrf=False):
    """Create a test client with a fresh in-memory database."""
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET_KEY': 'test-jwt-secret-key-for-tests-only',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'SEED_PASSWORD': PASSWORD,
        'BCRYPT_ROUNDS': 4,
        'WTF_CSRF_ENABLED': csrf,
    })

    # Give seeded test accounts a known MFA secret.
    # Individual enrollment tests can clear it when needed.
    with app.app_context():
        users = User.query.all()
        for user in users:
            user.totp_secret = TEST_TOTP_SECRET
        db.session.commit()

    return app.test_client()


def current_code():
    """Generate the current TOTP code for the test secret."""
    return pyotp.TOTP(TEST_TOTP_SECRET).now()


def login(client, username):
    """Complete web login using password and MFA."""
    response = client.post(
        '/login',
        data={'username': username, 'password': PASSWORD},
        follow_redirects=False,
    )
    assert response.status_code == 302, f'password step for {username} failed'
    assert response.headers['Location'].endswith('/mfa/verify')

    response = client.post(
        '/mfa/verify',
        data={'code': current_code()},
        follow_redirects=False,
    )
    assert response.status_code == 302, f'MFA login as {username} failed'


def get_token(client, username):
    """Complete API login using password and MFA, then return the JWT."""
    response = client.post(
        '/api/v1/auth/login',
        json={
            'username': username,
            'password': PASSWORD,
            'code': current_code(),
        },
    )
    assert response.status_code == 200, f'API login as {username} failed'
    return response.get_json()['access_token']


def auth_header(token):
    """The header that sends a JWT with an API request."""
    return {'Authorization': f'Bearer {token}'}