import base64
from cryptography.hazmat.primitives import serialization
from tests.helpers import make_client, login, get_token
from app import db
from app.models import AuditLog, Ballot, Election, Result
from app.utils.signing import canonical_bytes
from tests.test_ballot import number_every_candidate, cast


def test_close_count_and_publish():
    client = make_client()

    # voter1 votes
    token = get_token(client, 'voter1')
    assert cast(client, token, number_every_candidate(client, token)).status_code == 201

    # the auditor closes and counts the election
    login(client, 'auditor1')
    assert client.post('/auditor/elections/1/close').status_code == 302
    assert client.post('/auditor/elections/1/count').status_code == 302

    # anyone can fetch and check the results
    results = client.get('/api/v1/results/1').get_json()
    for result in results:
        if result['payload']['division'] == 'Melbourne':
            assert result['payload']['ballots_total'] == 1
    assert client.get('/api/v1/results/1/verify').get_json()['valid'] is True


def test_cannot_count_open_election():
    client = make_client()
    login(client, 'auditor1')
    client.post('/auditor/elections/1/count')
    assert client.get('/api/v1/results/1').get_json() == []


def vote_and_close(client):
    """voter1 votes, then auditor1 logs in and closes election 1"""
    token = get_token(client, 'voter1')
    assert cast(client, token, number_every_candidate(client, token)).status_code == 201
    login(client, 'auditor1')
    assert client.post('/auditor/elections/1/close').status_code == 302


def test_tampered_ballot_stops_the_count():
    # R18: sha256(sealed) must match the receipt, or nothing is counted
    client = make_client()
    vote_and_close(client)

    # someone with database access swaps a byte in the sealed ballot
    with client.application.app_context():
        ballot = Ballot.query.first()
        ballot.sealed = bytes([ballot.sealed[0] ^ 1]) + ballot.sealed[1:]
        db.session.commit()
        bad_id = ballot.id

    client.post('/auditor/elections/1/count')

    assert client.get('/api/v1/results/1').get_json() == []
    with client.application.app_context():
        assert db.session.get(Election, 1).status == 'closed'
        entry = AuditLog.query.filter_by(action='count_refused').one()
        assert bad_id in entry.detail['bad_ballots']


def test_changed_result_fails_verification():
    # R18: editing a stored result breaks its signature
    client = make_client()
    vote_and_close(client)
    client.post('/auditor/elections/1/count')

    with client.application.app_context():
        result = Result.query.first()
        result.payload = dict(result.payload, elected='Someone Else')
        db.session.commit()

    assert client.get('/api/v1/results/1/verify').get_json()['valid'] is False


def test_only_auditor_can_count():
    client = make_client()
    vote_and_close(client)
    client.post('/logout')
    login(client, 'delegate1')
    assert client.post('/auditor/elections/1/count').status_code == 403


def test_anyone_can_verify_with_the_published_key():
    # R18: an outside system needs only the API and the public key
    client = make_client()
    vote_and_close(client)
    client.post('/auditor/elections/1/count')
    client.post('/logout')

    response = client.get('/api/v1/results/public-key')
    assert response.status_code == 200
    assert response.mimetype == 'text/plain'
    public_key = serialization.load_pem_public_key(response.data)

    for result in client.get('/api/v1/results/1').get_json():
        public_key.verify(base64.b64decode(result['signature']), canonical_bytes(result['payload']))


def test_results_page_shows_signature_check():
    client = make_client()
    vote_and_close(client)
    client.post('/auditor/elections/1/count')
    assert b'Signature valid' in client.get('/results/1').data
