from app.models import AuditLog, Candidate, CandidateProposal
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


def propose_as_delegate1(client):
    """delegate1 proposes NEW_CANDIDATE through the web form, then logs out"""
    login(client, 'delegate1')
    client.post('/delegate/candidates', data=NEW_CANDIDATE)
    client.post('/logout')
    with client.application.app_context():
        return CandidateProposal.query.filter_by(name='Z. New').one().id


def test_proposer_cannot_approve_own_proposal():
    # R19: separation of duties, the second approval must come from someone else
    client = make_client()
    proposal_id = propose_as_delegate1(client)
    login(client, 'delegate1')
    response = client.post(f'/delegate/candidates/proposals/{proposal_id}/approve')
    assert response.status_code == 403
    assert not candidate_exists(client, 'Z. New')


def test_other_delegate_can_approve():
    client = make_client()
    proposal_id = propose_as_delegate1(client)
    login(client, 'delegate2')
    response = client.post(f'/delegate/candidates/proposals/{proposal_id}/approve')
    assert response.status_code == 302
    assert candidate_exists(client, 'Z. New')
    with client.application.app_context():
        entry = AuditLog.query.filter_by(action='candidate_approved').one()
        assert entry.detail['proposed_by'] != entry.actor_id


def test_voter_cannot_approve():
    client = make_client()
    proposal_id = propose_as_delegate1(client)
    login(client, 'voter1')
    assert client.post(f'/delegate/candidates/proposals/{proposal_id}/approve').status_code == 403
