import argparse
import json
import sys

from app.config import Settings, HomeGuideError
from app.ingestion import ingest


def main():
    parser = argparse.ArgumentParser(description='Index registered PDFs in pdfs/ with physical page citations.')
    parser.add_argument('--rebuild', action='store_true', help='Build and atomically publish a fresh index generation.')
    args = parser.parse_args()
    try:
        result = ingest(Settings(), rebuild=args.rebuild)
        print(json.dumps(result, indent=2))
    except (HomeGuideError, ValueError) as exc:
        print(f'HomeGuide: {exc}', file=sys.stderr)
        return 1
    except Exception:
        print('HomeGuide: Ingestion failed. Check the vector store path, dependencies and available disk space.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
