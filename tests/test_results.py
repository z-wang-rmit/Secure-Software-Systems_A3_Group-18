from tests.helpers import make_client, login, get_token
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
