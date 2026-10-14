from app.config import Settings, HomeGuideError
from app.documents import document_for
from app.generation import generate
from app.ingestion import active_collection
from app.retrieval import retrieve
from app.schemas import Question, Answer


def ask(request: Question, settings: Settings) -> Answer:
    if request.appliance is None:
        return Answer(answer='Which appliance do you mean? Please select a washing machine, dishwasher, or coffee machine.', status='clarification')
    doc = document_for(request.appliance, settings)
    collection = active_collection(settings)
    if not settings.llm_api_key:
        raise HomeGuideError('LLM_API_KEY is missing. Add your OpenAI API key to the local .env file and restart HomeGuide.')
    sources = retrieve(request.question, request.appliance, settings, collection)
    return generate(request.question, doc, sources, settings)
