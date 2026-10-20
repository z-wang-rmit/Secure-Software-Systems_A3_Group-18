#this python file tests for csrf sessions, running through different scenarios related to csrf tokens.

import re
from datetime import timedelta

from tests.helpers import PASSWORD, make_client


def _form_token(client):
    html = client.get('/login').get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_post_without_csrf_token_is_rejected():
    client = make_client(csrf=True)
    response = client.post('/login', data={'username': 'voter1', 'password': PASSWORD})
    assert response.status_code == 400


def test_post_with_csrf_token_is_accepted():
    client = make_client(csrf=True)
    token = _form_token(client)
    response = client.post('/login', data={
        'username': 'voter1', 'password': PASSWORD, 'csrf_token': token})
    assert response.status_code == 302


def test_api_login_does_not_need_csrf_token():
    client = make_client(csrf=True)
    response = client.post('/api/v1/auth/login',
                           json={'username': 'voter1', 'password': PASSWORD})
    assert response.status_code == 200


def test_session_cookie_has_security_flags():
    client = make_client()
    response = client.post('/login', data={'username': 'voter1', 'password': PASSWORD})
    cookie = ' '.join(response.headers.getlist('Set-Cookie'))
    assert 'HttpOnly' in cookie
    assert 'Secure' in cookie
    assert 'SameSite=Strict' in cookie


def test_session_expires_after_15_minutes_of_inactivity():
    client = make_client()
    assert client.application.config['PERMANENT_SESSION_LIFETIME'] == timedelta(minutes=15)