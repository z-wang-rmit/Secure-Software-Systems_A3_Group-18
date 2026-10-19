# R08 tests: the server rejects bad input with 400, whatever the browser sends
from tests.helpers import auth_header, get_token, make_client

GOOD = {'given_name': 'Ann', 'family_name': "O'Brien-Lee", 'dob': '1980-02-03',
        'address': '1 Test St, Melbourne VIC 3000', 'division_id': 1}


def register(client, token, **changes):
    return client.post('/api/v1/electors', headers=auth_header(token), json={**GOOD, **changes})


def test_good_elector_is_accepted():
    client = make_client()
    token = get_token(client, 'staff1')
    assert register(client, token).status_code == 201


def test_bad_elector_fields_are_rejected():
    client = make_client()
    token = get_token(client, 'staff1')
    bad_inputs = [
        {'given_name': 'A' * 51},                      # too long
        {'given_name': '<script>alert(1)</script>'},   # not letters
        {'family_name': 'Smith1'},                     # digit in a name
        {'dob': '03/02/1980'},                         # wrong format
        {'dob': '1980-02-30'},                         # not a real date
        {'dob': '2015-01-01'},                         # under 18
        {'address': 'x' * 201},                        # too long
        {'address': '<b>1 Test St</b>'},               # HTML characters
        {'division_id': 999},                          # division does not exist
        {'division_id': 'abc'},                        # not a number
    ]
    for change in bad_inputs:
        response = register(client, token, **change)
        assert response.status_code == 400, f'accepted bad input {change}'
        assert 'error' in response.get_json()


def test_bad_address_update_is_rejected():
    client = make_client()
    token = get_token(client, 'voter1')
    for address in ['', 'x' * 201, '<script>alert(1)</script>', 123]:
        response = client.put('/api/v1/enrolment', headers=auth_header(token),
                              json={'address': address})
        assert response.status_code == 400, f'accepted bad address {address!r}'


def test_duplicate_ballot_numbers_are_rejected():
    client = make_client()
    token = get_token(client, 'voter1')
    candidates = client.get('/api/v1/elections/1/candidates',
                            headers=auth_header(token)).get_json()
    ids = [str(c['id']) for c in candidates]
    assert len(ids) == 4
    for prefs in [{i: 1 for i in ids},                              # all number 1
                  {i: n + 2 for n, i in enumerate(ids)},             # starts at 2
                  {i: str(n + 1) for n, i in enumerate(ids)}]:       # text, not numbers
        response = client.post('/api/v1/ballots', headers=auth_header(token),
                               json={'election_id': 1, 'preferences': prefs})
        assert response.status_code == 400, f'accepted bad ballot {prefs}'
