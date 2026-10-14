from urllib.parse import quote

from app.config import Settings, HomeGuideError
from app.documents import document_for
from app.ingestion import active_collection, embed, OVERLAP_WORDS
from app.schemas import Source


def retrieve(question: str, appliance: str, settings: Settings, collection=None) -> list[Source]:
    doc = document_for(appliance, settings)
    collection = collection if collection is not None else active_collection(settings)
    try:
        available = collection.get(where={'appliance': doc.id}, include=[])['ids']
        if not available:
            raise HomeGuideError('No indexed pages for this appliance. Run: python -m scripts.ingest')
        result = collection.query(query_embeddings=embed([question], settings),
                                  n_results=min(settings.top_k, len(available)),
                                  where={'appliance': doc.id}, include=['metadatas'])
        primary_pages = list(dict.fromkeys(m['page'] for m in result['metadatas'][0]))
        # Complete pages and adjacent pages retain procedure continuations. Safety pages
        # are explicitly added; cosine distance never decides answerability.
        kinds = {p: 'semantic match' for p in primary_pages}
        for p in primary_pages:
            for adjacent in (p - 1, p + 1):
                if adjacent in doc.pages:
                    kinds.setdefault(adjacent, 'adjacent procedure context')
        for p in doc.safety_pages:
            kinds.setdefault(p, 'safety context')
        rows = collection.get(where={'$and': [{'appliance': doc.id}, {'page': {'$in': list(kinds)}}]},
                              include=['documents', 'metadatas'])
        sources = []
        for page, kind in kinds.items():
            parts = sorted([(m['ordinal'], t, id_) for m, t, id_ in
                            zip(rows['metadatas'], rows['documents'], rows['ids']) if m['page'] == page])
            if not parts:
                continue
            words = []
            for ordinal, text, _ in parts:
                words.extend(text.split()[OVERLAP_WORDS:] if ordinal else text.split())
            sources.append(Source(filename=doc.filename, page=page, appliance=doc.id,
                                  model=doc.model, text=' '.join(words), kind=kind,
                                  chunk_ids=[x[2] for x in parts],
                                  url=f'/manuals/{quote(doc.id)}#page={page}'))
        return sources
    except HomeGuideError:
        raise
    except Exception as exc:
        raise HomeGuideError('Cannot query the vector index. Check storage access or rebuild with python -m scripts.ingest --rebuild.') from exc
