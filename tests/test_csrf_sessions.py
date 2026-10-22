# Tests for CSRF protection and session security.

import re
from datetime import timedelta

from tests.helpers import (
    PASSWORD, make_client, current_code,
)


def _form_token(client):
    html = client.get('/login').get_data(as_text=True)
    match = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert match is not None, 'CSRF token was not found in login form'
    return match.group(1)


def test_post_without_csrf_token_is_rejected():
    client = make_client(csrf=True)
    response = client.post(
        '/login',
        data={'username': 'voter1', 'password': PASSWORD},
    )
    assert response.status_code == 400


def test_post_with_csrf_token_is_accepted():
    client = make_client(csrf=True)
    token = _form_token(client)
    response = client.post(
        '/login',
        data={
            'username': 'voter1',
            'password': PASSWORD,
            'csrf_token': token,
        },
    )
    assert response.status_code == 302
    assert response.headers['Location'].endswith('/mfa/verify')


def test_api_login_does_not_need_csrf_token():
    client = make_client(csrf=True)
    response = client.post(
        '/api/v1/auth/login',
        json={
            'username': 'voter1',
            'password': PASSWORD,
            'code': current_code(),
        },
    )
    assert response.status_code == 200
    assert response.get_json().get('access_token')


def test_session_cookie_has_security_flags():
    client = make_client()
    response = client.post(
        '/login',
        data={'username': 'voter1', 'password': PASSWORD},
    )
    cookie = ' '.join(response.headers.getlist('Set-Cookie'))
    assert 'HttpOnly' in cookie
    assert 'Secure' in cookie
    assert 'SameSite=Strict' in cookie
    assert response.headers['Location'].endswith('/mfa/verify')


def test_session_expires_after_15_minutes_of_inactivity():
    client = make_client()
    assert client.application.config['PERMANENT_SESSION_LIFETIME'] == timedelta(minutes=15)