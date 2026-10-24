from __future__ import annotations

from typing import Any, Protocol

import numpy as np
import pandas as pd

from .base import validate_documents
from .vector_index import NumpyVectorIndex


class Encoder(Protocol):
    def encode(self, sentences: Any, **kwargs: Any) -> np.ndarray: ...


class SemanticRetriever:
    """Multilingual dense retrieval with an injectable encoder for easy testing."""

    def __init__(self, model_name: str, text_field: str = "answer", encoder: Encoder | None = None) -> None:
        self.model_name = model_name
        self.text_field = text_field
        self.encoder = encoder
        self.documents: pd.DataFrame | None = None
        self.index: NumpyVectorIndex | None = None

    def _encoder(self) -> Encoder:
        if self.encoder is None:
            from sentence_transformers import SentenceTransformer
            self.encoder = SentenceTransformer(self.model_name)
        return self.encoder

    def fit(self, documents: pd.DataFrame, embeddings: np.ndarray | None = None) -> "SemanticRetriever":
        self.documents = validate_documents(documents, self.text_field)
        vectors = embeddings
        if vectors is None:
            vectors = self._encoder().encode(
                self.documents[self.text_field].tolist(), batch_size=32, show_progress_bar=True
            )
        if len(vectors) != len(self.documents):
            raise ValueError("Embedding count does not match document count")
        self.index = NumpyVectorIndex(np.asarray(vectors))
        return self

    def retrieve(self, query: str, top_k: int = 3) -> list[dict[str, Any]]:
        if self.documents is None or self.index is None:
            raise RuntimeError("Call fit() before retrieve()")
        if not query or not query.strip():
            return []
        query_vector = self._encoder().encode([query])
        return self._results_from_vector(np.asarray(query_vector)[0], top_k)

    def retrieve_batch(self, queries: list[str], top_k: int = 3) -> list[list[dict[str, Any]]]:
        """Encode multiple queries together for efficient evaluation."""
        if self.documents is None or self.index is None:
            raise RuntimeError("Call fit() before retrieve_batch()")
        vectors = self._encoder().encode(queries, batch_size=32, show_progress_bar=False)
        return [self._results_from_vector(vector, top_k) for vector in vectors]

    def _results_from_vector(self, vector: np.ndarray, top_k: int) -> list[dict[str, Any]]:
        assert self.documents is not None and self.index is not None
        scores, indices = self.index.search(vector, min(top_k, len(self.documents)))
        results = []
        for rank, (score, index) in enumerate(zip(scores, indices), 1):
            item = self.documents.iloc[int(index)].to_dict()
            item.update(score=float(score), rank=rank)
            results.append(item)
        return results
