from dataclasses import replace
import pymupdf

from app.ingestion import ingest

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


def test_startup_and_missing_index(tmp_path):
    settings = replace(Settings(), chroma_dir=tmp_path / 'missing', llm_api_key='')
    with TestClient(create_app(settings)) as client:
        page = client.get('/')
        assert page.status_code == 200
        assert '<html lang="en">' in page.text
        assert client.get('/static/app.js').status_code == 200
        info = client.get('/api/appliances').json()
        assert len(info['documents']) == 3
        assert info['index_ready'] is False
        assert info['llm_ready'] is False
        response = client.post('/api/chat', json={'appliance': 'washing-machine', 'question': 'Child lock?'})
        assert response.status_code == 503
        assert 'python -m scripts.ingest' in response.json()['detail']


def test_clarification_validation_and_registered_routes(tmp_path):
    pdf_dir = tmp_path / 'pdfs'
    pdf_dir.mkdir()
    for filename in ('Bosch-WAV28EH3GB-Washing-Machine.pdf', 'Bosch-SMS8ZDI86M-Dishwasher.pdf', 'Bosch-TIS-3.3-Coffee-Machine.pdf'):
        with pymupdf.open() as pdf:
            pdf.new_page()
            pdf.save(pdf_dir / filename)
    with TestClient(create_app(replace(Settings(), chroma_dir=tmp_path, pdf_dir=pdf_dir))) as client:
        response = client.post('/api/chat', json={'question': 'How do I clean it?'})
        assert response.json()['status'] == 'clarification'
        assert 'Which appliance' in response.json()['answer']
        for question in ('', ' ', 'x' * 2001):
            assert client.post('/api/chat', json={'appliance': 'dishwasher', 'question': question}).status_code == 422
        assert client.get('/manuals/not-registered').status_code == 404
        assert client.get('/manuals/.env').status_code == 404
        assert client.get('/manuals/%2e%2e%2f.env').status_code == 404
        assert client.get('/.env').status_code == 404
        assert 'script-src' in client.get('/').headers['Content-Security-Policy']
        for id_ in ('washing-machine', 'dishwasher', 'coffee-machine'):
            response = client.get('/manuals/' + id_)
            assert response.status_code == 200
            assert response.content.startswith(b'%PDF')
            assert response.headers['content-type'] == 'application/pdf'
            assert 'inline' in response.headers['content-disposition']


def test_missing_credentials_existing_index(corpus):
    settings = corpus
    ingest(settings)
    with TestClient(create_app(settings)) as client:
        response = client.post('/api/chat', json={'appliance': 'washing-machine', 'question': 'Child lock?'})
        assert response.status_code == 503
        assert 'LLM_API_KEY is missing' in response.json()['detail']
