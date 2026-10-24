from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.pipeline import IndicMedPipeline
from src.translation.languages import contains_expected_script
from src.utils.helpers import resolve_project_path

QUERIES = [
    ("en", "What is asthma?"),
    ("hi", "मधुमेह के लक्षण क्या हैं?"),
    ("te", "మైగ్రేన్‌కు కారణాలు ఏమిటి?"),
    ("ta", "காசநோய் எவ்வாறு கண்டறியப்படுகிறது?"),
]


def main() -> None:
    pipeline = IndicMedPipeline()
    summaries = []
    for language, query in QUERIES:
        result = pipeline.ask(query, language=language, retrieval_method="semantic",
                              multilingual_strategy="translate", top_k=3)
        if not result["answer"] or not result["source"]:
            raise RuntimeError(f"Incomplete grounded response for {language}")
        if not contains_expected_script(result["translated_answer"], language):
            raise RuntimeError(f"Unexpected answer script for {language}: {result['translated_answer'][:100]}")
        summaries.append({
            "language": language, "query": query, "english_query": result["english_query"],
            "retrieval_strategy": result["retrieval_strategy"], "document_id": result["document_id"],
            "category": result["category"], "source": result["source"],
            "source_url": result["source_url"], "similarity_score": result["similarity_score"],
            "grounded_english_answer": result["answer"], "translated_answer": result["translated_answer"],
        })
        print(f"{language}: {result['english_query']} -> {result['category']} | {result['source']} | {result['similarity_score']:.4f}")
        print(result["translated_answer"][:300])
    destination = resolve_project_path("outputs/results/multilingual_pipeline_demos.json")
    destination.write_text(json.dumps(summaries, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Saved: {destination}")


if __name__ == "__main__":
    main()
