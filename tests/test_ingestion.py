from dataclasses import replace
import json

import pymupdf
import pytest

from app.config import HomeGuideError
from app.documents import documents, document_for
from app.ingestion import active_collection, clean_text, extract_document, ingest, ingestion_lock, read_state, split_page
from app.retrieval import retrieve


def test_page_chunks_and_overlapping_context(corpus):
    doc = document_for('washing-machine', corpus)
    chunks = extract_document(doc, corpus)
    assert {c['metadata']['page'] for c in chunks} == {1, 2, 3}
    assert len({c['id'] for c in chunks}) == len(chunks)
    assert all(c['metadata']['filename'] == 'washing-machine.pdf' for c in chunks)
    page = [c for c in chunks if c['metadata']['page'] == 1]
    assert page[0]['text'].split()[-30:] == page[1]['text'].split()[:30]
    assert 'Warning! Do not drink liquids.' in clean_text('en\nWarning! Do not drink liquids.\n34', 34)
    assert split_page('') == []


def test_idempotent_persistent_index_and_filter(corpus):
    first = ingest(corpus)
    second = ingest(corpus)
    assert second['status'] == 'unchanged'
    assert first['collection'] == second['collection']
    assert first['chunks'] == active_collection(corpus).count()
    for doc in documents(corpus):
        sources = retrieve('filter child coffee cleaning', doc.id, corpus)
        assert sources
        assert all(s.appliance == doc.id and s.filename == doc.filename and 1 <= s.page <= 3 for s in sources)
        assert all(s.url.endswith('#page=' + str(s.page)) for s in sources)


def test_changed_document_and_rebuild(corpus):
    first = ingest(corpus)
    doc = document_for('washing-machine', corpus)
    path = corpus.pdf_dir / doc.filename
    pdf = pymupdf.open(path)
    pdf[0].insert_text((50, 760), 'Additional maintenance warning for this manual.')
    pdf.saveIncr()
    pdf.close()
    with pytest.raises(HomeGuideError, match='changed'):
        active_collection(corpus)
    changed = ingest(corpus)
    assert changed['fingerprint'] != first['fingerprint']
    assert changed['collection'] != first['collection']
    rebuilt = ingest(corpus, rebuild=True)
    assert rebuilt['fingerprint'] == changed['fingerprint']
    assert rebuilt['chunks'] == changed['chunks']
    assert rebuilt['collection'] != changed['collection']


def test_failed_rebuild_preserves_active_index(corpus, monkeypatch):
    first = ingest(corpus)
    def unavailable(*args):
        raise HomeGuideError('Embedding service unavailable')
    monkeypatch.setattr('app.ingestion.embed', unavailable)
    with pytest.raises(HomeGuideError):
        ingest(corpus, rebuild=True)
    assert read_state(corpus)['collection'] == first['collection']
    assert active_collection(corpus).count() == first['chunks']


def test_missing_unreadable_empty_and_wrong_page_count(corpus):
    doc = document_for('washing-machine', corpus)
    path = corpus.pdf_dir / doc.filename
    original = path.read_bytes()
    path.unlink()
    with pytest.raises(HomeGuideError, match='Missing registered PDF'):
        extract_document(doc, corpus)
    path.write_bytes(b'not a PDF')
    with pytest.raises(HomeGuideError, match='valid, readable PDF'):
        extract_document(doc, corpus)
    path.unlink()
    with pymupdf.open() as pdf:
        pdf.new_page()
        pdf.save(path)
    with pytest.raises(HomeGuideError, match='expected 3'):
        extract_document(doc, corpus)
    with pytest.raises(HomeGuideError, match='no extractable text'):
        extract_document(replace(doc, page_count=1, page_ranges=[[1, 1]]), corpus)
    path.write_bytes(original)


def test_missing_index_changed_embedding_and_lock(corpus):
    with pytest.raises(HomeGuideError, match='No usable index'):
        active_collection(corpus)
    ingest(corpus)
    with pytest.raises(HomeGuideError, match='embedding model changed'):
        active_collection(replace(corpus, embedding_model='another-model'))
    with ingestion_lock(corpus):
        with pytest.raises(HomeGuideError, match='already running'):
            ingest(corpus)


def test_manifest_rejects_unregistered_paths(corpus):
    payload = json.loads(corpus.manifest_path.read_text())
    payload['documents'][0]['filename'] = '../.env'
    corpus.manifest_path.write_text(json.dumps(payload))
    with pytest.raises(HomeGuideError, match='manifest'):
        documents(corpus)
