# Helper functions shared by all the test files
from app import create_app

PASSWORD = 'test-password-123'


def make_client():
    """A fake browser talking to a brand-new app with a fresh in-memory database.

    The demo data is loaded: staff1, delegate1, delegate2, auditor1, and voter1-voter5
    (voter1-3 in Melbourne, voter4-5 in Sydney). They all use PASSWORD.
    """
    app = create_app({
        'TESTING': True,
        'SECRET_KEY': 'test-secret-key',
        'JWT_SECRET_KEY': 'test-jwt-secret-key-for-tests-only',
        'SQLALCHEMY_DATABASE_URI': 'sqlite://',
        'SEED_PASSWORD': PASSWORD,
        'BCRYPT_ROUNDS': 4,   # fast password hashing, for tests only
        'WTF_CSRF_ENABLED': False #this is for R16, so that its off for normal tests, but on for CSRF tests
    })
    return app.test_client()


def login(client, username):
    """Log in through the login page (for testing pages)"""
    response = client.post('/login', data={'username': username, 'password': PASSWORD})
    assert response.status_code == 302, f'login as {username} failed'


def get_token(client, username):
    """Log in through the API and return the JWT token (for testing the API)"""
    response = client.post('/api/v1/auth/login', json={'username': username, 'password': PASSWORD})
    assert response.status_code == 200, f'API login as {username} failed'
    return response.get_json()['access_token']


def auth_header(token):
    """The header that sends a JWT token with an API request"""
    return {'Authorization': f'Bearer {token}'}
