# R14 tests: classic SQL injection payloads must be rejected or stored as plain text
import pathlib
import re

from sqlalchemy import inspect

from app import db
from app.models.user import User
from tests.helpers import make_client, get_token, auth_header

PAYLOADS = [
    "' OR '1'='1",
    "admin'--",
    "'; DROP TABLE users; --",
    "' UNION SELECT username, password_hash FROM users --",
]

TABLES = {'users', 'electors', 'ballots', 'participation', 'audit_log'}


def tables_still_exist(client):
    with client.application.app_context():
        names = set(inspect(db.engine).get_table_names())
    return TABLES <= names


def test_login_page_rejects_injection():
    client = make_client()
    for payload in PAYLOADS:
        response = client.post('/login', data={'username': payload, 'password': payload})
        # a successful login would redirect (302); a refused one stays on the page
        assert response.status_code != 302, f'login bypassed with {payload!r}'
    assert tables_still_exist(client)


def test_api_login_rejects_injection():
    client = make_client()
    for payload in PAYLOADS:
        response = client.post('/api/v1/auth/login',
                               json={'username': payload, 'password': payload})
        assert response.status_code in (400, 401), f'API login bypassed with {payload!r}'
        assert 'access_token' not in (response.get_json() or {})
    assert tables_still_exist(client)


def test_injection_in_enrolment_is_plain_text():
    client = make_client()
    token = get_token(client, 'voter1')
    payload = "'; DROP TABLE electors; --"
    response = client.put('/api/v1/enrolment', headers=auth_header(token),
                          json={'address': payload})
    # either rejected by validation (R08) or saved as harmless text
    assert response.status_code in (200, 400)
    if response.status_code == 200:
        data = client.get('/api/v1/enrolment', headers=auth_header(token)).get_json()
        assert data['address'] == payload
    assert tables_still_exist(client)


def test_injection_in_register_does_not_break_database():
    client = make_client()
    token = get_token(client, 'staff1')
    with client.application.app_context():
        users_before = User.query.count()
    for payload in PAYLOADS:
        client.post('/api/v1/electors', headers=auth_header(token), json={
            'given_name': payload, 'family_name': payload, 'dob': '1980-02-03',
            'address': payload, 'division_id': 1})
    assert tables_still_exist(client)
    with client.application.app_context():
        assert User.query.count() == users_before


def test_no_raw_sql_built_from_strings():
    """Guard: nobody builds SQL with f-strings, + or % in the app code."""
    risky = re.compile(r'(execute|text)\(\s*(f["\']|["\'].*["\']\s*(\+|%))')
    for path in pathlib.Path('app').rglob('*.py'):
        for number, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
            assert not risky.search(line), f'raw SQL built from a string: {path}:{number}'
