# R05 tests: every role against every protected page (style of the Week 5 test_rbac.py)
from tests.helpers import make_client, login

PAGES = ['/enrolment', '/ballot', '/staff/electors', '/delegate/candidates',
         '/auditor/audit', '/auditor/count']

# Which pages each role is allowed to open
ALLOWED = {
    'voter1': {'/enrolment', '/ballot'},
    'staff1': {'/staff/electors'},
    'delegate1': {'/delegate/candidates'},
    'auditor1': {'/auditor/audit', '/auditor/count'},
}


def test_every_role_against_every_page():
    for username, allowed in ALLOWED.items():
        client = make_client()
        login(client, username)
        for page in PAGES:
            expected = 200 if page in allowed else 403
            got = client.get(page).status_code
            assert got == expected, f'{username} {page}: expected {expected}, got {got}'


def test_new_route_without_a_rule_is_denied():
    client = make_client()
    app = client.application

    @app.route('/secret-test-page')   # no @role_required on purpose
    def secret_test_page():
        return 'should never be seen'

    login(client, 'voter1')
    assert client.get('/secret-test-page').status_code == 403


def test_api_without_token_is_401():
    client = make_client()
    assert client.get('/api/v1/enrolment').status_code == 401


def test_public_pages_still_open():
    client = make_client()
    for page in ['/', '/login', '/register', '/health']:
        assert client.get(page).status_code == 200
