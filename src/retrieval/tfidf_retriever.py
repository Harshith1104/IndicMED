from __future__ import annotations

from typing import Any

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel

from .base import ranked_records, validate_documents


class TfidfRetriever:
    """Word and bigram TF-IDF retrieval over medical answer documents."""

    def __init__(self, text_field: str = "answer") -> None:
        self.text_field = text_field
        self.vectorizer = TfidfVectorizer(lowercase=True, ngram_range=(1, 2), stop_words="english")
        self.documents: pd.DataFrame | None = None
        self.matrix: Any = None

    def fit(self, documents: pd.DataFrame) -> "TfidfRetriever":
        self.documents = validate_documents(documents, self.text_field)
        self.matrix = self.vectorizer.fit_transform(self.documents[self.text_field])
        return self

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self.documents is None or self.matrix is None:
            raise RuntimeError("Call fit() before retrieve()")
        if not query or not query.strip():
            return []
        scores = linear_kernel(self.vectorizer.transform([query]), self.matrix)[0]
        return ranked_records(self.documents, scores, top_k)

