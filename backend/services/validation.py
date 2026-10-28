"""Conservative application validation; never alters the research retrievers.

Intent and answerability are separate. A medical question can be unanswerable.
No raw TF-IDF/BM25/cross-lingual similarity cutoff is shared across routes.
"""
import hashlib
import json
import re
from pathlib import Path


from src.preprocessing.normalizer import normalize_text
from src.utils.helpers import resolve_project_path

POLICY_PATH = resolve_project_path('config/validation_policy.json')
MEDICAL_ANCHORS = [
    'What medical condition causes these symptoms?', 'Why do I feel unwell and dizzy?',
    'What causes a persistent headache?', 'How is a disease diagnosed?',
    'What are the risks and side effects of a medicine?', 'How can I prevent an infection?',
    'How are inherited rare disorders treated?', 'What do my blood test results mean?',
    'How do I keep my body healthy?', 'Why does my stomach hurt after eating?',
    'My room seems to spin when I stand up.', 'I cannot catch my breath when walking.',
]
OTHER_ANCHORS = [
    'Who is this actor or famous person?', 'Who won a sports match?',
    'Tell me about a film and its cast.', 'Who leads the government?',
    'Explain a JavaScript software framework.', 'How do I program a computer?',
    'What is the capital city of a country?', 'How much does this stock cost?',
    'Write a song or a poem.', 'How do I repair a car engine?',
    'How do I cook a cake?', 'What is the weather forecast?',
]
MEDICAL = re.compile(r'\b(symptoms?|diseases?|syndromes?|disorders?|diagnos\w*|treatments?|medicin\w*|medications?|vaccin\w*|infections?|blood|pain|headaches?|migraine|dizz\w*|asthma|diabet\w*|amyloidosis|cancer|paracetamol|acetaminophen|side effects?|healthcare|medical|health|pregnan\w*|fever|cough|nausea|breath\w*|urination|fatigue|thirst|heartburn|allerg\w*|insulin|tuberculosis|seizures?|numbness|vomit\w*|diarrh\w*)\b', re.I)
OTHER = re.compile(r'\b(who (?:is|was|won)|prime minister|president of|cricket|football|movie|film|actor|actress|javascript|react js|programming|software|election|stock market|capital of|weather forecast|car engine|recipe)\b', re.I)
OTHER_CONTEXT = re.compile(r'\b(baseball|hard (?:drive|disk)|python decorators?|bicycle (?:tyre|tire)|laptop|holiday|travel itinerary|algorithm|(?:video|computer) games?)\b', re.I)
NATIVE_MEDICAL = re.compile(r'मधुमेह|लक्षण|बीमारी|रोग|दर्द|चिकित्सा|दवा|बुखार|सिरदर्द|स्वास्थ्य|मधुमेहం|మధుమేహ|లక్షణ|వ్యాధి|నొప్పి|వైద్య|మందు|జ్వరం|తలనొప్పి|ఆరోగ్య|నீரிழிவு|அறிகுறி|நோய்|வலி|மருத்துவ|மருந்து|காய்ச்சல்|தலைவலி|சுகாதார')
NATIVE_OTHER = re.compile(r'कौन|क्रिकेट|फिल्म|प्रधानमंत्री|जावास्क्रिप्ट|సినిమా|క్రికెట్|ఎవరు|ప్రధానమంత్రి|திரைப்பட|கிரிக்கெட்|யார்|பிரதமர்')
FACETS = {
    'symptoms': r'symptom|signs?|manifest|feel|experience',
    'causes': r'caus|trigger|risk factor|why|because|due to|inherited|genetic',
    'diagnosis': r'diagnos|test|detect|screen',
    'treatment': r'treat|therap|manage|cure|medicine|medication',
    'side_effects': r'side effect|adverse|reaction|complication',
    'prevention': r'prevent|avoid|protect|reduce.*risk',
}
GENERIC = set('a an the and or but of to for from in on at by with without as it its be been being am was were has had he she they them their his her we our us these those which when where who what how why are does did do can could would should tell about person people someone this that have having feel feeling frequent persistent common cause causes symptom symptoms treatment treatments disease diseases medical health healthcare condition information effects effect side signs diagnosis diagnosed test tests prevent prevention mean means is are were you your my me i please serious safe dangerous normal harmful okay bad'.split())
ALIASES = {'dizzy': 'dizziness', 'headaches': 'headache', 'migraines': 'migraine', 'diabetic': 'diabetes', 'tb': 'tuberculosis', 'acetaminophen': 'paracetamol'}


def tokens(text):
    return {ALIASES.get(word, word) for word in re.findall(r'[a-z][a-z0-9-]*', text.lower()) if len(word) > 2 and word not in GENERIC}


def cosine(a, b):
    import numpy as np
    return float(np.dot(a, b) / max(float(np.linalg.norm(a) * np.linalg.norm(b)), 1e-12))


class ValidationAbstention(Exception):
    def __init__(self, status, reason, evidence=None, candidate=None):
        self.status, self.reason = status, reason
        self.evidence, self.candidate = evidence or {}, candidate


class MedicalValidator:
    def __init__(self, pipeline, policy=None):
        self.pipeline = pipeline
        self.policy = policy if policy is not None else self._read_policy()
        # A corpus-derived terminology check preserves rare disease names rather
        # than limiting acceptance to a fixed list of common health keywords.
        self.entities = set()
        for title in pipeline.documents['question']:
            match = re.match(r'what is (?:\(are\) )?(.+?)\s*\??$', str(title), re.I)
            if match:
                entity = re.sub(r'[^a-z0-9 -]', '', match.group(1).lower()).strip()
                if len(entity) >= 4:
                    self.entities.add(entity)

    def _read_policy(self):
        try:
            policy = json.loads(POLICY_PATH.read_text(encoding='utf-8'))
            if policy['embedding_model'] != self.pipeline.config['models']['embedding_model']:
                return {}
            dataset = resolve_project_path(self.pipeline.config['paths']['dataset'])
            if policy.get('dataset_sha256') != hashlib.sha256(dataset.read_bytes()).hexdigest():
                return {}
            return policy
        except (OSError, ValueError, KeyError):
            return {}

    def encode(self, texts):
        from backend.services.cache import EncoderCache
        retriever = self.pipeline._retriever('semantic')
        encoder = retriever._encoder()
        if not isinstance(encoder, EncoderCache):
            retriever.encoder = EncoderCache(encoder)
        return retriever.encoder.encode(texts)

    def native_intent(self, query):
        if NATIVE_OTHER.search(query) and not NATIVE_MEDICAL.search(query):
            return {'decision': 'out_of_scope', 'reason': 'non_medical_context'}
        return None

    def intent(self, english_query, *, observed_margin=None):
        query = normalize_text(english_query).lower()
        medical = bool(MEDICAL.search(query))
        nonmedical = bool(OTHER.search(query) or OTHER_CONTEXT.search(query))
        if nonmedical and not medical:
            return {'decision': 'out_of_scope', 'reason': 'non_medical_context'}
        if medical:
            return {'decision': 'medical', 'reason': 'explicit_health_intent'}
        if re.search(r'\b(?:als|hiv|copd|mri|ecg)\b', query):
            return {'decision': 'medical', 'reason': 'medical_acronym_with_no_conflicting_context'}
        plain = re.sub(r'[^a-z0-9 -]', '', query)
        words = plain.split()
        # Query n-gram membership avoids compiling thousands of corpus entity
        # regular expressions on every request.
        if any(' '.join(words[start:end]) in self.entities for start in range(len(words))
               for end in range(start + 1, min(len(words), start + 12) + 1)):
            return {'decision': 'medical', 'reason': 'corpus_medical_terminology'}
        # Bare acronyms and referential fragments require context. In particular
        # AL alone is not evidence for AL amyloidosis.
        if len(tokens(query)) == 0 or re.fullmatch(r'(?:what is |tell me about )?[a-z]{1,3}\??', query):
            return {'decision': 'clarification_needed', 'reason': 'ambiguous_question'}
        settings = self.policy.get('intent')
        if not settings:
            return {'decision': 'clarification_needed', 'reason': 'validation_unavailable'}
        if observed_margin is None:
            vectors = self.encode([english_query, *MEDICAL_ANCHORS, *OTHER_ANCHORS])
            positive = max(cosine(vectors[0], v) for v in vectors[1:1 + len(MEDICAL_ANCHORS)])
            negative = max(cosine(vectors[0], v) for v in vectors[1 + len(MEDICAL_ANCHORS):])
            margin = positive - negative
            evidence = {'medical_anchor_similarity': positive, 'other_anchor_similarity': negative, 'intent_margin': margin}
        else:
            # Offline report replay of an already measured, fingerprint-checked
            # score. Production callers always compute their own embeddings.
            margin = float(observed_margin)
            evidence = {'intent_margin': margin}
        if margin >= settings['medical_margin']:
            return {'decision': 'medical', 'reason': 'contrastive_health_intent', **evidence}
        if margin <= settings['outside_margin']:
            return {'decision': 'out_of_scope', 'reason': 'contrastive_non_medical_intent', **evidence}
        return {'decision': 'clarification_needed', 'reason': 'ambiguous_question', **evidence}

    def lexical_features(self, english_query, candidate):
        from src.qa.answer_simplifier import simplify_answer
        title = str(candidate.get('question', ''))
        # Validate the same conservative excerpt that the pipeline will show,
        # rather than relying on evidence beyond its truncation boundary.
        answer = simplify_answer(str(candidate.get('answer', '')),
                                 self.pipeline.config['application']['max_answer_characters'])
        query_topics = tokens(english_query)
        document_topics = tokens(title + ' ' + answer)
        matched = sorted(query_topics & document_topics)
        coverage = len(matched) / len(query_topics) if query_topics else 0.0
        requested = [name for name, pattern in FACETS.items() if re.search(pattern, english_query, re.I)]
        # A FAQ can answer a facet in its answer even when its title is generic.
        missing = [name for name in requested if not re.search(FACETS[name], title + ' ' + answer, re.I)]
        return {'topic_coverage': coverage,
                'matched_topics': matched, 'missing_facets': missing, 'requested_facets': requested}

    def features(self, english_query, candidate):
        vectors = self.encode([english_query, str(candidate.get('question', ''))])
        return {'question_similarity': cosine(vectors[0], vectors[1]), **self.lexical_features(english_query, candidate)}

    def relevance(self, english_query, candidate, route):
        evidence = self.features(english_query, candidate)
        policy = self.policy.get('routes', {}).get(route)
        if not policy:
            return False, 'validation_unavailable', evidence
        enough = (evidence['topic_coverage'] >= policy['topic_coverage'] and not evidence['missing_facets']
                  and evidence['question_similarity'] >= policy['question_similarity'])
        return enough, 'matching_evidence' if enough else 'weak_retrieval_evidence', evidence
