"""Real API validation/comparison checks; writes only the new validation report."""
import json
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def main():
    rows = []
    cases = json.loads((ROOT / 'validation/cases.json').read_text(encoding='utf-8'))
    with httpx.Client(base_url='http://127.0.0.1:8000', timeout=600) as client:
        for case in cases:
            response = client.post('/api/ask', json={'query': case['query'], 'language': case['language']})
            result = response.json()
            observed = result.get('validation', {}).get('intent', {}).get('decision', result.get('status', 'error'))
            valid = response.status_code == 200 and observed == case['domain']
            if case['domain'] != 'medical':
                valid = valid and 'answer' not in result and 'translated_answer' not in result
            if case.get('expected_status'):
                valid = valid and result.get('status') == case['expected_status']
            rows.append({**case, 'observed_domain': observed, 'status': result.get('status'), 'passed': valid,
                         'reason': result.get('reason'), 'document_id': result.get('document_id'),
                         'candidate_question': result.get('candidate', {}).get('question') if result.get('candidate') else None})
            print(f"{'PASS' if valid else 'FAIL'} {case['language']} {case['query']} -> {result.get('status')} ({observed})", flush=True)
        comparisons = []
        for language, query in [('en', 'What is asthma?'), ('hi', 'मधुमेह के लक्षण क्या हैं?'),
                                ('te', 'మైగ్రేన్‌కు కారణాలు ఏమిటి?'), ('ta', 'காசநோய் எவ்வாறு கண்டறியப்படுகிறது?')]:
            response = client.post('/api/compare', json={'query': query, 'language': language, 'top_k': 3})
            result = response.json()
            valid = response.status_code == 200 and result.get('retrieval_method') == 'semantic'
            if valid:
                valid = result['translate']['status'] == 'success'
                valid = valid and result['direct'].get('retrieval_query', result['direct'].get('candidate', {}).get('retrieval_query') if result['direct'].get('candidate') else query) == query
                if language == 'en':
                    valid = valid and result['equivalent'] and result['direct'] == result['translate']
            comparisons.append({'language': language, 'passed': valid, 'response': result})
            print(f"{'PASS' if valid else 'FAIL'} comparison {language}", flush=True)
    summary = {'examples': len(rows), 'passed': sum(r['passed'] for r in rows),
               'false_domain_accepts': sum(r['domain'] != 'medical' and r['observed_domain'] == 'medical' for r in rows),
               'false_domain_rejects': sum(r['domain'] == 'medical' and r['observed_domain'] == 'out_of_scope' for r in rows),
               'medical_domain_abstentions': sum(r['domain'] == 'medical' and r['observed_domain'] == 'clarification_needed' for r in rows),
               'medical_answers_withheld': sum(r['domain'] == 'medical' and r['status'] != 'success' for r in rows),
               'comparisons_passed': sum(r['passed'] for r in comparisons)}
    report = {'summary': summary, 'limitation': 'Authored development examples, including inspected holdout cases; not general classifier accuracy or clinical answer validation.',
              'cases': rows, 'comparisons': comparisons}
    (ROOT / 'validation/application_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, indent=2), flush=True)
    return 0 if all(r['passed'] for r in rows + comparisons) else 1


if __name__ == '__main__':
    sys.exit(main())
