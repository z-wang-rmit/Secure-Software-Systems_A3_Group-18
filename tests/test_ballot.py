from datetime import date
import pytest
from sqlalchemy.exc import IntegrityError
from app import db
from app.models import Participation, Ballot, Elector
import app.routes.ballot as ballot_routes
from app.utils.auth import current_user
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


def test_voter_cannot_vote_for_another_divisions_candidates():
    client = make_client()
    # get Melbourne candidates using voter1
    token1 = get_token(client, 'voter1')
    melb_prefs = number_every_candidate(client, token1)

    # voter4 is in Sydney, so Melbourne candidate IDs should be rejected
    token4 = get_token(client, 'voter4')
    resp = cast(client, token4, melb_prefs)
    assert resp.status_code == 400


def test_database_refuses_a_second_participation_row():
    client = make_client()
    with client.application.app_context():
        db.session.add(Participation(election_id=1, elector_id=1, voted_on=date.today()))
        db.session.commit()
        db.session.add(Participation(election_id=1, elector_id=1, voted_on=date.today()))
        with pytest.raises(IntegrityError):
            db.session.commit()


def test_two_votes_at_the_same_moment_leave_one_ballot(monkeypatch):
    def fake_check_eligible(election):
        elector = Elector.query.filter_by(user_id=current_user().id).first()
        return elector, None

    monkeypatch.setattr(ballot_routes, 'check_eligible', fake_check_eligible)

    client = make_client()
    token = get_token(client, 'voter1')
    prefs = number_every_candidate(client, token)

    first = cast(client, token, prefs)
    assert first.status_code == 201

    second = cast(client, token, prefs)
    assert second.status_code == 400
    assert second.get_json()['error'] == 'You have already voted in this election.'

    with client.application.app_context():
        assert Ballot.query.count() == 1
        assert Participation.query.count() == 1