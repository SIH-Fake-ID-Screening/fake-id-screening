import { NavLink, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard, ScanLine, History, Settings, Shield,
  LogOut, FileSearch, ChevronRight
} from 'lucide-react';
import { MOCK_OFFICER } from '../../data/mockData';

const NAV_ITEMS = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/dashboard' },
  { label: 'New Screening', icon: ScanLine, to: '/screening/new' },
  { label: 'Screening History', icon: History, to: '/screening/history' },
  { label: 'Settings', icon: Settings, to: '/settings' },
];

export default function Sidebar() {
  const navigate = useNavigate();
  const initials = MOCK_OFFICER.name.split(' ').map(n => n[0]).join('');

  return (
    <aside className="sidebar">
      {/* Logo */}
      <div className="sidebar-logo">
        <div className="logo-icon">
          <Shield size={18} color="white" />
        </div>
        <div className="logo-text">
          SIH-Verify
          <div className="logo-sub">ID Screening System</div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        <div className="nav-section-label">Navigation</div>
        {NAV_ITEMS.map(({ label, icon: Icon, to }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}
          >
            <Icon className="nav-icon" />
            <span>{label}</span>
          </NavLink>
        ))}

        <div className="nav-section-label" style={{ marginTop: 12 }}>Quick Actions</div>
        <button
          className="nav-item"
          style={{ border: 'none', background: 'none', width: '100%', textAlign: 'left', cursor: 'pointer' }}
          onClick={() => navigate('/screening/new')}
        >
          <FileSearch className="nav-icon" />
          <span>Start Screening</span>
          <ChevronRight size={13} style={{ marginLeft: 'auto', opacity: 0.4 }} />
        </button>
      </nav>

      {/* Footer */}
      <div className="sidebar-footer">
        <div className="officer-card">
          <div className="officer-avatar">{initials}</div>
          <div className="officer-info">
            <div className="officer-name">{MOCK_OFFICER.name}</div>
            <div className="officer-badge">{MOCK_OFFICER.badge}</div>
          </div>
          <button
            onClick={() => navigate('/login')}
            style={{ background: 'none', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 4 }}
            title="Logout"
          >
            <LogOut size={14} />
          </button>
        </div>
      </div>
    </aside>
  );
}
