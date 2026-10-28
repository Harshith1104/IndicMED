from __future__ import annotations

from pathlib import Path
import pickle
from typing import Any

import numpy as np
import pandas as pd

from src.preprocessing.language_detector import detect_language
from src.preprocessing.normalizer import normalize_text
from src.qa.answer_selector import select_answer
from src.qa.answer_simplifier import simplify_answer
from src.qa.response_generator import build_response
from src.retrieval import BM25Retriever, SemanticRetriever, TfidfRetriever
from src.translation import IndicTranslator, TranslationUnavailableError
from src.utils.helpers import load_config, resolve_project_path


class IndicMedPipeline:
    def __init__(self, config_path: str | Path = "config/config.yaml", documents: pd.DataFrame | None = None,
                 translator: Any | None = None) -> None:
        self.config = load_config(config_path)
        self.documents = documents if documents is not None else pd.read_csv(
            resolve_project_path(self.config["paths"]["dataset"])
        ).fillna("")
        translation = self.config["models"]["translation"]
        self.translator = translator or IndicTranslator(translation["en_to_indic"], translation["indic_to_en"])
        self.retrievers: dict[str, Any] = {}

    def _retriever(self, method: str):
        if method in self.retrievers:
            return self.retrievers[method]
        if method == "tfidf":
            retriever = TfidfRetriever().fit(self.documents)
        elif method == "bm25":
            retriever = BM25Retriever().fit(self.documents)
        elif method == "semantic":
            embeddings_path = resolve_project_path(self.config["paths"]["embeddings"])
            if not embeddings_path.exists():
                raise FileNotFoundError("Semantic embeddings are missing. Run: python scripts/build_embeddings.py")
            metadata_path = resolve_project_path(self.config["paths"]["metadata"])
            if not metadata_path.exists():
                raise FileNotFoundError("Semantic index metadata is missing. Run: python scripts/build_embeddings.py")
            with metadata_path.open("rb") as handle:
                metadata = pickle.load(handle)
            if metadata.get("ids") != self.documents["id"].tolist():
                raise ValueError("Semantic index metadata does not match the current dataset; rebuild embeddings")
            if metadata.get("model_name") != self.config["models"]["embedding_model"]:
                raise ValueError("Semantic index model does not match config; rebuild embeddings")
            retriever = SemanticRetriever(self.config["models"]["embedding_model"]).fit(
                self.documents, np.load(embeddings_path)
            )
        else:
            raise ValueError(f"Unknown retrieval method: {method}")
        self.retrievers[method] = retriever
        return retriever

    def ask(self, query: str, language: str | None = None, retrieval_method: str | None = None,
            top_k: int | None = None, multilingual_strategy: str | None = None,
            *, retrieval_guard: Any | None = None) -> dict[str, Any]:
        normalized = normalize_text(query)
        if not normalized:
            raise ValueError("Question cannot be empty")
        language = detect_language(normalized) if language in (None, "auto") else language
        if language not in self.config["languages"]["supported"]:
            raise ValueError(f"Unsupported language: {language}")
        method = retrieval_method or self.config["retrieval"]["default_method"]
        strategy = multilingual_strategy or self.config["retrieval"].get("default_multilingual_strategy", "translate")
        if strategy not in {"direct", "translate"}:
            raise ValueError(f"Unknown multilingual strategy: {strategy}")
        english_query = normalized
        if language == "en":
            retrieval_strategy = method
        elif strategy == "direct":
            if method != "semantic":
                raise ValueError("Direct multilingual retrieval is available only with semantic retrieval")
            retrieval_strategy = "direct_semantic"
        else:
            try:
                english_query = self.translator.translate_to_english(normalized, language)
            except TranslationUnavailableError as error:
                raise TranslationUnavailableError(
                    "Translate-then-retrieve is unavailable. Select direct multilingual retrieval or configure IndicTrans2."
                ) from error
            retrieval_strategy = f"translate_{method}"
        results = self._retriever(method).retrieve(
            normalized if retrieval_strategy == "direct_semantic" else english_query,
            top_k or self.config["retrieval"]["top_k"],
        )
        # Optional application safety gate. Research callers retain the exact
        # original ranking/selection behavior when this callback is absent.
        if retrieval_guard is not None:
            retrieval_guard(results, english_query, retrieval_strategy)
        selected = select_answer(results)
        if selected is None:
            raise LookupError("No relevant FAQ was found")
        answer = simplify_answer(selected["answer"], self.config["application"]["max_answer_characters"])
        selected = {**selected, "answer": answer}
        translation_warning = None
        if language == "en":
            translated = answer
        else:
            try:
                translated = self.translator.translate_from_english(answer, language)
            except TranslationUnavailableError as error:
                translated = answer
                translation_warning = f"Answer translation unavailable; showing grounded English answer. {error}"
        return build_response(normalized, language, english_query, selected, translated, results[1:],
                              retrieval_strategy, translation_warning)
