from dataclasses import replace
import json
import sys

from fastapi.testclient import TestClient
import httpx

from app.generation import UNKNOWN
from app.ingestion import ingest
from app.main import create_app
from scripts import query


def test_cli_and_web_complete_pipeline_with_mocked_provider(corpus, monkeypatch, capsys):
    settings = replace(corpus, llm_api_key='test-placeholder')
    ingest(settings)
    original_client = httpx.Client
    def handler(request):
        payload = json.loads(request.content)
        user_data = json.loads(payload['input'])
        if 'weather' in user_data['question'].lower():
            raw = {'supported': False, 'blocks': []}
        else:
            source = user_data['untrusted_reference_data'][0]
            raw = {'supported': True,
                   'blocks': [{'text': 'This manual discusses child lock instructions.',
                               'evidence': [{'source_id': source['source_id']}]}]}
        return httpx.Response(200, json={'status': 'completed', 'output': [
            {'type': 'message', 'content': [{'type': 'output_text', 'text': json.dumps(raw)}]}]})
    # Only generation's client factory is replaced; no live socket or API is used.
    class MockProviderClient(original_client):
        def __init__(self, *args, **kwargs):
            kwargs['transport'] = httpx.MockTransport(handler)
            super().__init__(*args, **kwargs)
    monkeypatch.setattr('app.generation.httpx.Client', MockProviderClient)
    monkeypatch.setattr(query, 'Settings', lambda: settings)
    monkeypatch.setattr(sys, 'argv', ['query', '--appliance', 'washing-machine', '--json', 'How does child lock work?'])
    assert query.main() == 0
    result = json.loads(capsys.readouterr().out)
    assert result['status'] == 'answered'
    assert '[washing-machine.pdf, p.' in result['answer']
    assert all(source['appliance'] == 'washing-machine' for source in result['sources'])
    with TestClient(create_app(settings)) as client:
        result = client.post('/api/chat', json={'appliance': 'washing-machine', 'question': 'How does child lock work?'})
        assert result.status_code == 200
        assert result.json()['status'] == 'answered'
        result = client.post('/api/chat', json={'appliance': 'dishwasher', 'question': 'What is tomorrow’s weather?'})
        assert result.json()['answer'] == UNKNOWN
