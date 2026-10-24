import pandas as pd
import numpy as np
import pytest

from src.retrieval import BM25Retriever, TfidfRetriever
from src.retrieval.semantic_retriever import SemanticRetriever


@pytest.fixture
def documents() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {"id": "diabetes", "question": "What is diabetes?", "answer": "Diabetes causes high blood glucose and may cause thirst and frequent urination."},
            {"id": "migraine", "question": "What is migraine?", "answer": "Migraine is a headache that may include nausea and sensitivity to light."},
            {"id": "asthma", "question": "What is asthma?", "answer": "Asthma affects the airways and can cause wheezing and shortness of breath."},
        ]
    )


@pytest.mark.parametrize("retriever_class", [TfidfRetriever, BM25Retriever])
def test_retrievers_rank_relevant_answer_first(retriever_class, documents: pd.DataFrame) -> None:
    results = retriever_class().fit(documents).retrieve("high blood glucose thirst", top_k=2)
    assert len(results) == 2
    assert results[0]["id"] == "diabetes"
    assert results[0]["score"] >= results[1]["score"]
    assert [item["rank"] for item in results] == [1, 2]


@pytest.mark.parametrize("retriever_class", [TfidfRetriever, BM25Retriever])
def test_empty_query_returns_no_results(retriever_class, documents: pd.DataFrame) -> None:
    assert retriever_class().fit(documents).retrieve("   ") == []


class FakeEncoder:
    def encode(self, sentences, **kwargs):
        vectors = []
        for text in sentences:
            lowered = text.lower()
            vectors.append([float("glucose" in lowered or "diabetes" in lowered), float("headache" in lowered)])
        return np.asarray(vectors, dtype=np.float32)


def test_semantic_retriever_api_without_model_download(documents: pd.DataFrame) -> None:
    retriever = SemanticRetriever("unused", encoder=FakeEncoder()).fit(documents)
    results = retriever.retrieve("diabetes glucose", 1)
    assert results[0]["id"] == "diabetes"
    batch = retriever.retrieve_batch(["diabetes glucose", "headache"], 1)
    assert [items[0]["id"] for items in batch] == ["diabetes", "migraine"]
