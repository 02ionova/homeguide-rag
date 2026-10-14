from dataclasses import replace
import hashlib
import json

import pymupdf
import pytest

from app.config import Settings


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    pdf_dir = tmp_path / 'pdfs'
    pdf_dir.mkdir()
    manifest = []
    for id_, subject in [('washing-machine', 'child lock'), ('dishwasher', 'filter cleaning'), ('coffee-machine', 'coffee flow')]:
        filename = id_ + '.pdf'
        with pymupdf.open() as pdf:
            for page in range(3):
                p = pdf.new_page()
                p.insert_textbox(pymupdf.Rect(40, 40, 550, 800),
                                 f'Page {page+1}\n{subject.title()}\n' +
                                 (f'This is the {id_} manual. Instructions about {subject}. ' * 24), fontsize=10)
            pdf.save(pdf_dir / filename)
        manifest.append(dict(id=id_, filename=filename, appliance=id_.replace('-', ' ').title(),
                             model='Test model', page_count=3, page_ranges=[[1, 3]], safety_pages=[1], diagram_pages=[],
                             sha256=hashlib.sha256((pdf_dir / filename).read_bytes()).hexdigest(),
                             source_url='https://example.invalid/manual.pdf', language='English', notes='Synthetic test fixture', questions=[]))
    manifest_path = tmp_path / 'documents.json'
    manifest_path.write_text(json.dumps({'documents': manifest}))
    settings = replace(Settings(), pdf_dir=pdf_dir, manifest_path=manifest_path, chroma_dir=tmp_path / 'chroma', embedding_model='test-embedding', llm_api_key='')
    def deterministic_embed(texts, settings):
        vectors = []
        for text in texts:
            lower = text.lower()
            vector = [1.0 + lower.count(term) for term in ('child', 'filter', 'coffee', 'instructions')]
            length = sum(x*x for x in vector) ** 0.5
            vectors.append([x / length for x in vector])
        return vectors
    monkeypatch.setattr('app.ingestion.embed', deterministic_embed)
    monkeypatch.setattr('app.retrieval.embed', deterministic_embed)
    return settings
