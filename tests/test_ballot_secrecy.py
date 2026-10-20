import app.routes.ballot as ballot_routes
from app.models import Ballot, Participation, AuditLog
from tests.helpers import make_client, get_token
from tests.test_ballot import number_every_candidate, cast


def test_failed_vote_does_not_print_secret_details(monkeypatch, capsys):
    def fake_seal_ballot(prefs):
        raise RuntimeError('SECRET-RECEIPT-123')

    monkeypatch.setattr(ballot_routes, 'seal_ballot', fake_seal_ballot)

    client = make_client()
    token = get_token(client, 'voter1')
    prefs = number_every_candidate(client, token)

    response = cast(client, token, prefs)
    assert response.status_code == 500

    printed = capsys.readouterr().out
    assert 'SECRET-RECEIPT-123' not in printed


def test_ballot_table_has_no_voter_link():
    cols = set()
    for col in Ballot.__table__.columns:
        cols.add(col.name)
        for bad in ['user', 'elector', 'voter', 'ip_address', 'time']:
            assert bad not in col.name
    assert cols == {'id', 'election_id', 'division_id', 'sealed', 'receipt'}
    assert len(Ballot.__table__.foreign_keys) == 0


def test_audit_entry_for_vote_has_no_voter():
    client = make_client()
    token = get_token(client, 'voter1')
    prefs = number_every_candidate(client, token)

    response = cast(client, token, prefs)
    assert response.status_code == 201
    receipt = response.get_json()['receipt']

    with client.application.app_context():
        entry = AuditLog.query.filter_by(action='ballot_cast').first()
        assert entry is not None
        assert entry.actor_id is None
        assert receipt not in entry.target


def test_nothing_but_election_links_ballot_and_participation():
    ballot_cols = set()
    for col in Ballot.__table__.columns:
        ballot_cols.add(col.name)

    part_cols = set()
    for col in Participation.__table__.columns:
        part_cols.add(col.name)

    shared = ballot_cols & part_cols
    assert shared <= {'election_id', 'division_id'}