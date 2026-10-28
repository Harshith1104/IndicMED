import { BookOpen, Check, ChevronDown, ExternalLink, FileText, Languages } from 'lucide-react';
import Notice from './Notice';

const METHODS = { tfidf: 'TF-IDF', bm25: 'BM25', semantic: 'Semantic' };
const LANGUAGES = { en: 'English', hi: 'Hindi', te: 'Telugu', ta: 'Tamil' };

export function safeSourceUrl(value) {
  try {
    const url = new URL(value);
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : null;
  } catch { return null; }
}

export default function AnswerCard({ result, titleId = 'answer-title' }) {
  const sourceUrl = safeSourceUrl(result.source_url);
  const method = result.retrieval_strategy.split('_').at(-1);
  const strategy = result.retrieval_strategy.startsWith('direct_') ? 'Direct multilingual retrieval'
    : result.retrieval_strategy.startsWith('translate_') ? 'Translate-then-retrieve' : 'English retrieval';
  const untranslatedQuery = result.retrieval_strategy === 'direct_semantic';
  const score = Number.isFinite(result.similarity_score) ? result.similarity_score.toFixed(3) : 'Unavailable';
  const readableCategory = result.category && !/[_/\\]/.test(result.category);
  return <section className="answer-card" aria-labelledby={titleId} tabIndex={-1}>
    <div className="answer-heading"><span className="eyebrow"><Check size={15} /> RETRIEVED ANSWER</span>
      <span className="language-badge"><Languages size={14} />{result.translation_warning ? 'English fallback' : LANGUAGES[result.selected_language]}</span></div>
    <h2 id={titleId}>{result.retrieved_question || (readableCategory ? result.category : 'Retrieved health information')}</h2>
    {result.translation_warning && <Notice warning>{result.translation_warning}</Notice>}
    <div className="answer-text" lang={result.translation_warning ? 'en' : result.selected_language}>{result.translated_answer}</div>
    <div className="evidence"><div className="evidence-source"><BookOpen size={19} /><div><span className="evidence-label">INFORMATION SOURCE</span>
      {sourceUrl ? <a href={sourceUrl} target="_blank" rel="noopener noreferrer">{result.source || 'View original source'}<ExternalLink size={14} /><span className="sr-only"> (opens in a new tab)</span></a>
        : <strong>{result.source || 'Source name unavailable'}</strong>}
    </div></div><div className="score"><span className="evidence-label">RETRIEVAL SIMILARITY SCORE</span><strong>{score}</strong></div></div>
    <p className="score-explanation">Similarity measures how closely the retrieved document matches your question. It does not represent medical accuracy or clinical confidence.</p>
    <div className="result-tags"><span>{METHODS[method] || method}</span><span>{strategy}</span></div>
    {result.related_questions?.length > 0 && <div className="related"><h3>Related questions</h3><p>Other retrieved FAQs, shown in their original English.</p><ul>
      {result.related_questions.map((question, index) => <li key={`${index}-${question}`}><FileText size={15} aria-hidden="true" /><span>{question}</span></li>)}
    </ul></div>}
    <details className="technical"><summary><span className="inline"><FileText size={16} /> Technical details</span><ChevronDown size={16} className="chevron" /></summary>
      <dl><dt>Original query</dt><dd>{result.query}</dd>
        <dt>Selected or detected language</dt><dd>{LANGUAGES[result.detected_language]}</dd>
        <dt>English translated query</dt><dd>{untranslatedQuery ? 'Direct retrieval uses the original query; English canonicalization is used only for validation.' : result.english_query}</dd>
        <dt>Grounded English answer</dt><dd lang="en">{result.answer}</dd>
        <dt>Document ID</dt><dd className="document-id">{result.document_id}</dd>
        <dt>Dataset category</dt><dd>{result.category || 'Not supplied'}</dd>
        <dt>RETRIEVAL SIMILARITY SCORE</dt><dd>{score}</dd>
        <dt>Strategy used</dt><dd>{result.retrieval_strategy}</dd></dl>
    </details>
  </section>;
}
