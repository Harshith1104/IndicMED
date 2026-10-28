import { ArrowDown, BookOpen, Languages, Search, ShieldCheck } from 'lucide-react';

export default function InformationPanel() {
  return <aside className="information-panel" aria-label="How IndicMed works">
    <div className="panel-illustration" aria-hidden="true"><span className="illustration-ring ring-one" /><span className="illustration-ring ring-two" />
      <span className="illustration-center"><BookOpen size={29} strokeWidth={1.6} /></span>
      <span className="script-token token-hi">अ</span><span className="script-token token-te">అ</span><span className="script-token token-ta">அ</span>
      <span className="illustration-spark">+</span></div>
    <div className="eyebrow">LANGUAGE SHOULD BE A BRIDGE</div>
    <h2>A clearer path to<br />health information.</h2>
    <p>Explore medical FAQs in the language you’re comfortable with, with the source always in view.</p>
    <ol className="workflow">
      <li><span className="workflow-icon"><Languages size={18} /></span><div><h3>Ask in your language</h3><p>Choose a language or let us detect it.</p></div></li>
      <li className="workflow-connector" aria-hidden="true"><ArrowDown size={13} /></li>
      <li><span className="workflow-icon"><Search size={18} /></span><div><h3>Find a grounded answer</h3><p>Retrieve a matching English MedQuAD FAQ.</p></div></li>
      <li className="workflow-connector" aria-hidden="true"><ArrowDown size={13} /></li>
      <li><span className="workflow-icon"><BookOpen size={18} /></span><div><h3>Understand the evidence</h3><p>Read the answer, translation and source.</p></div></li>
    </ol>
    <div className="source-note"><ShieldCheck size={21} /><div><strong>Built on MedQuAD</strong><p>Source-linked medical FAQs. Retrieval-grounded answers.</p></div></div>
  </aside>;
}
