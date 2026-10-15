from tests.helpers import make_client, get_token, auth_header


def test_voter_sees_enrolment():
    client = make_client()
    token = get_token(client, 'voter1')
    response = client.get('/api/v1/enrolment', headers=auth_header(token))
    assert response.status_code == 200
    assert response.get_json()['enrolled'] is True


def test_staff_can_register_elector():
    client = make_client()
    token = get_token(client, 'staff1')
    response = client.post('/api/v1/electors', headers=auth_header(token), json={
        'given_name': 'Ann', 'family_name': 'Lee', 'dob': '1980-02-03',
        'address': '1 Test St', 'division_id': 1})
    assert response.status_code == 201


def test_missing_fields_rejected():
    client = make_client()
    token = get_token(client, 'staff1')
    response = client.post('/api/v1/electors', headers=auth_header(token), json={'given_name': 'Ann'})
    assert response.status_code == 400
