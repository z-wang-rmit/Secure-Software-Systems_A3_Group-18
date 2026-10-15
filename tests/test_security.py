from tests.helpers import make_client


def test_health_check():
    client = make_client()
    assert client.get('/health').get_json()['status'] == 'healthy'
