from tests.helpers import make_client, get_token
from tests.test_ballot import number_every_candidate, cast


def test_receipt_appears_on_public_bulletin():
    client = make_client()
    token = get_token(client, 'voter1')
    prefs = number_every_candidate(client, token)

    vote = cast(client, token, prefs)
    assert vote.status_code == 201
    receipt = vote.get_json()['receipt']

    response = client.get('/bulletin/1')
    assert response.status_code == 200
    assert receipt in response.get_data(as_text=True)