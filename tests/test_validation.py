import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient

from backend.main import app, get_pipeline_service
from backend.schemas import AskRequest, CompareRequest
from backend.services.cache import EncoderCache, TranslationCache
from backend.services.pipeline import PipelineBusyError, PipelineService
from backend.services.validation import MedicalValidator
from src.pipeline import IndicMedPipeline
from src.translation import TranslationUnavailableError

ROW = {'id': 'asthma', 'question': 'What is asthma?', 'answer': 'Asthma affects the airways. Symptoms include wheezing. Causes include allergens.',
       'category': 'Asthma', 'source': 'NIH', 'source_url': 'https://example.test/asthma', 'score': 0.76}
POLICY = {'intent': {'medical_margin': 0.2, 'outside_margin': -0.2},
          'routes': {f'{method}:{strategy}:{language}': {'question_similarity': 0.5, 'topic_coverage': 0.5}
                     for method in ['semantic', 'tfidf', 'bm25'] for strategy in ['english', 'direct', 'translate']
                     for language in ['en', 'hi', 'te', 'ta']}}


class Translator:
    def __init__(self):
        self.calls = []
        self.fail_query = self.fail_answer = False

    def translate_to_english(self, text, language):
        self.calls.append(('query', text, language))
        if self.fail_query:
            raise TranslationUnavailableError('secret path')
        return 'What is asthma?'

    def translate_from_english(self, text, language):
        self.calls.append(('answer', text, language))
        if self.fail_answer:
            raise TranslationUnavailableError('secret path')
        return {'hi': 'अस्थमा', 'te': 'ఆస్తమా', 'ta': 'ஆஸ்துமா'}[language]


class Retriever:
    def __init__(self):
        self.calls = []
        self.encoder = None
        self.fail_direct = False

    def _encoder(self):
        return self.encoder

    def retrieve(self, query, top_k):
        self.calls.append((query, top_k))
        if self.fail_direct and query != 'What is asthma?':
            raise RuntimeError('secret backend details')
        return [dict(ROW)]


def make_service():
    translator, retriever = Translator(), Retriever()
    pipeline = IndicMedPipeline(documents=pd.DataFrame([ROW]), translator=translator)
    pipeline.retrievers = {method: retriever for method in ['semantic', 'tfidf', 'bm25']}
    def factory(pipeline):
        gate = MedicalValidator(pipeline, policy=POLICY)
        gate.encode = lambda texts: np.ones((len(texts), 2))
        return gate
    return PipelineService(lambda: pipeline, validator_factory=factory), translator, retriever


@pytest.fixture
def gate():
    service, _, _ = make_service()
    service._ensure()
    return service._validator


@pytest.mark.parametrize('query', ['Who is Allu Arjun?', 'Who is Virat Kohli?', 'Who is the prime minister of India?',
    'What is React JS?', 'Who won the cricket match?', 'Tell me about the movie Pushpa.',
    'Who is Taylor Swift?', 'Explain JavaScript promises.', 'What does AL mean in baseball standings?'])
def test_obvious_nonmedical_intent(gate, query):
    assert gate.intent(query)['decision'] == 'out_of_scope'


@pytest.mark.parametrize('query', ['What is asthma?', 'What is AL amyloidosis?', 'Why do I feel dizzy?',
    'What causes frequent headaches?', 'What are the side effects of paracetamol?',
    'What disease did this person have?', 'How is pneumonia diagnosed?', 'What are the symptoms of diabetes?'])
def test_medical_intent(gate, query):
    assert gate.intent(query)['decision'] == 'medical'


@pytest.mark.parametrize('query', ['What is AL?', 'Tell me about it.', 'Is it serious?'])
def test_ambiguous_queries(gate, query):
    assert gate.intent(query)['decision'] == 'clarification_needed'


def test_rare_corpus_term_is_medical_without_fixed_keyword(gate):
    gate.entities.add('fabry')
    assert gate.intent('Tell me about Fabry')['reason'] == 'corpus_medical_terminology'


@pytest.mark.parametrize('query', ['अल्लू अर्जुन कौन हैं?', 'विराट कोहली कौन हैं?', 'పుష్ప సినిమా గురించి చెప్పండి.',
    'అల్లు అర్జున్ ఎవరు?', 'அல்லு அர்ஜுன் யார்?', 'புஷ்பா திரைப்படத்தைப் பற்றி சொல்லுங்கள்.'])
def test_native_nonmedical_context(gate, query):
    assert gate.native_intent(query)['decision'] == 'out_of_scope'


@pytest.mark.parametrize('query', ['इस व्यक्ति को कौन सा रोग था?', 'ఈ వ్యక్తికి ఏ వ్యాధి ఉంది?', 'இந்த நபருக்கு என்ன நோய் இருந்தது?'])
def test_native_person_question_with_medical_context_not_rejected(gate, query):
    assert gate.native_intent(query) is None


def test_relevance_checks_topic_and_requested_facet(gate):
    accepted, _, _ = gate.relevance('What is asthma?', ROW, 'semantic:english:en')
    assert accepted
    accepted, _, _ = gate.relevance('What is AL amyloidosis?', ROW, 'semantic:english:en')
    assert not accepted
    accepted, _, evidence = gate.relevance('How is asthma diagnosed?', ROW, 'semantic:english:en')
    assert not accepted and 'diagnosis' in evidence['missing_facets']


def test_raw_score_scale_cannot_override_evidence(gate):
    for score in [0.3, 10, 10000]:
        assert gate.relevance('What is asthma?', {**ROW, 'score': score}, 'bm25:english:en')[0]
        assert not gate.relevance('What is paracetamol?', {**ROW, 'score': score}, 'bm25:english:en')[0]


def test_missing_route_policy_abstains(gate):
    gate.policy = {}
    assert gate.relevance('What is asthma?', ROW, 'semantic:english:en')[1] == 'validation_unavailable'


def test_evidence_beyond_visible_answer_excerpt_is_not_counted(gate):
    candidate = {**ROW, 'answer': 'Asthma information. ' + 'Example text. ' * 150 + ' Diagnosis requires a test.'}
    enough, _, evidence = gate.relevance('How is asthma diagnosed?', candidate, 'semantic:english:en')
    assert not enough and 'diagnosis' in evidence['missing_facets']


def test_unsupported_medical_question_never_returns_unrelated_answer():
    service, translator, _ = make_service()
    response = service.ask(AskRequest(query='What is experimental Zorvex-99 syndrome?', language='en'))
    assert response['status'] == 'insufficient_evidence'
    assert 'answer' not in response and 'translated_answer' not in response
    assert not translator.calls


def test_outside_question_skips_retrieval_and_translation():
    service, translator, retriever = make_service()
    response = service.ask(AskRequest(query='Who is Allu Arjun?'))
    assert response['status'] == 'out_of_scope'
    assert not translator.calls and not retriever.calls


@pytest.mark.parametrize('language,query', [('hi', 'अस्थमा क्या है?'), ('te', 'ఆస్తమా అంటే ఏమిటి?'), ('ta', 'ஆஸ்துமா என்றால் என்ன?')])
def test_comparison_routing_and_cached_translation(language, query):
    service, translator, retriever = make_service()
    result = service.compare(CompareRequest(query=query, language=language, top_k=2))
    assert retriever.calls == [(query, 2), ('What is asthma?', 2)]
    assert result['direct']['status'] == result['translate']['status'] == 'success'
    assert result['direct']['retrieval_query'] == query
    assert result['translate']['retrieval_query'] == 'What is asthma?'
    assert result['direct']['retrieved_question'] == ROW['question']
    for branch in ['direct', 'translate']:
        assert result[branch]['source_url'] == ROW['source_url']
        assert result[branch]['document_id'] == ROW['id']
    assert sum(call[0] == 'query' for call in translator.calls) == 1
    assert sum(call[0] == 'answer' for call in translator.calls) == 1


def test_english_comparison_reuses_one_inference():
    service, translator, retriever = make_service()
    result = service.compare(CompareRequest(query='What is asthma?', language='en'))
    assert result['equivalent'] and result['direct'] == result['translate']
    assert len(retriever.calls) == 1 and not translator.calls


def test_one_strategy_failure_preserves_other_result():
    service, _, retriever = make_service()
    retriever.fail_direct = True
    result = service.compare(CompareRequest(query='ఆస్తమా అంటే ఏమిటి?', language='te'))
    assert result['direct']['status'] == 'clarification_needed'
    assert result['translate']['status'] == 'success'
    assert 'secret' not in json.dumps(result)


def test_translation_unavailable_does_not_classify_as_medical_or_outside():
    service, translator, _ = make_service()
    translator.fail_query = True
    result = service.ask(AskRequest(query='ఆస్తమా అంటే ఏమిటి?', language='te'))
    assert result['status'] == 'clarification_needed' and result['reason'] == 'validation_unavailable'
    assert 'answer' not in result


def test_answer_translation_failure_has_explicit_english_fallback():
    service, translator, _ = make_service()
    translator.fail_answer = True
    result = service.compare(CompareRequest(query='ఆస్తమా అంటే ఏమిటి?', language='te'))
    assert result['translate']['status'] == 'success'
    assert result['translate']['translation_warning']
    assert result['translate']['translated_answer'] == ROW['answer']
    assert 'secret' not in json.dumps(result)


def test_compare_api_and_nonbreaking_success_contract():
    service, _, _ = make_service()
    app.dependency_overrides[get_pipeline_service] = lambda: service
    try:
        with TestClient(app) as client:
            result = client.post('/api/compare', json={'query': 'What is asthma?', 'top_k': 2})
            assert result.status_code == 200 and result.json()['equivalent']
            assert client.post('/api/compare', json={'query': 'asthma', 'retrieval_method': 'bm25'}).status_code == 422
            result = client.post('/api/ask', json={'query': 'Who is Allu Arjun?'})
            assert result.status_code == 200 and result.json()['status'] == 'out_of_scope'
            assert 'answer' not in result.json()
    finally:
        app.dependency_overrides.clear()


def test_bounded_caches_reuse_inputs_and_do_not_cache_failures():
    class Encoder:
        def __init__(self): self.calls = []
        def encode(self, texts):
            self.calls.append(texts)
            return np.ones((len(texts), 2))
    encoder = Encoder()
    cache = EncoderCache(encoder, limit=2)
    cache.encode(['asthma', 'diabetes'])
    cache.encode(['asthma'])
    assert len(encoder.calls) == 1
    cache.encode(['headache'])
    assert len(cache.values) == 2
    translator = Translator()
    cached = TranslationCache(translator, limit=1)
    translator.fail_query = True
    with pytest.raises(TranslationUnavailableError): cached.translate_to_english('x', 'te')
    translator.fail_query = False
    assert cached.translate_to_english('x', 'te') == 'What is asthma?'
    cached.translate_to_english('x', 'te')
    assert len(translator.calls) == 2


@pytest.mark.parametrize('query', ['What is ALS?', 'What is HIV?', 'What is COPD?'])
def test_medical_acronyms_with_context_are_preserved(gate, query):
    assert gate.intent(query)['decision'] == 'medical'


@pytest.mark.parametrize('query', ['What does TB mean on a hard drive?', 'Explain the ALS algorithm for movie recommendations.'])
def test_acronym_hard_negatives_use_context(gate, query):
    assert gate.intent(query)['decision'] == 'out_of_scope'


def test_unavailable_encoder_abstains_for_uncertain_intent(gate):
    def fail(_texts): raise RuntimeError('private model details')
    gate.encode = fail
    service, _, _ = make_service()
    service._ensure()
    service._validator = gate
    result = service.ask(AskRequest(query='Help me understand the thing I am experiencing', language='en'))
    assert result['status'] == 'clarification_needed'
    assert result['reason'] == 'validation_unavailable'
    assert 'answer' not in result


def test_comparison_holds_one_lock_across_both_branches():
    service, _, retriever = make_service()
    entered, release = Event(), Event()
    original = retriever.retrieve
    def blocking(query, top_k):
        entered.set()
        assert release.wait(5)
        return original(query, top_k)
    retriever.retrieve = blocking
    with ThreadPoolExecutor() as pool:
        future = pool.submit(service.compare, CompareRequest(query='ఆస్తమా అంటే ఏమిటి?', language='te'))
        try:
            assert entered.wait(5)
            with pytest.raises(PipelineBusyError):
                service.ask(AskRequest(query='What is asthma?'))
        finally:
            release.set()
        result = future.result()
    assert result['direct']['status'] == result['translate']['status'] == 'success'
