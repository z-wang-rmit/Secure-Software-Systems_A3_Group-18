import pytest
from sqlalchemy import text
from sqlalchemy.exc import DatabaseError
from app import db
from tests.helpers import make_client, login
from app.models import AuditLog
from app.utils.audit import log_event


def test_login_is_audited():
    client = make_client()
    login(client, 'voter1')
    login(client, 'auditor1')
    page = client.get('/auditor/audit').get_data(as_text=True)
    assert 'login_ok' in page


def test_voter_cannot_read_audit_log():
    client = make_client()
    login(client, 'voter1')
    assert client.get('/auditor/audit').status_code == 403


def test_secrets_are_not_stored_in_the_log():
    # R17: log_event drops protected data before saving (W5 L s22-24)
    client = make_client()
    with client.application.app_context():
        log_event(1, 'test_event', 'user:1',
                  {'password': 'hunter2-secret', 'code': '123456', 'via': 'api'})
        entry = AuditLog.query.filter_by(action='test_event').one()
        assert 'hunter2-secret' not in str(entry.detail)
        assert '123456' not in str(entry.detail)
        assert entry.detail['via'] == 'api'


def test_fake_log_lines_are_not_stored():
    # R17: a newline in a username can't start a fake log line
    client = make_client()
    client.post('/login', data={'username': 'bob\nlogin_ok user:1', 'password': 'x'})
    with client.application.app_context():
        entry = AuditLog.query.filter_by(action='login_failed').one()
        assert '\n' not in entry.target


def test_long_username_fits_in_the_log():
    # R17: target is a 128-character column, so a huge username must be cut down
    client = make_client()
    client.post('/login', data={'username': 'a' * 500, 'password': 'x'})
    with client.application.app_context():
        entry = AuditLog.query.filter_by(action='login_failed').one()
        assert len(entry.target) <= 128


def test_database_refuses_to_edit_the_log():
    # R17: a trigger stops anyone changing an entry, even with direct DB access (W7 L s17-18)
    client = make_client()
    login(client, 'voter1')
    with client.application.app_context():
        with pytest.raises(DatabaseError):
            db.session.execute(text("UPDATE audit_log SET action = 'nothing_happened'"))
        db.session.rollback()


def test_database_refuses_to_delete_the_log():
    client = make_client()
    login(client, 'voter1')
    with client.application.app_context():
        with pytest.raises(DatabaseError):
            db.session.execute(text('DELETE FROM audit_log'))
        db.session.rollback()
        assert AuditLog.query.count() > 0
