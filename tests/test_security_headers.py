#this python file tests for logged in sessions, checking for what i changed for r15

from tests.helpers import auth_header, get_token, login, make_client

XSS = '<script>alert(1)</script>'

def test_every_response_has_nosniff_and_frame_options():
    client = make_client()
    response = client.get('/login')
    assert response.headers['X-Content-Type-Options'] == 'nosniff'
    assert response.headers['X-Frame-Options'] == 'DENY'


def test_logged_in_pages_are_not_cached():
    client = make_client()
    login(client, 'voter1')
    response = client.get('/enrolment')
    assert response.status_code == 200
    assert 'no-store' in response.headers.get('Cache-Control', '')


def test_api_responses_with_a_token_are_not_cached():
    client = make_client()
    token = get_token(client, 'voter1')
    response = client.get('/api/v1/enrolment', headers=auth_header(token))
    assert response.status_code == 200
    assert 'no-store' in response.headers.get('Cache-Control', '')


def test_script_in_address_is_rejected_and_never_shown():
    client = make_client()
    login(client, 'voter1')
    response = client.post('/enrolment', data={'address': XSS})
    assert response.status_code < 500
    assert XSS not in response.get_data(as_text=True)
    # and it was not stored
    assert XSS not in client.get('/enrolment').get_data(as_text=True)


def test_user_text_is_html_escaped_on_the_page():
    client = make_client()
    login(client, 'voter1')
    client.post('/enrolment', data={'address': "5 O'Brien St"})
    html = client.get('/enrolment').get_data(as_text=True)
    assert 'O&#39;Brien' in html
    assert "O'Brien" not in html