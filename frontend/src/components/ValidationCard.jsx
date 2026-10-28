import { ShieldCheck, Info } from 'lucide-react';
import { safeSourceUrl } from './AnswerCard';

const MESSAGES = {
  en: {
    out_of_scope: ["This question is outside IndicMed's medical scope.", 'IndicMed is designed to help with health and medical information. Try asking about a disease, symptom, medicine, or general healthcare topic.'],
    insufficient_evidence: ["We couldn't find sufficiently relevant medical information.", 'Try rephrasing your question or using more specific medical terms.'],
    clarification_needed: ['We need more context to answer safely.', 'Please describe the health topic or symptom more specifically. If translation or validation is unavailable, try again after the backend setup is restored.'],
    validation_unavailable: ['A required resource is temporarily unavailable.', 'Translation, retrieval, or medical validation could not be completed. No medical answer is displayed. Check the backend setup or try again later.'],
    examples: ['What is asthma?', 'What are the symptoms of diabetes?'], label: 'Try a health question',
  },
  hi: {
    out_of_scope: ['यह प्रश्न IndicMed के चिकित्सा दायरे से बाहर है।', 'IndicMed स्वास्थ्य और चिकित्सा जानकारी के लिए है। किसी बीमारी, लक्षण, दवा या स्वास्थ्य विषय के बारे में पूछें।'],
    insufficient_evidence: ['हमें पर्याप्त प्रासंगिक चिकित्सा जानकारी नहीं मिली।', 'प्रश्न को दोबारा लिखें या अधिक स्पष्ट चिकित्सा शब्दों का उपयोग करें।'],
    clarification_needed: ['हमें आपके प्रश्न के बारे में अधिक जानकारी चाहिए।', 'स्वास्थ्य विषय या लक्षण को स्पष्ट करें। अनुवाद या सत्यापन उपलब्ध न हो तो बाद में दोबारा प्रयास करें।'],
    validation_unavailable: ['एक आवश्यक संसाधन अभी उपलब्ध नहीं है।', 'अनुवाद, खोज या चिकित्सा सत्यापन पूरा नहीं हो सका। कोई चिकित्सा उत्तर नहीं दिखाया गया है। बाद में फिर प्रयास करें।'],
    examples: ['अस्थमा क्या है?', 'मधुमेह के लक्षण क्या हैं?'], label: 'स्वास्थ्य संबंधी प्रश्न पूछें',
  },
  te: {
    out_of_scope: ['ఈ ప్రశ్న IndicMed వైద్య పరిధికి వెలుపల ఉంది.', 'IndicMed ఆరోగ్యం మరియు వైద్య సమాచారం కోసం రూపొందించబడింది. వ్యాధి, లక్షణం, మందు లేదా ఆరోగ్య విషయం గురించి అడగండి.'],
    insufficient_evidence: ['తగిన సంబంధిత వైద్య సమాచారం కనుగొనలేకపోయాము.', 'ప్రశ్నను మరో విధంగా అడగండి లేదా మరింత స్పష్టమైన వైద్య పదాలను ఉపయోగించండి.'],
    clarification_needed: ['మీ ప్రశ్నకు మరింత వివరణ అవసరం.', 'ఆరోగ్య విషయం లేదా లక్షణాన్ని స్పష్టంగా వివరించండి. అనువాదం లేదా ధృవీకరణ అందుబాటులో లేకపోతే తరువాత ప్రయత్నించండి.'],
    validation_unavailable: ['అవసరమైన వనరు ప్రస్తుతం అందుబాటులో లేదు.', 'అనువాదం, శోధన లేదా వైద్య ధృవీకరణ పూర్తి కాలేదు. వైద్య సమాధానం చూపించబడలేదు. తరువాత మళ్లీ ప్రయత్నించండి.'],
    examples: ['ఆస్తమా అంటే ఏమిటి?', 'మధుమేహం లక్షణాలు ఏమిటి?'], label: 'ఆరోగ్య ప్రశ్నను ప్రయత్నించండి',
  },
  ta: {
    out_of_scope: ['இந்தக் கேள்வி IndicMed மருத்துவ வரம்பிற்கு வெளியே உள்ளது.', 'IndicMed உடல்நலம் மற்றும் மருத்துவத் தகவல்களுக்கானது. நோய், அறிகுறி, மருந்து அல்லது சுகாதாரத் தலைப்பு பற்றிக் கேளுங்கள்.'],
    insufficient_evidence: ['போதுமான தொடர்புடைய மருத்துவத் தகவல்கள் கிடைக்கவில்லை.', 'கேள்வியை மாற்றிக் கேளுங்கள் அல்லது மேலும் குறிப்பான மருத்துவச் சொற்களைப் பயன்படுத்துங்கள்.'],
    clarification_needed: ['உங்கள் கேள்விக்கு மேலும் விளக்கம் தேவை.', 'உடல்நலத் தலைப்பு அல்லது அறிகுறியைத் தெளிவாக விவரிக்கவும். மொழிபெயர்ப்பு அல்லது சரிபார்ப்பு கிடைக்காவிட்டால் பின்னர் முயற்சிக்கவும்.'],
    validation_unavailable: ['தேவையான ஒரு வசதி தற்போது கிடைக்கவில்லை.', 'மொழிபெயர்ப்பு, தேடல் அல்லது மருத்துவச் சரிபார்ப்பு முடியவில்லை. மருத்துவப் பதில் காட்டப்படவில்லை. பின்னர் மீண்டும் முயற்சிக்கவும்.'],
    examples: ['ஆஸ்துமா என்றால் என்ன?', 'நீரிழிவு நோயின் அறிகுறிகள் என்ன?'], label: 'உடல்நலக் கேள்வியை முயற்சிக்கவும்',
  },
};

export default function ValidationCard({ result, onExample, diagnostic = false }) {
  const language = result.selected_language || 'en';
  const copy = MESSAGES[language] || MESSAGES.en;
  const key = ['validation_unavailable', 'strategy_unavailable'].includes(result.reason) ? 'validation_unavailable' : result.status;
  const [title, description] = copy[key] || copy.clarification_needed;
  const candidateUrl = safeSourceUrl(result.candidate?.source_url);
  return <section className="validation-card" role="status" lang={language}>
    <span className="validation-icon"><ShieldCheck size={26} /></span>
    <h2>{title}</h2><p>{description}</p>
    <span className="validation-status">{result.status.replaceAll('_', ' ')}</span>
    {onExample && <div className="validation-examples"><h3>{copy.label}</h3>{copy.examples.map(query =>
      <button type="button" className="example-card" key={query} onClick={() => onExample(query)}>{query}</button>)}</div>}
    {diagnostic && result.candidate && <details className="candidate-details"><summary><Info size={17} /> Rejected candidate · inspection only</summary>
      <p>No medical answer is displayed because the evidence check did not pass.</p>
      <dl><dt>Retrieved FAQ</dt><dd>{result.candidate.question}</dd>
        <dt>Question sent to retriever</dt><dd>{result.candidate.retrieval_query}</dd>
        <dt>Source</dt><dd>{candidateUrl ? <a href={candidateUrl} target="_blank" rel="noopener noreferrer">{result.candidate.source || 'View source'}</a> : result.candidate.source || 'Not supplied'}</dd>
        <dt>Document ID</dt><dd>{result.candidate.id}</dd>
        <dt>RETRIEVAL SIMILARITY SCORE</dt><dd>{Number.isFinite(result.candidate.similarity_score) ? result.candidate.similarity_score.toFixed(3) : 'Unavailable'}</dd>
      </dl><p>Similarity measures how closely the retrieved document matches your question. It does not represent medical accuracy or clinical confidence.</p></details>}
  </section>;
}
