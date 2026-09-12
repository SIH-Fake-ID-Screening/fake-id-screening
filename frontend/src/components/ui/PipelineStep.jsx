import {
  Upload, ScanLine, Database, UserCheck, ShieldAlert, BarChart2, CheckCircle2, Loader2, X
} from 'lucide-react';

const ICONS = { Upload, ScanLine, Database, UserCheck, ShieldAlert, BarChart2, CheckCircle2 };

// state: 'idle' | 'done' | 'active' | 'error' | 'success'
export default function PipelineStep({ label, state = 'idle', isLast = false }) {
  const Icon = state === 'active' ? Loader2 :
               state === 'done' || state === 'success' ? CheckCircle2 :
               state === 'error' ? X : ICONS.CheckCircle2;

  return (
    <div className={`pipeline-step ${state}${isLast ? ' last' : ''}`}>
      <div className="pipeline-circle">
        <Icon size={16} />
      </div>
      <div className="pipeline-label">{label}</div>
    </div>
  );
}
