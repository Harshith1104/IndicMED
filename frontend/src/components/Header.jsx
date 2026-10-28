import { HeartPulse, Moon, Sun } from 'lucide-react';
import { useTheme } from '../hooks/useTheme';

export default function Header() {
  const [theme, toggleTheme] = useTheme();
  return <header className="site-header">
    <div className="header-inner">
      <a href="#main" className="brand" aria-label="IndicMed home">
        <span className="brand-mark"><HeartPulse size={26} aria-hidden="true" /></span>
        <span><span className="brand-name">Indic<span>Med</span><span className="brand-dot">.</span></span>
          <span className="brand-subtitle">Multilingual Health Information Retrieval</span></span>
      </a>
      <div className="header-actions"><span className="header-note">One knowledge base. Four languages.</span>
        <button type="button" className="icon-button" onClick={toggleTheme}
          aria-label={`Switch to ${theme === 'light' ? 'dark' : 'light'} mode`}>
          {theme === 'light' ? <Moon size={19} /> : <Sun size={19} />}
        </button>
      </div>
    </div>
  </header>;
}
