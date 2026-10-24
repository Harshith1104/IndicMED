import pandas as pd
import pytest

from src.pipeline import IndicMedPipeline
from src.translation import TranslationUnavailableError


class IdentityTranslator:
    def __init__(self):
        self.to_english_calls = 0
        self.from_english_calls = 0

    def translate_to_english(self, text, language):
        self.to_english_calls += 1
        return text

    def translate_from_english(self, text, language):
        self.from_english_calls += 1
        return text


class RecordingTranslator(IdentityTranslator):
    def translate_to_english(self, text, language):
        self.to_english_calls += 1
        return "high blood glucose"

    def translate_from_english(self, text, language):
        self.from_english_calls += 1
        return "తెలుగు సమాధానం"


class FakeSemanticRetriever:
    def __init__(self, result):
        self.result = result
        self.queries = []

    def retrieve(self, query, top_k):
        self.queries.append(query)
        return [self.result]


class UnavailableTranslator:
    def translate_to_english(self, text, language):
        raise TranslationUnavailableError("test unavailable")

    def translate_from_english(self, text, language):
        raise TranslationUnavailableError("test unavailable")


def test_pipeline_returns_grounded_metadata() -> None:
    documents = pd.DataFrame([{
        "id": "d1", "question": "What is diabetes?", "answer": "Diabetes can cause high blood glucose.",
        "category": "diabetes", "source": "NIH", "source_url": "https://example.test/diabetes"
    }])
    pipeline = IndicMedPipeline(documents=documents, translator=IdentityTranslator())
    result = pipeline.ask("high blood glucose", language="en", retrieval_method="tfidf", top_k=1)
    assert result["document_id"] == "d1"
    assert result["source"] == "NIH"
    assert result["answer"] == documents.iloc[0]["answer"]


def test_english_skips_translation() -> None:
    documents = pd.DataFrame([{"id": "d1", "question": "Diabetes?", "answer": "High blood glucose.",
                               "category": "diabetes", "source": "NIH", "source_url": ""}])
    translator = IdentityTranslator()
    pipeline = IndicMedPipeline(documents=documents, translator=translator)
    pipeline.ask("high blood glucose", "en", "tfidf", 1, "translate")
    assert translator.to_english_calls == translator.from_english_calls == 0


def test_direct_and_translate_multilingual_routing() -> None:
    row = {"id": "d1", "question": "Diabetes?", "answer": "High blood glucose.",
           "category": "diabetes", "source": "NIH", "source_url": ""}
    translator = RecordingTranslator()
    pipeline = IndicMedPipeline(documents=pd.DataFrame([row]), translator=translator)
    fake = FakeSemanticRetriever({**row, "score": 0.8, "rank": 1})
    pipeline.retrievers["semantic"] = fake
    direct = pipeline.ask("మధుమేహం", "te", "semantic", 1, "direct")
    translated = pipeline.ask("మధుమేహం", "te", "semantic", 1, "translate")
    assert fake.queries == ["మధుమేహం", "high blood glucose"]
    assert direct["retrieval_strategy"] == "direct_semantic"
    assert translated["retrieval_strategy"] == "translate_semantic"
    assert translated["english_query"] == "high blood glucose"
    assert translated["translated_answer"] == "తెలుగు సమాధానం"


def test_translation_failure_keeps_direct_retrieval_usable() -> None:
    row = {"id": "d1", "question": "Diabetes?", "answer": "High blood glucose.",
           "category": "diabetes", "source": "NIH", "source_url": ""}
    pipeline = IndicMedPipeline(documents=pd.DataFrame([row]), translator=UnavailableTranslator())
    pipeline.retrievers["semantic"] = FakeSemanticRetriever({**row, "score": 0.7, "rank": 1})
    result = pipeline.ask("మధుమేహం", "te", "semantic", 1, "direct")
    assert result["translated_answer"] == row["answer"]
    assert "showing grounded English answer" in result["translation_warning"]
    with pytest.raises(TranslationUnavailableError, match="Select direct"):
        pipeline.ask("మధుమేహం", "te", "semantic", 1, "translate")
