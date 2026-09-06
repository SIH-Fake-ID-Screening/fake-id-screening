import { useLocation } from 'react-router-dom';
import { Bell, RefreshCw, ChevronRight } from 'lucide-react';

const ROUTE_LABELS = {
  '/dashboard': 'Dashboard',
  '/screening/new': 'New Screening',
  '/screening/history': 'Screening History',
  '/settings': 'Settings',
};

function getLabel(pathname) {
  if (pathname.startsWith('/screening/result/')) return 'Screening Result';
  if (pathname.startsWith('/screening/details/')) return 'Screening Details';
  return ROUTE_LABELS[pathname] || 'Dashboard';
}

export default function TopBar() {
  const { pathname } = useLocation();
  const label = getLabel(pathname);
  const now = new Date();
  const timeStr = now.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' });
  const dateStr = now.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });

  return (
    <header className="topbar">
      <div className="topbar-left">
        <div className="breadcrumb">
          <span>SIH-Verify</span>
          <ChevronRight size={13} />
          <span className="breadcrumb-current">{label}</span>
        </div>
      </div>

      <div className="topbar-right">
        <div className="system-status">
          <div className="status-dot" />
          <span>System Online</span>
        </div>

        <span style={{ fontSize: 12, color: 'var(--text-muted)', fontFamily: 'JetBrains Mono, monospace' }}>
          {dateStr} · {timeStr}
        </span>

        <button className="topbar-btn" title="Refresh">
          <RefreshCw size={15} />
        </button>

        <button className="topbar-btn" title="Notifications">
          <Bell size={15} />
        </button>
      </div>
    </header>
  );
}
