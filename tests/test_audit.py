from tests.helpers import make_client, login


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
