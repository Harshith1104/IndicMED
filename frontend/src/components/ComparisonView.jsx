import AnswerCard from './AnswerCard';
import ValidationCard from './ValidationCard';

export default function ComparisonView({ result }) {
  return <section className="comparison-view" aria-labelledby="comparison-title">
    <p className="sr-only" role="status">Comparison complete. Review both strategy results.</p>
    <div className="comparison-intro"><div><span className="eyebrow">ONE QUESTION · TWO QUERY PATHS</span><h2 id="comparison-title">Compare retrieval strategies</h2></div>
      <span className="result-tags"><span>Semantic · top {result.top_k}</span></span></div>
    <p className="comparison-explanation">{result.equivalent
      ? 'English questions use the same query in both paths. IndicMed ran retrieval once and reused that result.'
      : 'Direct and Translate use different query representations. Their similarity scores may not be directly comparable and do not identify a medically more accurate answer.'}</p>
    <div className="comparison-grid">{['direct', 'translate'].map(strategy => {
      const branch = result[strategy];
      return <article className={`comparison-column ${strategy === 'translate' ? 'default-strategy' : ''}`} key={strategy} aria-label={strategy === 'direct' ? 'Direct Multilingual Retrieval' : 'Translate-then-Retrieve'}>
        <div className="comparison-heading"><h3>{strategy === 'direct' ? 'Direct Multilingual Retrieval' : 'Translate-then-Retrieve'}</h3>
          {strategy === 'translate' && <span className="default-badge">Application default</span>}</div>
        <p className="query-path">{result.equivalent ? 'English query → MiniLM → English FAQs (shared inference)' : strategy === 'direct' ? 'Original question → MiniLM → English FAQs' : 'Question → IndicTrans2 English → MiniLM → English FAQs'}</p>
        <div className="retriever-query"><span>QUESTION SENT TO RETRIEVER</span><p>{branch.retrieval_query || branch.candidate?.retrieval_query || 'Retrieval did not complete or was withheld by the intent check.'}</p></div>
        {branch.status === 'success' ? <><span className="validation-status accepted">Evidence check passed · not clinical validation</span><AnswerCard result={branch} titleId={`${strategy}-answer-title`} /></>
          : <ValidationCard result={branch} diagnostic />}
      </article>;
    })}</div>
    <details className="evaluation-note"><summary>Previously recorded evaluation-set Recall@1</summary>
      <p>200 underlying questions represented in four languages. These are recorded benchmark results, not a score for this live question.</p>
      <table><thead><tr><th>Language</th><th>Direct</th><th>Translate</th></tr></thead>
        <tbody><tr><th>Hindi</th><td>11.5%</td><td>39.5%</td></tr><tr><th>Telugu</th><td>1.5%</td><td>38.0%</td></tr><tr><th>Tamil</th><td>0.5%</td><td>32.0%</td></tr></tbody></table>
    </details>
  </section>;
}
