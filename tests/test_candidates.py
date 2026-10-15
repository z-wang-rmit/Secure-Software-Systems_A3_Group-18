from tests.helpers import make_client, get_token, auth_header


def test_delegate_can_add_candidate():
    client = make_client()
    token = get_token(client, 'delegate1')
    response = client.post('/api/v1/candidates', headers=auth_header(token), json={
        'election_id': 1, 'division_id': 1, 'name': 'Z. New', 'party': 'Ind', 'ballot_order': 5})
    assert response.status_code == 201


def test_voter_cannot_add_candidate():
    client = make_client()
    token = get_token(client, 'voter1')
    response = client.post('/api/v1/candidates', headers=auth_header(token), json={})
    assert response.status_code == 403
