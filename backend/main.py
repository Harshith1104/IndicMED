"""Start from the repository root: uvicorn backend.main:app --reload."""
import logging

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.schemas import (AskRequest, AskResponse, AbstentionResponse, CompareRequest,
                             ComparisonResponse, ErrorResponse, HealthResponse, OptionsResponse, RequestSettings)
from backend.services.pipeline import PipelineBusyError, PipelineService
from src.translation import TranslationUnavailableError
from src.translation.languages import LANGUAGE_NAMES
from src.utils.helpers import load_config

LOGGER = logging.getLogger(__name__)
_pipeline_service = PipelineService()  # Cheap owner only; no dataset/models loaded.


def get_pipeline_service() -> PipelineService:
    return _pipeline_service


def error_response(status: int, code: str, message: str, headers=None):
    return JSONResponse(status_code=status, content={"code": code, "message": message}, headers=headers)


app = FastAPI(title="IndicMed API", version="1.0.0", description="Retrieval-grounded multilingual medical FAQs.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"], allow_headers=["Content-Type"],
)


@app.exception_handler(RequestValidationError)
async def invalid_request(_request: Request, error: RequestValidationError):
    # Do not echo user inputs, exception contexts or local file paths.
    issues = []
    for item in error.errors():
        field = ".".join(str(part) for part in item["loc"] if part != "body")
        issues.append(f"{field + ': ' if field else ''}{item['msg']}")
    return error_response(422, "invalid_request", " ".join(issues))


@app.exception_handler(Exception)
async def unexpected_error(_request: Request, error: Exception):
    LOGGER.error("Unhandled API error (%s)", type(error).__name__)
    return error_response(500, "internal_error", "The backend could not complete this request. Please try again.")


@app.get("/api/health", response_model=HealthResponse)
async def health():
    return HealthResponse()


@app.get("/api/options", response_model=OptionsResponse)
def options():
    config = load_config()
    settings = config["retrieval"]
    return OptionsResponse(
        languages=[{"value": "auto", "label": "Auto detect"}] +
                  [{"value": code, "label": name} for code, name in LANGUAGE_NAMES.items()],
        retrieval_methods=[{"value": "tfidf", "label": "TF-IDF"}, {"value": "bm25", "label": "BM25"},
                           {"value": "semantic", "label": "Semantic"}],
        multilingual_strategies=[{"value": "translate", "label": "Translate-then-retrieve"},
                                 {"value": "direct", "label": "Direct multilingual retrieval"}],
        defaults=RequestSettings(retrieval_method=settings["default_method"],
                            multilingual_strategy=settings["default_multilingual_strategy"], top_k=settings["top_k"]),
    )


@app.post("/api/ask", response_model=AskResponse | AbstentionResponse,
          responses={code: {"model": ErrorResponse} for code in [404, 422, 500, 503]})
def ask(request: AskRequest, service: PipelineService = Depends(get_pipeline_service)):
    # Sync endpoints run in FastAPI's threadpool, keeping health/options responsive.
    try:
        return service.ask(request)
    except PipelineBusyError:
        return error_response(503, "pipeline_busy", "IndicMed is processing another question. Please wait and try again.", {"Retry-After": "5"})
    except TranslationUnavailableError:
        return error_response(503, "translation_unavailable", "Query translation is unavailable. Select direct multilingual retrieval with Semantic, or check the IndicTrans2 setup.")
    except FileNotFoundError:
        return error_response(503, "resources_unavailable", "Required dataset, index or model files are missing. Check the backend setup instructions.")
    except KeyError:
        return error_response(503, "pipeline_unavailable", "Required dataset or configuration fields are missing. Check the backend setup.")
    except LookupError:
        return error_response(404, "no_results", "No relevant FAQ was found. Try rephrasing your question.")
    except (ValueError, OSError, ImportError, RuntimeError):
        return error_response(503, "pipeline_unavailable", "The retrieval resources or model could not be used. Check the backend dataset, index and model setup.")
    except Exception as error:
        LOGGER.error("Inference failed (%s)", type(error).__name__)
        return error_response(500, "internal_error", "IndicMed could not complete the search. Please try again.")


@app.post('/api/compare', response_model=ComparisonResponse,
          responses={code: {'model': ErrorResponse} for code in [422, 500, 503]})
def compare(request: CompareRequest, service: PipelineService = Depends(get_pipeline_service)):
    try:
        return service.compare(request)
    except PipelineBusyError:
        return error_response(503, 'pipeline_busy', 'IndicMed is processing another question. Please wait and try again.', {'Retry-After': '5'})
    except (FileNotFoundError, ValueError, OSError, ImportError, RuntimeError, KeyError):
        return error_response(503, 'pipeline_unavailable', 'Comparison resources are unavailable. Check the backend dataset, index and model setup.')
    except Exception as error:
        LOGGER.error('Comparison failed (%s)', type(error).__name__)
        return error_response(500, 'internal_error', 'IndicMed could not complete this comparison. Please try again.')
