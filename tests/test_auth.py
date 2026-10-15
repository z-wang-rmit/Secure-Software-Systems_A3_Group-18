from tests.helpers import make_client, login, get_token, PASSWORD


def test_login_page_loads():
    client = make_client()
    assert client.get('/login').status_code == 200


def test_valid_login():
    client = make_client()
    login(client, 'voter1')


def test_wrong_password_rejected():
    client = make_client()
    response = client.post('/login', data={'username': 'voter1', 'password': 'wrong'})
    assert response.status_code == 401


def test_api_login_returns_token():
    client = make_client()
    response = client.post('/api/v1/auth/login', json={'username': 'voter1', 'password': PASSWORD})
    assert response.status_code == 200
    assert response.get_json()['user']['role'] == 'voter'
    assert get_token(client, 'voter1')


def test_api_without_token_rejected():
    client = make_client()
    assert client.get('/api/v1/enrolment').status_code == 401
