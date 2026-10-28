"""Opt-in application gate calibration. NEVER writes existing research outputs.

Only the calibration split chooses policy cutoffs. Holdout examples report errors.
Candidate relevance labels use the manually authored topic targets in cases.json;
they measure topic support, not medical correctness or answer completeness.
"""
import hashlib
import json
import sys
import argparse
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.services.pipeline import PipelineService
from backend.services.validation import MEDICAL_ANCHORS, OTHER_ANCHORS, cosine, tokens
from src.utils.helpers import resolve_project_path


def choose_cutoff(positives, negatives):
    """Empirical, conservative risk tradeoff: a false accept costs 3 rejects."""
    if not positives:
        return 1.01  # No positive support for this route: always abstain.
    candidates = sorted(set([min(positives), *positives, *[v + 1e-6 for v in negatives]]))
    return min(candidates, key=lambda t: (3 * sum(v >= t for v in negatives) + sum(v < t for v in positives), -t))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--reuse-observations', action='store_true', help='Refit/report using previously measured cosine scores and translations for the exact same cases, dataset and model.')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    cases = json.loads((root / 'validation/cases.json').read_text(encoding='utf-8'))
    service = PipelineService()
    service._ensure()
    gate, pipeline = service._validator, service._pipeline
    anchors = None if args.reuse_observations else gate.encode([*MEDICAL_ANCHORS, *OTHER_ANCHORS])
    domain_rows, route_rows = [], defaultdict(list)
    if args.reuse_observations:
        previous_policy = json.loads((root / 'config/validation_policy.json').read_text(encoding='utf-8'))
        assert previous_policy['cases_sha256'] == hashlib.sha256((root / 'validation/cases.json').read_bytes()).hexdigest(), 'Cases changed; collect new observations.'
        assert previous_policy['dataset_sha256'] == hashlib.sha256(resolve_project_path(pipeline.config['paths']['dataset']).read_bytes()).hexdigest(), 'Dataset changed.'
        assert previous_policy['embedding_model'] == pipeline.config['models']['embedding_model'], 'Model changed.'
        previous = json.loads((root / 'validation/calibration_report.json').read_text(encoding='utf-8'))
        domain_rows, route_rows = previous['domain_examples'], previous['retrieval_routes']
        documents = pipeline.documents.set_index('id')
        for rows in route_rows.values():
            for row in rows:
                row.update(gate.lexical_features(row['english_query'], documents.loc[row['document_id']].to_dict()))
    for index, case in enumerate([] if args.reuse_observations else cases):
        query, language = case['query'], case['language']
        native = gate.native_intent(query) if language != 'en' else None
        # Translate even rejected native cases for calibration of the evidence
        # gate independently of the first intent gate. Production skips this work.
        english = query if language == 'en' else pipeline.translator.translate_to_english(query, language)
        vector = gate.encode([english])[0]
        margin = max(cosine(vector, v) for v in anchors[:len(MEDICAL_ANCHORS)]) - max(cosine(vector, v) for v in anchors[len(MEDICAL_ANCHORS):])
        domain_rows.append({**case, 'english_query': english, 'margin': margin})
        # Observe ALL domains for route calibration, including hard negatives.
        methods = ['semantic', 'tfidf', 'bm25']
        strategies = ['english'] if language == 'en' else ['translate', 'direct']
        for method in methods:
            for strategy in strategies:
                if strategy == 'direct' and method != 'semantic':
                    continue
                representation = query if strategy == 'direct' else english
                results = pipeline._retriever(method).retrieve(representation, 3)
                if not results:
                    continue
                item = results[0]
                features = gate.features(english, item)
                # Authored entity targets are independent of the model's score.
                # Unsupported synthetic cases have targets absent from MedQuAD.
                content = tokens(str(item['question']) + ' ' + str(item['answer']))
                targets = set(case.get('topics', []))
                relevant = case['domain'] == 'medical' and bool(targets) and targets <= content
                route_rows[f'{method}:{strategy}:{language}'].append({
                    'split': case['split'], 'query': query, 'english_query': english,
                    'document_id': item['id'], 'faq_question': item['question'], 'raw_score': float(item['score']),
                    'relevant_topic': relevant, **features})
        print(f'{index + 1}/{len(cases)} {language}: {query}', flush=True)
    calibration = [r for r in domain_rows if r['split'] == 'calibration']
    medical_margin = choose_cutoff([r['margin'] for r in calibration if r['domain'] == 'medical'],
                                   [r['margin'] for r in calibration if r['domain'] != 'medical'])
    outside_margin = -choose_cutoff([-r['margin'] for r in calibration if r['domain'] == 'out_of_scope'],
                                    [-r['margin'] for r in calibration if r['domain'] != 'out_of_scope'])
    # Keep a nonempty uncertain region rather than forcing binary classification.
    outside_margin = min(outside_margin, medical_margin - 1e-6)
    policy = {'version': 1, 'embedding_model': pipeline.config['models']['embedding_model'],
              'dataset_sha256': hashlib.sha256(resolve_project_path(pipeline.config['paths']['dataset']).read_bytes()).hexdigest(),
              'cases_sha256': hashlib.sha256((root / 'validation/cases.json').read_bytes()).hexdigest(),
              'intent': {'medical_margin': medical_margin, 'outside_margin': outside_margin}, 'routes': {}}
    for route, rows in route_rows.items():
        subset = [r for r in rows if r['split'] == 'calibration']
        positives = [r for r in subset if r['relevant_topic']]
        negatives = [r for r in subset if not r['relevant_topic']]
        # Coverage derives from the observed positive distribution, per route.
        coverage = min([r['topic_coverage'] for r in positives], default=1.01)
        # Fit the semantic cutoff jointly with topic/facet checks. A negative
        # already excluded for missing the topic must not force rejection of a
        # supported symptom paraphrase merely because it has a higher cosine.
        eligible_negatives = [r for r in negatives if r['topic_coverage'] >= max(coverage, 1e-6) and not r['missing_facets']]
        threshold = choose_cutoff([r['question_similarity'] for r in positives], [r['question_similarity'] for r in eligible_negatives])
        policy['routes'][route] = {'question_similarity': threshold, 'topic_coverage': max(coverage, 1e-6),
                                    'positive_count': len(positives), 'negative_count': len(negatives)}
    (root / 'config/validation_policy.json').write_text(json.dumps(policy, indent=2), encoding='utf-8')
    gate.policy = policy
    summary = {}
    for split in ['calibration', 'holdout']:
        rows = [r for r in domain_rows if r['split'] == split]
        for row in rows:
            native = gate.native_intent(row['query']) if row['language'] != 'en' else None
            row['observed_domain'] = (native or gate.intent(row['english_query'], observed_margin=row['margin']))['decision']
        summary[split] = {'count': len(rows),
            'false_accepts': sum(r['domain'] != 'medical' and r['observed_domain'] == 'medical' for r in rows),
            'false_rejects': sum(r['domain'] == 'medical' and r['observed_domain'] == 'out_of_scope' for r in rows),
            'medical_abstentions': sum(r['domain'] == 'medical' and r['observed_domain'] == 'clarification_needed' for r in rows),
            'domain_mismatches': [{k: r[k] for k in ['query', 'domain', 'observed_domain']} for r in rows if r['domain'] != r['observed_domain']]}
    for route, rows in route_rows.items():
        settings = policy['routes'][route]
        for row in rows:
            row['accepted'] = (row['question_similarity'] >= settings['question_similarity'] and row['topic_coverage'] >= settings['topic_coverage'] and not row['missing_facets'])
    retrieval_summary = {route: {split: {
        'count': sum(r['split'] == split for r in rows),
        'topic_support_false_accepts': sum(r['split'] == split and not r['relevant_topic'] and r['accepted'] for r in rows),
        'supported_topic_withheld': sum(r['split'] == split and r['relevant_topic'] and not r['accepted'] for r in rows),
    } for split in ['calibration', 'holdout']} for route, rows in route_rows.items()}
    report = {'limitations': 'Small authored development examples; holdout cases were inspected during fixes and are not an untouched statistical test set. Topic labels do not establish clinical accuracy or full answerability. No original retrieval benchmark was rerun.',
              'domain': summary, 'domain_examples': domain_rows, 'retrieval_summary': retrieval_summary, 'retrieval_routes': dict(route_rows)}
    (root / 'validation/calibration_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=False, indent=2), flush=True)


if __name__ == '__main__':
    main()
