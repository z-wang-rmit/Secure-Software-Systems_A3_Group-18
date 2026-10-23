from app.models import Candidate
from tests.helpers import make_client, get_token, auth_header, login

NEW_CANDIDATE = {'election_id': 1, 'division_id': 1, 'name': 'Z. New', 'party': 'Ind', 'ballot_order': 5}


def candidate_exists(client, name):
    with client.application.app_context():
        return Candidate.query.filter_by(name=name).first() is not None


def test_delegate_can_propose_candidate():
    # R19: the API creates a proposal, not a candidate
    client = make_client()
    token = get_token(client, 'delegate1')
    response = client.post('/api/v1/candidates', headers=auth_header(token), json=NEW_CANDIDATE)
    assert response.status_code == 201
    assert response.get_json()['status'] == 'pending'


def test_proposal_is_not_on_the_ballot_yet():
    # R19: one delegate alone can't change the ballot
    client = make_client()
    login(client, 'delegate1')
    client.post('/delegate/candidates', data=NEW_CANDIDATE)
    assert not candidate_exists(client, 'Z. New')


def test_voter_cannot_add_candidate():
    client = make_client()
    token = get_token(client, 'voter1')
    response = client.post('/api/v1/candidates', headers=auth_header(token), json={})
    assert response.status_code == 403
