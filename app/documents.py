import json
from dataclasses import dataclass
from pathlib import Path

from app.config import Settings, HomeGuideError


@dataclass(frozen=True)
class Document:
    id: str
    filename: str
    appliance: str
    model: str
    page_count: int
    page_ranges: list[list[int]]
    safety_pages: list[int]
    diagram_pages: list[int]
    sha256: str
    source_url: str
    language: str
    notes: str
    questions: list[dict]

    @property
    def pages(self):
        return [p for start, end in self.page_ranges for p in range(start, end + 1)]


def documents(settings: Settings) -> list[Document]:
    try:
        result = [Document(**d) for d in json.loads(settings.manifest_path.read_text())['documents']]
        if len({d.id for d in result}) != len(result) or len({d.filename for d in result}) != len(result):
            raise ValueError('Duplicate document IDs or filenames')
        for d in result:
            if Path(d.filename).name != d.filename or not d.filename.endswith('.pdf'):
                raise ValueError('Invalid PDF filename')
            if not d.pages or min(d.pages) < 1 or max(d.pages) > d.page_count:
                raise ValueError('Invalid physical page range')
        return result
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise HomeGuideError('The document manifest is missing or invalid. Check documents.json.') from exc


def document_for(appliance: str | None, settings: Settings) -> Document:
    for d in documents(settings):
        if d.id == appliance:
            return d
    raise HomeGuideError('Please select washing-machine, dishwasher, or coffee-machine to clarify the appliance.')


def pdf_path(doc: Document, settings: Settings) -> Path:
    path = (settings.pdf_dir / doc.filename).resolve()
    if not path.is_relative_to(settings.pdf_dir.resolve()) or not path.is_file():
        raise HomeGuideError(f'Missing registered PDF: {doc.filename}. See pdfs/README.md.')
    return path
