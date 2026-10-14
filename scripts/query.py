import argparse
import json
import sys

from app.config import Settings, HomeGuideError
from app.documents import documents
from app.retrieval import retrieve
from app.schemas import Question
from app.service import ask


def main():
    settings = Settings()
    parser = argparse.ArgumentParser(description='Ask a standalone question about one appliance manual.')
    parser.add_argument('--appliance', required=True, choices=[d.id for d in documents(settings)])
    parser.add_argument('--sources-only', action='store_true', help='Retrieve evidence without calling an LLM or needing an API key.')
    parser.add_argument('--json', action='store_true', help='Print machine-readable answer and sources.')
    parser.add_argument('question')
    args = parser.parse_args()
    try:
        request = Question(appliance=args.appliance, question=args.question)
        if args.sources_only:
            sources = retrieve(request.question, request.appliance, settings)
            print(json.dumps({'sources': [s.model_dump() for s in sources]}, indent=2, ensure_ascii=False))
        else:
            result = ask(request, settings)
            if args.json:
                print(result.model_dump_json(indent=2))
            else:
                print(result.answer)
                print('\nRetrieved context:')
                for s in result.sources:
                    print(f'  [{s.filename}, p. {s.page}] — {s.kind}')
    except (HomeGuideError, ValueError) as exc:
        # Pydantic errors could contain user input; no secrets are read from input here.
        print(f'HomeGuide: {exc}', file=sys.stderr)
        return 1
    except Exception:
        print('HomeGuide: Query failed. Check the local index, dependencies, and LLM configuration.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
