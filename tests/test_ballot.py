from tests.helpers import make_client, get_token, auth_header


def number_every_candidate(client, token):
    """Ask for the voter's candidates and number them 1, 2, 3, ..."""
    response = client.get('/api/v1/elections/1/candidates', headers=auth_header(token))
    prefs = {}
    number = 1
    for candidate in response.get_json():
        prefs[str(candidate['id'])] = number
        number += 1
    return prefs


def cast(client, token, prefs):
    return client.post('/api/v1/ballots', headers=auth_header(token),
                       json={'election_id': 1, 'preferences': prefs})


def test_voter_can_vote_once():
    client = make_client()
    token = get_token(client, 'voter1')
    prefs = number_every_candidate(client, token)

    first = cast(client, token, prefs)
    assert first.status_code == 201
    assert len(first.get_json()['receipt']) == 64

    second = cast(client, token, prefs)
    assert second.status_code == 400


def test_incomplete_ballot_rejected():
    client = make_client()
    token = get_token(client, 'voter2')
    assert cast(client, token, {'1': 1}).status_code == 400
