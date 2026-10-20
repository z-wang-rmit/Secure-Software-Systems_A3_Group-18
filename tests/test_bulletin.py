from tests.helpers import make_client, get_token, auth_header
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


def test_api_bulletin_lists_receipt():
    client = make_client()
    token = get_token(client, 'voter1')
    prefs = number_every_candidate(client, token)

    vote = cast(client, token, prefs)
    assert vote.status_code == 201
    receipt = vote.get_json()['receipt']

    response = client.get('/api/v1/bulletin/1')
    assert response.status_code == 200
    data = response.get_json()
    assert data['election'] is not None
    assert receipt in data['receipts']


def test_bulletin_is_public_and_contains_no_candidate_names():
    client = make_client()
    token = get_token(client, 'voter1')
    
    # Grab candidate names before voting so we know what to check for
    cand_resp = client.get('/api/v1/elections/1/candidates', headers=auth_header(token))
    assert cand_resp.status_code == 200
    candidates = cand_resp.get_json()
    candidate_names = [c['name'] for c in candidates]

    # Cast vote and save receipt
    prefs = number_every_candidate(client, token)
    vote = cast(client, token, prefs)
    assert vote.status_code == 201
    receipt = vote.get_json()['receipt']

    # Brand-new visitor with no login token can view bulletin without redirect
    visitor = make_client()
    response = visitor.get('/bulletin/1')
    assert response.status_code == 200

    # Check the page text using client to ensure receipt is shown and no candidate names leak
    page_text = client.get('/bulletin/1').get_data(as_text=True)
    assert receipt in page_text

    for name in candidate_names:
        assert name not in page_text