"""Page-local chunks, explicit embeddings, and atomic publication of Chroma indexes."""
from contextlib import contextmanager
from functools import lru_cache
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import uuid

import pymupdf

from app.config import ROOT, Settings, HomeGuideError
from app.documents import documents, pdf_path

CHUNK_WORDS = 140
OVERLAP_WORDS = 30
PIPELINE_VERSION = 'page-words-v1'
os.environ.setdefault('HF_HOME', str(ROOT / 'data' / 'models'))


def clean_text(text: str, page: int) -> str:
    # Preserve warnings, headings, numbers, units and table reading order.
    text = text.replace('\u00ad', '').replace('\x00', '').replace('\u00a0', ' ')
    text = re.sub(r'(?<=[a-z])-\n(?=[a-z])', '', text)
    lines = [re.sub(r'[^\S\n]+', ' ', line).strip() for line in text.splitlines()]
    return '\n'.join(line for line in lines if line and line not in {str(page), 'en'})


def split_page(text: str) -> list[str]:
    words = text.split()
    if not words:
        return []
    return [' '.join(words[start:start + CHUNK_WORDS])
            for start in range(0, len(words), CHUNK_WORDS - OVERLAP_WORDS)
            if start == 0 or len(words[start:]) > OVERLAP_WORDS]


def extract_document(doc, settings):
    path = pdf_path(doc, settings)
    try:
        with pymupdf.open(path) as pdf:
            if pdf.needs_pass:
                raise HomeGuideError(f'{doc.filename} is password protected.')
            if len(pdf) != doc.page_count:
                raise HomeGuideError(f'{doc.filename} has {len(pdf)} pages; expected {doc.page_count}. Review documents.json.')
            chunks = []
            for page in doc.pages:
                text = clean_text(pdf[page - 1].get_text(sort=False), page)
                if len(text.split()) < 5:
                    continue  # Deliberately do not manufacture text for diagrams.
                heading = ' / '.join(text.splitlines()[:2])[:130]
                for ordinal, body in enumerate(split_page(text)):
                    stable = f'{doc.filename}:{page}:{ordinal}:{body}'
                    id_ = hashlib.sha256(stable.encode()).hexdigest()
                    chunks.append({'id': id_, 'text': body, 'metadata': {
                        'filename': doc.filename, 'page': page, 'appliance': doc.id,
                        'model': doc.model, 'chunk_id': id_, 'ordinal': ordinal,
                        'heading': heading,
                    }})
            if not chunks:
                raise HomeGuideError(f'{doc.filename} contains no extractable text in the registered ranges. Check the PDF; OCR may be needed.')
            return chunks
    except HomeGuideError:
        raise
    except Exception as exc:
        raise HomeGuideError(f'Cannot read {doc.filename}. Check that it is a valid, readable PDF.') from exc


@lru_cache(maxsize=2)
def embedding_model(name: str):
    try:
        from sentence_transformers import SentenceTransformer
        # CPU is predictable on Apple Silicon; no CUDA or Metal setup is needed.
        return SentenceTransformer(name, device='cpu', trust_remote_code=False)
    except Exception as exc:
        raise HomeGuideError('Cannot load the embedding model. Initial setup requires a Hugging Face download; check connectivity and model access.') from exc


def embed(texts: list[str], settings: Settings):
    try:
        return embedding_model(settings.embedding_model).encode(
            texts, normalize_embeddings=True, show_progress_bar=False,
            batch_size=32).tolist()
    except HomeGuideError:
        raise
    except Exception as exc:
        raise HomeGuideError('Embedding failed. Check the embedding model and available memory.') from exc


def client(settings):
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    return chromadb.PersistentClient(path=str(settings.chroma_dir),
                                    settings=ChromaSettings(anonymized_telemetry=False))


def fingerprint(settings):
    registered = documents(settings)
    hashes = {d.filename: hashlib.sha256(pdf_path(d, settings).read_bytes()).hexdigest() for d in registered}
    spec = {'documents': json.loads(settings.manifest_path.read_text()),
            'hashes': hashes, 'embedding_model': settings.embedding_model,
            'pipeline': PIPELINE_VERSION, 'chunk_words': CHUNK_WORDS, 'overlap': OVERLAP_WORDS}
    return hashlib.sha256(json.dumps(spec, sort_keys=True).encode()).hexdigest(), hashes


def read_state(settings):
    try:
        return json.loads((settings.chroma_dir / 'active-index.json').read_text())
    except (OSError, ValueError) as exc:
        raise HomeGuideError('No usable index found. Run: python -m scripts.ingest') from exc


def active_collection(settings, check_fresh=True):
    state = read_state(settings)
    if state.get('embedding_model') != settings.embedding_model:
        raise HomeGuideError('The embedding model changed. Run: python -m scripts.ingest --rebuild')
    if check_fresh and state.get('fingerprint') != fingerprint(settings)[0]:
        raise HomeGuideError('The manuals or manifest changed. Run: python -m scripts.ingest')
    try:
        collection = client(settings).get_collection(state['collection'], embedding_function=None)
        if collection.count() != state['chunks'] or not state['chunks']:
            raise ValueError('Incomplete index')
        return collection
    except Exception as exc:
        raise HomeGuideError('The vector index is incomplete or unavailable. Run: python -m scripts.ingest --rebuild') from exc


@contextmanager
def ingestion_lock(settings):
    settings.chroma_dir.mkdir(parents=True, exist_ok=True)
    with (settings.chroma_dir / 'ingestion.lock').open('w') as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise HomeGuideError('Ingestion is already running. Wait for it to finish.') from exc
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def ingest(settings: Settings, rebuild=False) -> dict:
    with ingestion_lock(settings):
        signature, hashes = fingerprint(settings)
        if not rebuild:
            try:
                state = read_state(settings)
                if state.get('fingerprint') == signature:
                    active_collection(settings, check_fresh=False)
                    return {**state, 'status': 'unchanged'}
            except HomeGuideError:
                pass
        # Validate every PDF before creating a new collection. Never alter originals.
        chunks = [c for doc in documents(settings) for c in extract_document(doc, settings)]
        name = 'homeguide-' + uuid.uuid4().hex
        db = client(settings)
        collection = db.create_collection(name, embedding_function=None,
                                          metadata={'hnsw:space': 'cosine', 'embedding_model': settings.embedding_model})
        try:
            for start in range(0, len(chunks), 64):
                batch = chunks[start:start + 64]
                collection.upsert(ids=[c['id'] for c in batch],
                                  documents=[c['text'] for c in batch],
                                  metadatas=[c['metadata'] for c in batch],
                                  embeddings=embed([c['text'] for c in batch], settings))
            if collection.count() != len(chunks):
                raise HomeGuideError('Index verification failed; the previous index is still active.')
            # Detect edits during the build, before publishing mixed document versions.
            if fingerprint(settings)[0] != signature:
                raise HomeGuideError('Manuals changed during ingestion. Please run ingestion again.')
            state = {'collection': name, 'fingerprint': signature, 'hashes': hashes,
                     'embedding_model': settings.embedding_model, 'chunks': len(chunks),
                     'per_appliance': {d.id: sum(c['metadata']['appliance'] == d.id for c in chunks)
                                       for d in documents(settings)}}
            temp = settings.chroma_dir / 'active-index.tmp'
            temp.write_text(json.dumps(state, indent=2) + '\n')
            os.replace(temp, settings.chroma_dir / 'active-index.json')
            # Old generations stay available to in-flight readers; no destructive DB wipe.
            return {**state, 'status': 'built'}
        except Exception:
            db.delete_collection(name)
            raise
