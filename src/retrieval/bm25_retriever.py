from __future__ import annotations

import re
from typing import Any

import pandas as pd
from rank_bm25 import BM25Okapi
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS

from .base import ranked_records, validate_documents


TOKEN_PATTERN = re.compile(r"(?u)\b\w\w+\b")


def tokenize(text: str) -> list[str]:
    return [token for token in TOKEN_PATTERN.findall(text.lower()) if token not in ENGLISH_STOP_WORDS]


class BM25Retriever:
    """Okapi BM25 retrieval over tokenized medical answer documents."""

    def __init__(self, text_field: str = "answer") -> None:
        self.text_field = text_field
        self.documents: pd.DataFrame | None = None
        self.index: BM25Okapi | None = None

    def fit(self, documents: pd.DataFrame) -> "BM25Retriever":
        self.documents = validate_documents(documents, self.text_field)
        corpus = [tokenize(text) for text in self.documents[self.text_field]]
        self.index = BM25Okapi(corpus)
        return self

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self.documents is None or self.index is None:
            raise RuntimeError("Call fit() before retrieve()")
        tokens = tokenize(query)
        if not tokens:
            return []
        return ranked_records(self.documents, self.index.get_scores(tokens), top_k)
