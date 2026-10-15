from tests.helpers import make_client, login


def test_not_logged_in_goes_to_login():
    client = make_client()
    response = client.get('/ballot')
    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_voter_cannot_open_staff_page():
    client = make_client()
    login(client, 'voter1')
    assert client.get('/staff/electors').status_code == 403
