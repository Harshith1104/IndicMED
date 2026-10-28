import { SlidersHorizontal, ChevronDown } from 'lucide-react';

export default function RetrievalSettings({ values, options, onChange }) {
  const direct = values.multilingual_strategy === 'direct';
  return <details className="settings">
    <summary><span className="inline"><SlidersHorizontal size={16} /> Advanced retrieval settings</span>
      <span className="settings-summary">{options.retrieval_methods.find(x => x.value === values.retrieval_method)?.label}
        <span className="summary-divider">·</span>{values.top_k} results <ChevronDown size={15} className="chevron" /></span></summary>
    <div className="settings-body">
      <div className="settings-grid">
        <label htmlFor="retrieval-method">Retrieval method<select id="retrieval-method" value={values.retrieval_method}
          onChange={e => onChange('retrieval_method', e.target.value)}>
          {options.retrieval_methods.map(x => <option key={x.value} value={x.value} disabled={direct && x.value !== 'semantic'}>{x.label}</option>)}
        </select></label>
        <label htmlFor="strategy">Multilingual strategy<select id="strategy" value={values.multilingual_strategy}
          onChange={e => onChange('multilingual_strategy', e.target.value)}>
          {options.multilingual_strategies.map(x => <option key={x.value} value={x.value}
            disabled={x.value === 'direct' && values.retrieval_method !== 'semantic'}>{x.label}</option>)}
        </select></label>
      </div>
      <div className="range-row"><label htmlFor="top-k">Retrieved results <strong>{values.top_k}</strong></label>
        <input id="top-k" type="range" min={options.top_k_min} max={options.top_k_max} step="1"
          value={values.top_k} onChange={e => onChange('top_k', Number(e.target.value))} /></div>
      <p className="field-hint">Direct multilingual retrieval requires Semantic. To use TF-IDF or BM25, choose translate-then-retrieve first. English questions skip translation in either strategy.</p>
    </div>
  </details>;
}
