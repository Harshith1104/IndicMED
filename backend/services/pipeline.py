from collections.abc import Callable
from threading import Lock
from typing import Any

from backend.schemas import AskRequest, CompareRequest
from backend.services.cache import TranslationCache
from backend.services.validation import MedicalValidator, ValidationAbstention
from src.preprocessing.language_detector import detect_language
from src.preprocessing.normalizer import normalize_text
from src.translation import TranslationUnavailableError

MESSAGES = {
    'out_of_scope': "This question is outside IndicMed's medical scope.",
    'insufficient_evidence': "We couldn't find sufficiently relevant medical information.",
    'clarification_needed': 'Please clarify your health question, or retry when validation resources are available.',
}


class PipelineBusyError(RuntimeError):
    pass


def create_pipeline():
    from src.pipeline import IndicMedPipeline
    return IndicMedPipeline()


class PipelineService:
    """One lazy pipeline and bounded caches under one inference lock.

    Comparison branches run sequentially, sharing the same encoder/translator.
    """
    def __init__(self, factory: Callable[[], Any] = create_pipeline, validator_factory=MedicalValidator):
        self._factory, self._validator_factory = factory, validator_factory
        self._pipeline = self._validator = None
        self._lock = Lock()

    def _ensure(self):
        if self._pipeline is None:
            pipeline = self._factory()
            if hasattr(pipeline, 'translator'):
                pipeline.translator = TranslationCache(pipeline.translator)
            self._pipeline = pipeline
        if self._validator is None:
            self._validator = self._validator_factory(self._pipeline)

    def _abstain(self, query, language, status, reason, evidence=None, candidate=None):
        return dict(status=status, query=query, selected_language=language, detected_language=language,
                    reason=reason, message=MESSAGES[status], validation=evidence or {}, candidate=candidate)

    def _prepare(self, query, language):
        native = self._validator.native_intent(query) if language != 'en' else None
        if native:
            return None, native
        english = query if language == 'en' else self._pipeline.translator.translate_to_english(query, language)
        if not english.strip():
            raise TranslationUnavailableError('Empty query translation')
        return english, self._validator.intent(english)

    def _run(self, request, language, english, intent):
        if intent['decision'] != 'medical':
            return self._abstain(request.query, language, intent['decision'], intent['reason'], {'intent': intent})
        selected = {}
        route = f'{request.retrieval_method}:{"english" if language == "en" else request.multilingual_strategy}:{language}'

        def guard(results, english_query, strategy):
            if not results:
                raise ValidationAbstention('insufficient_evidence', 'no_results')
            item = results[0]
            enough, reason, evidence = self._validator.relevance(english, item, route)
            selected.update(question=item['question'], evidence=evidence,
                            retrieval_query=request.query if strategy == 'direct_semantic' else english_query)
            if not enough:
                candidate = {key: item.get(key, '') for key in ['id', 'question', 'source', 'source_url']}
                candidate.update(similarity_score=float(item['score']), retrieval_query=selected['retrieval_query'])
                # Rejected answer text is withheld, including in comparison mode.
                raise ValidationAbstention('clarification_needed' if reason == 'validation_unavailable'
                                          else 'insufficient_evidence', reason, evidence, candidate)
        try:
            result = self._pipeline.ask(**{**request.model_dump(), 'language': language}, retrieval_guard=guard)
        except ValidationAbstention as decision:
            return self._abstain(request.query, language, decision.status, decision.reason,
                                 {'intent': intent, 'relevance': decision.evidence, 'route': route}, decision.candidate)
        if result.get('translation_warning'):
            result = {**result, 'translation_warning': 'Answer translation is unavailable; showing the grounded English answer. Check the backend translation setup before retrying.'}
        return {**result, 'status': 'success', 'retrieved_question': selected.get('question', ''),
                'retrieval_query': selected.get('retrieval_query', english),
                'validation': {'intent': intent, 'relevance': selected.get('evidence', {}), 'route': route}}

    def _execute(self, request, compare=False):
        if not self._lock.acquire(blocking=False):
            raise PipelineBusyError()
        try:
            query = normalize_text(request.query)
            language = detect_language(query) if request.language == 'auto' else request.language
            self._ensure()
            try:
                english, intent = self._prepare(query, language)
            except (TranslationUnavailableError, OSError, RuntimeError, ImportError):
                if not compare:
                    return self._abstain(query, language, 'clarification_needed', 'validation_unavailable')
                english, intent = None, {'decision': 'clarification_needed', 'reason': 'validation_unavailable'}
            if not compare:
                return self._run(request, language, english, intent)
            branches = {}
            for strategy in ['direct', 'translate']:
                if language == 'en' and strategy == 'translate':
                    branches[strategy] = dict(branches['direct'])
                    continue
                try:
                    ask = AskRequest(query=query, language=language, retrieval_method='semantic',
                                     multilingual_strategy=strategy, top_k=request.top_k)
                    branches[strategy] = self._run(ask, language, english, intent)
                except Exception:
                    branches[strategy] = self._abstain(query, language, 'clarification_needed', 'strategy_unavailable')
            return dict(query=query, selected_language=language, retrieval_method='semantic', top_k=request.top_k,
                        equivalent=language == 'en', explanation=(
                            'English uses the same query in both paths. One inference was reused.' if language == 'en' else
                            'Different query representations can produce incomparable scores. No live-query winner is inferred.'),
                        **branches)
        finally:
            self._lock.release()

    def ask(self, request: AskRequest):
        return self._execute(request)

    def compare(self, request: CompareRequest):
        return self._execute(request, compare=True)
