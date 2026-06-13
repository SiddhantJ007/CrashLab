def test_health_endpoint(client):
    response = client.get('/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['ok'] is True
    assert payload['targets'] >= 2


def test_targets_endpoint_hides_webarena(client):
    response = client.get('/api/targets')
    assert response.status_code == 200
    payload = response.json()
    assert 'flowise_std' in payload
    assert 'langflow_std' in payload
    assert all(item.get('kind') != 'webarena' for item in payload.values())


def test_history_endpoint_returns_runs_key(client):
    response = client.get('/api/history')
    assert response.status_code == 200
    payload = response.json()
    assert 'runs' in payload
    assert isinstance(payload['runs'], list)


def test_suite_preview_endpoint_returns_cases(client):
    response = client.get('/api/targets/flowise_std/suite-preview?mode=demo')
    assert response.status_code == 200
    payload = response.json()
    assert payload['source'] == 'explicit_target_spec'
    assert len(payload['cases']) == 5
