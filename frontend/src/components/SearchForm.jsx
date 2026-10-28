import { ArrowUpRight, Search, Languages, LoaderCircle, Columns2 } from 'lucide-react';
import RetrievalSettings from './RetrievalSettings';

const EXAMPLES = [
  { language: 'en', label: 'English', query: 'What is asthma?' },
  { language: 'hi', label: 'हिन्दी', query: 'मधुमेह के लक्षण क्या हैं?' },
  { language: 'te', label: 'తెలుగు', query: 'మైగ్రేన్‌కు కారణాలు ఏమిటి?' },
  { language: 'ta', label: 'தமிழ்', query: 'காசநோய் எவ்வாறு கண்டறியப்படுகிறது?' },
];

export default function SearchForm({ values, options, onChange, onSubmit, onCompare, loading, validation }) {
  const examples = values.language === 'auto' ? EXAMPLES : EXAMPLES.filter(x => x.language === values.language);
  return <section aria-labelledby="search-title" className="search-section">
    <form onSubmit={onSubmit} noValidate className="search-card">
      <div className="card-heading"><span className="section-icon"><Search size={19} /></span>
        <div><h2 id="search-title">Ask a health question</h2><p>Start with what you’d like to understand.</p></div></div>
      <label className="sr-only" htmlFor="question">Your health question</label>
      <textarea id="question" placeholder="For example, what are the symptoms of diabetes?"
        value={values.query} maxLength={4000} rows={4} aria-invalid={Boolean(validation)}
        aria-describedby={validation ? 'question-error' : 'question-hint'}
        onChange={e => onChange('query', e.target.value)} />
      <div className="input-meta"><span id="question-hint">Ask in English, हिन्दी, తెలుగు or தமிழ்</span><span>{values.query.length}/4000</span></div>
      {validation && <p id="question-error" className="validation-error" role="alert">{validation}</p>}
      <div className="search-actions">
        <div className="language-field"><Languages size={17} aria-hidden="true" />
          <label className="sr-only" htmlFor="language">Question language</label>
          <select id="language" value={values.language} onChange={e => onChange('language', e.target.value)}>
            {options.languages.map(x => <option key={x.value} value={x.value}>{x.label}</option>)}
          </select></div>
        <button className="primary-button" disabled={loading} type="submit">
          {loading ? <><LoaderCircle size={18} className="spin" /> Searching…</> : <><Search size={17} /> Ask IndicMed <ArrowUpRight size={17} /></>}
        </button>
      </div>
      <RetrievalSettings values={values} options={options} onChange={onChange} />
      <div className="compare-action"><button type="button" className="secondary-button" onClick={onCompare} disabled={loading}>
        <Columns2 size={19} /> Compare Strategies</button>
        <p>Both paths use Semantic and the same result count. Your Ask settings stay unchanged.</p></div>
    </form>
    <div className="examples"><div className="eyebrow muted">A PLACE TO START</div>
      <div className="example-grid">{examples.map(x => <button type="button" key={x.language} className="example-card"
        onClick={() => onChange('query', x.query)}><span className="example-top"><span lang={x.language}>{x.label}</span><ArrowUpRight size={15} /></span>
        <span lang={x.language}>{x.query}</span></button>)}</div>
    </div>
  </section>;
}
