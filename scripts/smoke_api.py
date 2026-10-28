"""Opt-in real-model API smoke test. Prints checks; never writes research artifacts.

Start the backend first, then: python scripts/smoke_api.py
"""
import argparse
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.translation.languages import contains_expected_script

QUESTIONS = {"en": "What is asthma?", "hi": "मधुमेह के लक्षण क्या हैं?",
             "te": "మైగ్రేన్‌కు కారణాలు ఏమిటి?", "ta": "காசநோய் எவ்வாறு கண்டறியப்படுகிறது?"}


def main(base_url):
    failures = 0
    with httpx.Client(base_url=base_url, timeout=600) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        cases = [(language, "semantic", "translate") for language in QUESTIONS]
        cases += [(language, "semantic", "direct") for language in ("hi", "te", "ta")]
        cases += [("en", method, "translate") for method in ("tfidf", "bm25")]
        for language, method, strategy in cases:
            started = time.perf_counter()
            response = client.post("/api/ask", json={"query": QUESTIONS[language], "language": language,
                "retrieval_method": method, "multilingual_strategy": strategy, "top_k": 3})
            result = response.json()
            approved = response.status_code == 200 and result.get('status') == 'success' and bool(result.get('document_id')) and bool(result.get('answer'))
            approved = approved and not result.get('translation_warning') and contains_expected_script(result.get('translated_answer', ''), language)
            withheld = response.status_code == 200 and strategy == 'direct' and result.get('status') == 'insufficient_evidence' and 'answer' not in result
            valid = approved or withheld
            print(f"{'PASS' if valid else 'FAIL'} {language} {method} {strategy}: HTTP {response.status_code}, {time.perf_counter() - started:.1f}s", flush=True)
            if approved:
                print(f"  document={result['document_id']} score={result['similarity_score']:.3f} strategy={result['retrieval_strategy']}", flush=True)
                print(f"  English query: {result['english_query']}", flush=True)
                print(f"  Answer preview: {result['translated_answer'][:180]}", flush=True)
            elif withheld:
                print('  Weak direct-retrieval evidence was explicitly withheld; no answer displayed.', flush=True)
            else:
                print(f"  {result.get('message') or result.get('translation_warning') or 'Invalid response'}", flush=True)
                failures += 1
    return 1 if failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    sys.exit(main(parser.parse_args().base_url))
