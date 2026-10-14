from dataclasses import dataclass, field
from pathlib import Path
import os

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env')


class HomeGuideError(Exception):
    """An actionable error safe to show without leaking provider responses."""


@dataclass(frozen=True)
class Settings:
    pdf_dir: Path = ROOT / 'pdfs'
    manifest_path: Path = ROOT / 'documents.json'
    chroma_dir: Path = field(default_factory=lambda: (ROOT / os.getenv('CHROMA_DIR', 'data/chroma')).resolve())
    embedding_model: str = field(default_factory=lambda: os.getenv('EMBEDDING_MODEL', 'sentence-transformers/all-MiniLM-L6-v2'))
    llm_api_key: str = field(default_factory=lambda: os.getenv('LLM_API_KEY', ''), repr=False)
    llm_model: str = field(default_factory=lambda: os.getenv('LLM_MODEL', 'gpt-4.1-mini'))
    llm_base_url: str = field(default_factory=lambda: os.getenv('LLM_BASE_URL', 'https://api.openai.com/v1').rstrip('/'))
    timeout: float = field(default_factory=lambda: float(os.getenv('LLM_TIMEOUT_SECONDS', '45')))
    retries: int = field(default_factory=lambda: int(os.getenv('LLM_RETRIES', '2')))
    top_k: int = field(default_factory=lambda: int(os.getenv('TOP_K', '6')))

    def __post_init__(self):
        if not 1 <= self.top_k <= 15:
            raise ValueError('TOP_K must be between 1 and 15.')
        if not 0 <= self.retries <= 3 or not 1 <= self.timeout <= 120:
            raise ValueError('Use 0–3 retries and a timeout between 1 and 120 seconds.')
