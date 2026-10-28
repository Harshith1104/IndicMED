"""HTTP contract tests; real pipeline routing with fake translation/encoding."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app, get_pipeline_service
from backend.schemas import AskRequest
from backend.services.pipeline import PipelineBusyError, PipelineService
from src.pipeline import IndicMedPipeline
from src.translation import TranslationUnavailableError

ROW = {"id": "faq-1", "question": "What is asthma?", "answer": "Asthma affects the airways.",
       "category": "Asthma", "source": "NIH", "source_url": "https://example.test/asthma"}


class AllowGate:
    """Isolate transport/routing tests; medical gating is tested separately."""
    def __init__(self, pipeline):
        pass

    def native_intent(self, query):
        return None

    def intent(self, query):
        return {'decision': 'medical', 'reason': 'test_fixture'}

    def relevance(self, query, item, route):
        return True, 'test_fixture', {}


class Translator:
    def __init__(self):
        self.calls = []
        self.fail = False

    def translate_to_english(self, text, language):
        self.calls.append(("to", language))
        if self.fail:
            raise TranslationUnavailableError("secret-token /private/model")
        return "What is asthma?"

    def translate_from_english(self, text, language):
        self.calls.append(("from", language))
        if self.fail:
            raise TranslationUnavailableError("secret-token /private/model")
        return {"hi": "हिन्दी उत्तर", "te": "తెలుగు సమాధానం", "ta": "தமிழ் பதில்"}[language]


class Retriever:
    def __init__(self):
        self.calls = []

    def retrieve(self, query, top_k):
        self.calls.append((query, top_k))
        return [{**ROW, "score": 0.76}, {**ROW, "question": "What causes asthma?", "score": 0.6}][:top_k]


@pytest.fixture
def api():
    translator, retriever = Translator(), Retriever()
    pipeline = IndicMedPipeline(documents=pd.DataFrame([ROW]), translator=translator)
    pipeline.retrievers = {method: retriever for method in ("tfidf", "bm25", "semantic")}
    service = PipelineService(lambda: pipeline, validator_factory=AllowGate)
    app.dependency_overrides[get_pipeline_service] = lambda: service
    with TestClient(app) as client:
        yield client, translator, retriever
    app.dependency_overrides.clear()


def test_health_and_options_do_not_load_pipeline():
    def forbidden():
        raise AssertionError("Health/options must never ask for a pipeline")
    app.dependency_overrides[get_pipeline_service] = forbidden
    try:
        with TestClient(app) as client:
            assert client.get("/api/health").json() == {"status": "ok"}
            options = client.get("/api/options").json()
            assert [x["value"] for x in options["languages"]] == ["auto", "en", "hi", "te", "ta"]
            assert options["defaults"]["retrieval_method"] == "semantic"
            assert options["defaults"]["multilingual_strategy"] == "translate"
            assert len(options["retrieval_methods"]) == 3
    finally:
        app.dependency_overrides.clear()


def test_valid_english_skips_translation(api):
    client, translator, retriever = api
    response = client.post("/api/ask", json={"query": "What is asthma?", "language": "en"})
    assert response.status_code == 200
    result = response.json()
    assert result["document_id"] == ROW["id"]
    assert result["answer"] == result["translated_answer"] == ROW["answer"]
    assert result["related_questions"] == ["What causes asthma?"]
    assert result["similarity_score"] == 0.76
    assert result["source_url"] == ROW["source_url"]
    assert translator.calls == []
    assert retriever.calls == [("What is asthma?", 3)]


@pytest.mark.parametrize("payload", [
    {"query": ""}, {"query": "  \n "}, {"query": "<p></p>"}, {"query": "x" * 4001},
    {"query": "test", "language": "fr"}, {"query": "test", "retrieval_method": "unknown"},
    {"query": "test", "multilingual_strategy": "unknown"},
    {"query": "test", "retrieval_method": "bm25", "multilingual_strategy": "direct"},
    {"query": "test", "retrieval_method": "tfidf", "multilingual_strategy": "direct"},
    *[{"query": "test", "top_k": k} for k in [0, 6, True, 1.5, "3"]],
    {"query": "test", "unexpected": "no"},
])
def test_invalid_requests(api, payload):
    client, translator, retriever = api
    assert client.post("/api/ask", json=payload).status_code == 422
    assert not translator.calls and not retriever.calls


@pytest.mark.parametrize("language,query", [("hi", "मधुमेह के लक्षण क्या हैं?"),
    ("te", "మైగ్రేన్‌కు కారణాలు ఏమిటి?"), ("ta", "காசநோய் எவ்வாறு கண்டறியப்படுகிறது?")])
@pytest.mark.parametrize("strategy", ["direct", "translate"])
@pytest.mark.parametrize("selection", ["auto", "manual"])
def test_multilingual_routing(api, language, query, strategy, selection):
    client, translator, retriever = api
    response = client.post("/api/ask", json={"query": query, "language": "auto" if selection == "auto" else language,
        "multilingual_strategy": strategy, "top_k": 2})
    assert response.status_code == 200
    result = response.json()
    assert result["selected_language"] == result["detected_language"] == language
    assert result["retrieval_strategy"] == f"{strategy}_semantic"
    # The application gate canonicalizes an Indic question once for validation
    # in either route. Direct retrieval still receives the native query.
    assert translator.calls == [("to", language), ("from", language)]
    assert retriever.calls == [(query if strategy == "direct" else "What is asthma?", 2)]


@pytest.mark.parametrize("method", ["tfidf", "bm25", "semantic"])
def test_translate_method_routing(api, method):
    result = api[0].post("/api/ask", json={"query": "मधुमेह", "retrieval_method": method})
    assert result.status_code == 200
    assert result.json()["retrieval_strategy"] == f"translate_{method}"


def test_manual_language_overrides_detection(api):
    result = api[0].post("/api/ask", json={"query": "मधुमेह", "language": "en"})
    assert result.json()["selected_language"] == "en"
    assert not api[1].calls


def test_translation_failure(api):
    client, translator, _ = api
    translator.fail = True
    failure = client.post("/api/ask", json={"query": "మధుమేహం"})
    assert failure.status_code == 200
    assert failure.json()['status'] == 'clarification_needed'
    assert failure.json()['reason'] == 'validation_unavailable'
    fallback = client.post("/api/ask", json={"query": "మధుమేహం", "multilingual_strategy": "direct"})
    assert fallback.status_code == 200
    assert fallback.json()['status'] == 'clarification_needed'
    assert 'translated_answer' not in fallback.json()
    assert "secret-token" not in failure.text + fallback.text
    assert "/private" not in failure.text + fallback.text


@pytest.mark.parametrize("error,status,code", [(FileNotFoundError("secret"), 503, "resources_unavailable"),
    (ValueError("secret index"), 503, "pipeline_unavailable"),
    (KeyError("secret configuration"), 503, "pipeline_unavailable"),
    (OSError("secret checkpoint"), 503, "pipeline_unavailable"),
    (LookupError("missing"), 404, "no_results"), (Exception("secret"), 500, "internal_error")])
def test_safe_backend_errors(api, error, status, code):
    def fail():
        raise error
    app.dependency_overrides[get_pipeline_service] = lambda: PipelineService(fail)
    response = api[0].post("/api/ask", json={"query": "asthma"})
    assert response.status_code == status
    assert response.json()["code"] == code
    assert "secret" not in response.text


def test_lazy_reuse_and_concurrency(api):
    entered, release = Event(), Event()
    calls = []
    class BlockingPipeline:
        def ask(self, **kwargs):
            entered.set()
            assert release.wait(5)
            return {}
    def factory():
        calls.append(1)
        return BlockingPipeline()
    service = PipelineService(factory, validator_factory=AllowGate)
    assert calls == []
    request = AskRequest(query="asthma")
    with ThreadPoolExecutor() as pool:
        future = pool.submit(service.ask, request)
        try:
            assert entered.wait(5)
            with pytest.raises(PipelineBusyError):
                service.ask(request)
            app.dependency_overrides[get_pipeline_service] = lambda: service
            busy = api[0].post("/api/ask", json={"query": "asthma"})
            assert busy.status_code == 503 and busy.json()["code"] == "pipeline_busy"
            assert api[0].get("/api/health").status_code == 200
        finally:
            release.set()
        future.result()
    service.ask(request)
    assert len(calls) == 1


def test_initialization_failure_can_retry():
    count = []
    class EmptyPipeline:
        def ask(self, **kwargs):
            return {}
    def factory():
        count.append(1)
        if len(count) == 1:
            raise FileNotFoundError()
        return EmptyPipeline()
    service = PipelineService(factory, validator_factory=AllowGate)
    with pytest.raises(FileNotFoundError):
        service.ask(AskRequest(query="asthma"))
    assert service.ask(AskRequest(query="asthma"))['status'] == 'success'


def test_cors_only_local_dev(api):
    client = api[0]
    for origin, expected in [("http://localhost:5173", 200), ("https://untrusted.test", 400)]:
        response = client.options("/api/ask", headers={"Origin": origin, "Access-Control-Request-Method": "POST"})
        assert response.status_code == expected
