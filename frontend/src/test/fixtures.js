export const options = {
  languages: [{ value: 'auto', label: 'Auto detect' }, { value: 'en', label: 'English' },
    { value: 'hi', label: 'Hindi' }, { value: 'te', label: 'Telugu' }, { value: 'ta', label: 'Tamil' }],
  retrieval_methods: [{ value: 'tfidf', label: 'TF-IDF' }, { value: 'bm25', label: 'BM25' }, { value: 'semantic', label: 'Semantic' }],
  multilingual_strategies: [{ value: 'translate', label: 'Translate-then-retrieve' }, { value: 'direct', label: 'Direct multilingual retrieval' }],
  defaults: { language: 'auto', retrieval_method: 'semantic', multilingual_strategy: 'translate', top_k: 3 },
  top_k_min: 1, top_k_max: 5,
};

// Test fixture only; never imported into the application.
export const answer = {
  query: 'What is asthma?', detected_language: 'en', selected_language: 'en', english_query: 'What is asthma?',
  answer: 'A grounded test answer.', translated_answer: 'A grounded test answer.',
  retrieval_strategy: 'semantic', category: 'Asthma', source: 'Test source',
  source_url: 'https://example.test/source', similarity_score: 0.7342,
  related_questions: ['What causes asthma?'], document_id: 'test-document', translation_warning: null,
};
