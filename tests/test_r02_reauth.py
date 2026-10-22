
from tests.helpers import make_client, login


def test_recent_password_allows_staff_registration_page():
    client = make_client()
    login(client, 'staff1')

    response = client.get('/staff/electors')

    assert response.status_code == 200


def test_expired_password_redirects_critical_action_to_reauth():
    client = make_client()
    login(client, 'staff1')

    with client.session_transaction() as sess:
        sess['password_verified_at'] = 1

    response = client.post('/staff/electors', data={}, follow_redirects=False)

    assert response.status_code == 302
    assert '/reauthenticate' in response.headers['Location']


def test_reauth_page_requires_login():
    client = make_client()

    response = client.get('/reauthenticate', follow_redirects=False)

    assert response.status_code == 302
    assert '/login' in response.headers['Location']


def test_staff_without_mfa_is_redirected_to_setup():
    client = make_client()
    login(client, 'staff1')

    with client.session_transaction() as sess:
        user_id = sess['user_id']

    app = client.application
    with app.app_context():
        from app import db
        from app.models import User

        user = db.session.get(User, user_id)
        user.totp_secret = None
        db.session.commit()

    response = client.get('/staff/electors', follow_redirects=False)

    assert response.status_code == 302
    assert '/mfa/setup' in response.headers['Location']


def test_delegate_without_mfa_is_redirected_to_setup():
    client = make_client()
    login(client, 'delegate1')

    with client.session_transaction() as sess:
        user_id = sess['user_id']

    app = client.application
    with app.app_context():
        from app import db
        from app.models import User

        user = db.session.get(User, user_id)
        user.totp_secret = None
        db.session.commit()

    response = client.get('/delegate/candidates', follow_redirects=False)

    assert response.status_code == 302
    assert '/mfa/setup' in response.headers['Location']


def test_auditor_without_mfa_is_redirected_to_setup():
    client = make_client()
    login(client, 'auditor1')

    with client.session_transaction() as sess:
        user_id = sess['user_id']

    app = client.application
    with app.app_context():
        from app import db
        from app.models import User

        user = db.session.get(User, user_id)
        user.totp_secret = None
        db.session.commit()

    response = client.get('/auditor/audit', follow_redirects=False)

    assert response.status_code == 302
    assert '/mfa/setup' in response.headers['Location']


def test_reauthentication_accepts_correct_password():
    from tests.helpers import PASSWORD

    client = make_client()
    login(client, 'staff1')

    response = client.post(
        '/reauthenticate',
        data={
            'password': PASSWORD,
            'next': '/staff/electors',
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers['Location'].endswith('/staff/electors')

    with client.session_transaction() as sess:
        assert sess['password_verified_at'] > 1



def test_reauthentication_rejects_incorrect_password():
    client = make_client()
    login(client, 'staff1')

    # Simulate an expired password-verification timestamp.
    with client.session_transaction() as sess:
        sess['password_verified_at'] = 1

    response = client.post(
        '/reauthenticate',
        data={
            'password': 'definitely-wrong-password',
            'next': '/staff/electors',
        },
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert b'Incorrect password' in response.data

    # An incorrect password must not refresh the timestamp.
    with client.session_transaction() as sess:
        assert sess['password_verified_at'] == 1


def test_api_critical_action_requires_fresh_jwt():
    from tests.helpers import get_token, auth_header

    client = make_client()
    token = get_token(client, 'staff1')

    # A valid but non-fresh token must not authorize a critical action.
    from flask_jwt_extended import create_access_token

    with client.application.app_context():
        non_fresh_token = create_access_token(
            identity='1',
            fresh=False,
        )

    response = client.post(
        '/api/v1/electors',
        headers=auth_header(non_fresh_token),
        json={
            'given_name': 'Ann',
            'family_name': 'Lee',
            'dob': '1980-02-03',
            'address': '1 Test St',
            'division_id': 1,
        },
    )

    assert response.status_code == 401


def test_api_login_returns_fresh_jwt():
    from tests.helpers import get_token, auth_header

    client = make_client()
    token = get_token(client, 'staff1')

    # The normal MFA login should initially issue a fresh token.
    response = client.post(
        '/api/v1/electors',
        headers=auth_header(token),
        json={
            'given_name': 'Ann',
            'family_name': 'Lee',
            'dob': '1980-02-03',
            'address': '1 Test St',
            'division_id': 1,
        },
    )

    assert response.status_code == 201


def test_api_reauthentication_with_correct_password_and_mfa():
    from tests.helpers import get_token, auth_header, PASSWORD, current_code

    client = make_client()
    token = get_token(client, 'staff1')

    response = client.post(
        '/api/v1/auth/reauthenticate',
        headers=auth_header(token),
        json={
            'password': PASSWORD,
            'code': current_code(),
        },
    )

    assert response.status_code == 200
    assert 'access_token' in response.get_json()


def test_api_reauthentication_rejects_wrong_password():
    from tests.helpers import get_token, auth_header, current_code

    client = make_client()
    token = get_token(client, 'staff1')

    response = client.post(
        '/api/v1/auth/reauthenticate',
        headers=auth_header(token),
        json={
            'password': 'definitely-wrong-password',
            'code': current_code(),
        },
    )

    assert response.status_code == 401
    assert 'access_token' not in response.get_json()

def test_expired_api_authentication_requires_reauthentication():
    from tests.helpers import get_token, auth_header, PASSWORD, current_code
    from flask_jwt_extended import create_access_token

    client = make_client()
    get_token(client, 'staff1')

    # Simulate a token whose password verification was over five minutes ago.
    with client.application.app_context():
        expired_token = create_access_token(
            identity='1',
            fresh=True,
            additional_claims={'password_verified_at': 1},
        )

    payload = {
        'given_name': 'Ann',
        'family_name': 'Lee',
        'dob': '1980-02-03',
        'address': '1 Test St',
        'division_id': 1,
    }

    response = client.post(
        '/api/v1/electors',
        headers=auth_header(expired_token),
        json=payload,
    )
    assert response.status_code == 401

    reauth_response = client.post(
        '/api/v1/auth/reauthenticate',
        headers=auth_header(expired_token),
        json={'password': PASSWORD, 'code': current_code()},
    )
    assert reauth_response.status_code == 200

    new_token = reauth_response.get_json()['access_token']
    retry_response = client.post(
        '/api/v1/electors',
        headers=auth_header(new_token),
        json=payload,
    )
    assert retry_response.status_code == 201
