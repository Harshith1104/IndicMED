from __future__ import annotations

import numpy as np


class NumpyVectorIndex:
    """Small, portable cosine-similarity index requiring no FAISS installation."""

    def __init__(self, vectors: np.ndarray) -> None:
        values = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(values, axis=1, keepdims=True)
        self.vectors = values / np.maximum(norms, 1e-12)

    def search(self, query_vector: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        query = np.asarray(query_vector, dtype=np.float32).reshape(1, -1)
        query /= np.maximum(np.linalg.norm(query, axis=1, keepdims=True), 1e-12)
        scores = (self.vectors @ query.T).ravel()
        order = np.argsort(scores, kind="stable")[::-1][:top_k]
        return scores[order], order

