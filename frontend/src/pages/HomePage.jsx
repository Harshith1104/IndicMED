import { useEffect, useState } from 'react';
import { ArrowRight, BookOpen, LoaderCircle, SearchX, ShieldCheck } from 'lucide-react';
import { getOptions } from '../services/api';
import { useAsk } from '../hooks/useAsk';
import AnswerCard from '../components/AnswerCard';
import InformationPanel from '../components/InformationPanel';
import Notice from '../components/Notice';
import SearchForm from '../components/SearchForm';
import ValidationCard from '../components/ValidationCard';
import ComparisonView from '../components/ComparisonView';

export default function HomePage() {
  const [options, setOptions] = useState(null);
  const [optionsError, setOptionsError] = useState(null);
  const [attempt, setAttempt] = useState(0);
  const [values, setValues] = useState(null);
  const [validation, setValidation] = useState('');
  const search = useAsk();

  useEffect(() => {
    const controller = new AbortController();
    setOptionsError(null);
    getOptions(controller.signal).then(data => {
      if (controller.signal.aborted) return;
      setOptions(data);
      setValues({ ...data.defaults, query: '' });
    }).catch(error => { if (!controller.signal.aborted) setOptionsError(error.message); });
    return () => controller.abort();
  }, [attempt]);

  function change(field, value) {
    search.reset(); // Invalidate the answer immediately when any input changes.
    setValidation('');
    setValues(current => ({ ...current, [field]: value }));
  }

  function submit(event, mode = 'ask') {
    event.preventDefault();
    if (!values.query.trim()) { setValidation('Please enter a health question.'); return; }
    if (mode === 'ask' && values.multilingual_strategy === 'direct' && values.retrieval_method !== 'semantic') {
      setValidation('Direct multilingual retrieval requires Semantic.'); return;
    }
    setValidation('');
    search.ask(values, mode);
  }

  return <main id="main" className="main-container">
    <section className="hero" aria-labelledby="hero-title"><span className="hero-badge"><ShieldCheck size={14} /> SOURCE-GROUNDED HEALTH INFORMATION</span>
      <h1 id="hero-title">Health information,<br /><span>in your language.</span></h1>
      <p>Find answers to your health questions in English, Hindi, Telugu and Tamil.<br className="desktop-break" /> Grounded in medical FAQs. Connected to their sources.</p>
    </section>
    <div className="workspace"><div className="primary-column">
      {options && values ? <SearchForm values={values} options={options} onChange={change} onSubmit={submit}
        onCompare={event => submit(event, 'compare')} loading={search.status === 'loading'} validation={validation} />
        : optionsError ? <div className="connection-card"><Notice error>{optionsError}</Notice>
          <button type="button" className="secondary-button" onClick={() => setAttempt(x => x + 1)}>Reconnect to backend <ArrowRight size={16} /></button></div>
          : <div className="connection-card" role="status"><LoaderCircle size={23} className="spin" /> Connecting to IndicMed…</div>}
      <div aria-live="polite" aria-atomic="false" aria-busy={search.status === 'loading'} className="results-region">
        {search.status === 'loading' && <div className="loading-card" role="status"><div className="loading-icon"><LoaderCircle size={25} className="spin" /></div>
          <h2>{search.mode === 'compare' ? 'Comparing both strategies' : 'Finding your answer'}</h2><p>Checking medical scope and retrieved evidence, then translating supported answers.</p>
          <span>The first request may take a few minutes while models load.</span></div>}
        {search.status === 'error' && <Notice error>{search.error.message}</Notice>}
        {search.status === 'empty' && <div className="empty-card"><SearchX size={27} /><h2>No matching FAQ found</h2><p>Try a clearer question or a different retrieval method.</p></div>}
        {search.status === 'success' && <AnswerCard result={search.result} />}
        {search.status === 'decision' && <ValidationCard result={search.result} onExample={query => change('query', query)} />}
      </div>
    </div><InformationPanel /></div>
    {search.status === 'comparison' && <ComparisonView result={search.result} />}
    <div className="medical-disclaimer"><ShieldCheck size={21} aria-hidden="true" /><p><strong>Information to support understanding.</strong> IndicMed provides general health information retrieved from medical information sources and is not a substitute for professional medical advice, diagnosis, or treatment.</p></div>
    <footer><span>IndicMed<span className="footer-dot">.</span> <span className="footer-separator">/</span> Language connects. Knowledge empowers.</span>
      <span className="inline"><BookOpen size={14} /> Retrieval-grounded · MedQuAD</span></footer>
  </main>;
}
