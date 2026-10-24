from __future__ import annotations

from typing import Any


def build_response(query: str, language: str, english_query: str, selected: dict[str, Any],
                   translated_answer: str, related: list[dict[str, Any]],
                   retrieval_strategy: str = "semantic", translation_warning: str | None = None) -> dict[str, Any]:
    return {
        "query": query,
        "detected_language": language,
        "selected_language": language,
        "retrieval_strategy": retrieval_strategy,
        "english_query": english_query,
        "answer": selected["answer"],
        "translated_answer": translated_answer,
        "category": selected.get("category", ""),
        "source": selected.get("source", ""),
        "source_url": selected.get("source_url", ""),
        "similarity_score": float(selected["score"]),
        "related_questions": [item["question"] for item in related],
        "document_id": selected["id"],
        "translation_warning": translation_warning,
    }
