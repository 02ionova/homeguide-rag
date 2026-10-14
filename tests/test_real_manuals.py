"""Integration checks use actual local PDFs/embeddings and never call an LLM."""
import hashlib

import pytest

from app.config import Settings
from app.documents import documents
from app.ingestion import active_collection, extract_document, ingest
from app.retrieval import retrieve

pytestmark = pytest.mark.integration


def test_originals_metadata_and_idempotency():
    settings = Settings()
    collection = active_collection(settings)
    rows = collection.get(include=['metadatas'])
    assert len(rows['ids']) == len(set(rows['ids']))
    for doc in documents(settings):
        assert hashlib.sha256((settings.pdf_dir / doc.filename).read_bytes()).hexdigest() == doc.sha256
        chunks = extract_document(doc, settings)
        assert all(c['metadata']['page'] in doc.pages for c in chunks)
        indexed = [m for m in rows['metadatas'] if m['appliance'] == doc.id]
        assert len(indexed) == len(chunks)
        assert all(m['model'] == doc.model and m['filename'] == doc.filename and m['page'] in doc.pages for m in indexed)
        if doc.id == 'coffee-machine':
            assert all(m['page'] == 1 or 5 <= m['page'] <= 26 for m in indexed)
    before = collection.count()
    repeat = ingest(settings)
    assert repeat['status'] == 'unchanged'
    assert repeat['chunks'] == before


def test_verified_questions_retrieve_known_pages_and_stay_filtered():
    settings = Settings()
    for doc in documents(settings):
        for question in doc.questions:
            sources = retrieve(question['question'], doc.id, settings)
            assert set(question['pages']) <= {s.page for s in sources}, question
            assert all(s.appliance == doc.id and s.filename == doc.filename for s in sources)
            assert any(s.kind == 'semantic match' for s in sources)


def test_absent_question_retrieval_is_not_an_answerability_gate():
    sources = retrieve('What is tomorrow’s weather in Prague?', 'dishwasher', Settings())
    # A vector DB always returns neighbors; these results are not proof of an answer.
    assert sources
    assert not any('weather forecast' in s.text.lower() for s in sources)
