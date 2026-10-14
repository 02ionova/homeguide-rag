from dataclasses import asdict
import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.config import ROOT, Settings, HomeGuideError
from app.documents import documents, document_for, pdf_path
from app.ingestion import active_collection, read_state
from app.schemas import Question, Answer
from app.service import ask


def create_app(settings=None):
    settings = settings or Settings()
    application = FastAPI(title='HomeGuide', description='Document-grounded appliance assistance', version='1.0.0')
    application.mount('/static', StaticFiles(directory=ROOT / 'app/static'), name='static')

    @application.middleware('http')
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['Referrer-Policy'] = 'same-origin'
        response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
        return response

    @application.exception_handler(HomeGuideError)
    async def known_error(request, exc):
        return JSONResponse(status_code=503, content={'detail': str(exc)})

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        return JSONResponse(status_code=422, content={'detail': 'Please enter a question between 1 and 2000 characters and select a supported appliance.'})

    @application.get('/', include_in_schema=False)
    def index():
        return FileResponse(ROOT / 'app/templates/index.html', media_type='text/html')

    @application.get('/api/appliances')
    def appliances():
        issue = None
        try:
            active_collection(settings)
            state = read_state(settings)
        except HomeGuideError as exc:
            issue = str(exc)
            state = {}
        return {'documents': [{**asdict(d), 'available': (settings.pdf_dir / d.filename).is_file(),
                               'indexed_chunks': state.get('per_appliance', {}).get(d.id, 0),
                               'url': '/manuals/' + d.id} for d in documents(settings)],
                'index_ready': issue is None, 'index_issue': issue,
                'llm_ready': bool(settings.llm_api_key)}

    @application.post('/api/chat', response_model=Answer)
    def chat(question: Question):
        try:
            return ask(question, settings)
        except HomeGuideError:
            raise
        except Exception:
            # Do not echo/log exception bodies that could contain provider credentials.
            logging.getLogger(__name__).error('HomeGuide query failed; private exception details withheld.')
            return JSONResponse(status_code=503, content={'detail': 'HomeGuide could not complete this request. Check the local index and service setup, then try again.'})

    @application.get('/manuals/{document_id}', include_in_schema=False)
    def manual(document_id: str):
        try:
            doc = document_for(document_id, settings)
            path = pdf_path(doc, settings)
        except HomeGuideError:
            return JSONResponse(status_code=404, content={'detail': 'This registered manual is not available locally.'})
        return FileResponse(path, media_type='application/pdf', filename=doc.filename,
                            content_disposition_type='inline')

    return application


app = create_app()
