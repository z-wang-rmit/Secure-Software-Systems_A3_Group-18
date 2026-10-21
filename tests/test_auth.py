from tests.helpers import (
    make_client, login, get_token, PASSWORD, current_code,
)


def test_login_page_loads():
    client = make_client()
    assert client.get('/login').status_code == 200


def test_valid_login():
    client = make_client()
    login(client, 'voter1')


def test_wrong_password_rejected():
    client = make_client()
    response = client.post(
        '/login',
        data={'username': 'voter1', 'password': 'wrong'},
    )
    assert response.status_code == 401


def test_api_login_returns_token():
    client = make_client()
    response = client.post(
        '/api/v1/auth/login',
        json={
            'username': 'voter1',
            'password': PASSWORD,
            'code': current_code(),
        },
    )
    assert response.status_code == 200
    assert response.get_json()['user']['role'] == 'voter'
    assert response.get_json()['access_token']


def test_api_login_without_code_rejected():
    client = make_client()
    response = client.post(
        '/api/v1/auth/login',
        json={'username': 'voter1', 'password': PASSWORD},
    )
    assert response.status_code == 400
    assert 'access_token' not in response.get_json()


def test_api_login_with_wrong_code_rejected():
    client = make_client()
    response = client.post(
        '/api/v1/auth/login',
        json={
            'username': 'voter1',
            'password': PASSWORD,
            'code': '000000',
        },
    )
    assert response.status_code == 401
    assert 'access_token' not in response.get_json()


def test_api_without_token_rejected():
    client = make_client()
    assert client.get('/api/v1/enrolment').status_code == 401

def test_password_only_does_not_grant_ballot_access():
    client = make_client()

    response = client.post(
        '/login',
        data={'username': 'voter1', 'password': PASSWORD},
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/mfa/verify')

    # The password step must not create an authenticated session.
    ballot_response = client.get('/ballot', follow_redirects=False)
    assert ballot_response.status_code == 302
    assert '/login' in ballot_response.headers['Location']


def test_mfa_setup_requires_pending_login():
    client = make_client()

    response = client.get('/mfa/setup', follow_redirects=False)

    assert response.status_code == 302
    assert '/login' in response.headers['Location']