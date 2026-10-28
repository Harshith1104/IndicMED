import { AlertCircle, Info } from 'lucide-react';

export default function Notice({ children, warning = false, error = false }) {
  const Icon = warning || error ? AlertCircle : Info;
  return <div className={`notice ${error ? 'notice-error' : warning ? 'notice-warning' : ''}`}
    role={error ? 'alert' : 'status'}><Icon size={19} aria-hidden="true" /><div>{children}</div></div>;
}
