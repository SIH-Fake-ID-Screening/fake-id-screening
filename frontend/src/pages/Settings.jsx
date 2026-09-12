import { useState } from 'react';
import {
  User2, Settings2, Bell, Shield, Key, Save, Eye, EyeOff
} from 'lucide-react';
import { MOCK_OFFICER } from '../data/mockData';

const SECTIONS = [
  { id: 'profile', label: 'Profile', icon: User2 },
  { id: 'preferences', label: 'Preferences', icon: Settings2 },
  { id: 'notifications', label: 'Notifications', icon: Bell },
  { id: 'api', label: 'API Configuration', icon: Settings2 },
  { id: 'security', label: 'Security', icon: Shield },
];

function Toggle({ on, onToggle }) {
  return (
    <button className={`toggle${on ? ' on' : ''}`} onClick={onToggle} type="button" />
  );
}

export default function Settings() {
  const [active, setActive] = useState('profile');
  const [form, setForm] = useState({
    name: MOCK_OFFICER.name,
    email: MOCK_OFFICER.email,
    role: MOCK_OFFICER.role,
    badge: MOCK_OFFICER.badge,
    dept: MOCK_OFFICER.department,
  });
  const [prefs, setPrefs] = useState({
    darkMode: true,
    compactTable: false,
    showRiskColors: true,
    autoRefresh: false,
  });
  const [notifs, setNotifs] = useState({
    rejections: true,
    suspicious: true,
    verified: false,
    systemAlerts: true,
    email: false,
  });
  const [api, setApi] = useState({
    baseUrl: 'http://localhost:8000',
    key: 'sk-sih-•••••••••••••••',
  });
  const [showKey, setShowKey] = useState(false);
  const [pw, setPw] = useState({ current: '', next: '', confirm: '' });
  const [showPw, setShowPw] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = () => {
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  const renderSection = () => {
    switch (active) {
      case 'profile':
        return (
          <div>
            <div className="settings-section-title">Profile Information</div>
            <div className="settings-section-desc">Your identity as displayed across the screening portal</div>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">Full Name</label>
                <input className="form-input" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Official Email</label>
                <input className="form-input" type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </div>
              <div className="form-group">
                <label className="form-label">Role</label>
                <select className="form-input filter-select" value={form.role} onChange={e => setForm(f => ({ ...f, role: e.target.value }))}>
                  <option>Senior Verification Officer</option>
                  <option>Verification Officer</option>
                  <option>Supervisor</option>
                  <option>Administrator</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Badge Number</label>
                <input className="form-input font-mono" value={form.badge} readOnly style={{ fontFamily: 'JetBrains Mono, monospace', opacity: 0.7 }} />
              </div>
              <div className="form-group" style={{ gridColumn: '1 / -1' }}>
                <label className="form-label">Department</label>
                <input className="form-input" value={form.dept} onChange={e => setForm(f => ({ ...f, dept: e.target.value }))} />
              </div>
            </div>

            <div className="divider" />
            <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'linear-gradient(135deg, var(--accent-blue), var(--accent-cyan))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20, fontWeight: 800, color: 'white' }}>
                {form.name.split(' ').map(n => n[0]).join('')}
              </div>
              <div>
                <div style={{ fontSize: 14, fontWeight: 600 }}>{form.name}</div>
                <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>{form.email}</div>
              </div>
            </div>
          </div>
        );

      case 'preferences':
        return (
          <div>
            <div className="settings-section-title">Display Preferences</div>
            <div className="settings-section-desc">Customize how the portal looks and behaves</div>

            {[
              { key: 'darkMode', label: 'Dark Theme', desc: 'Use dark color scheme (recommended for extended use)' },
              { key: 'compactTable', label: 'Compact Tables', desc: 'Reduce row height in screening history tables' },
              { key: 'showRiskColors', label: 'Risk Score Colors', desc: 'Highlight risk scores with green/amber/red colors' },
              { key: 'autoRefresh', label: 'Auto-Refresh Dashboard', desc: 'Automatically refresh dashboard statistics every 60 seconds' },
            ].map(({ key, label, desc }) => (
              <div className="toggle-wrap" key={key}>
                <div>
                  <div className="toggle-label">{label}</div>
                  <div className="toggle-desc">{desc}</div>
                </div>
                <Toggle on={prefs[key]} onToggle={() => setPrefs(p => ({ ...p, [key]: !p[key] }))} />
              </div>
            ))}
          </div>
        );

      case 'notifications':
        return (
          <div>
            <div className="settings-section-title">Notification Settings</div>
            <div className="settings-section-desc">Choose which events trigger alerts in the portal</div>

            {[
              { key: 'rejections', label: 'Rejection Alerts', desc: 'Notify when a screening is rejected' },
              { key: 'suspicious', label: 'Suspicious Flags', desc: 'Alert on suspicious screening results' },
              { key: 'verified', label: 'Verified Confirmations', desc: 'Notify on every successful verification' },
              { key: 'systemAlerts', label: 'System Alerts', desc: 'Backend errors or service disruptions' },
              { key: 'email', label: 'Email Notifications', desc: 'Send summary emails to your registered address' },
            ].map(({ key, label, desc }) => (
              <div className="toggle-wrap" key={key}>
                <div>
                  <div className="toggle-label">{label}</div>
                  <div className="toggle-desc">{desc}</div>
                </div>
                <Toggle on={notifs[key]} onToggle={() => setNotifs(n => ({ ...n, [key]: !n[key] }))} />
              </div>
            ))}
          </div>
        );

      case 'api':
        return (
          <div>
            <div className="settings-section-title">API Configuration</div>
            <div className="settings-section-desc">Configure the backend connection for live screening</div>

            <div className="form-group">
              <label className="form-label">Backend Base URL</label>
              <input
                className="form-input font-mono"
                value={api.baseUrl}
                onChange={e => setApi(a => ({ ...a, baseUrl: e.target.value }))}
                style={{ fontFamily: 'JetBrains Mono, monospace' }}
                placeholder="http://localhost:8000"
              />
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 5 }}>
                Screening endpoint: {api.baseUrl}/api/v1/screen
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">API Key</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="form-input font-mono"
                  type={showKey ? 'text' : 'password'}
                  value={api.key}
                  onChange={e => setApi(a => ({ ...a, key: e.target.value }))}
                  style={{ fontFamily: 'JetBrains Mono, monospace', paddingRight: 40 }}
                />
                <button
                  type="button"
                  className="input-addon-right"
                  onClick={() => setShowKey(v => !v)}
                >
                  {showKey ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <div className="info-box blue" style={{ marginTop: 4 }}>
              <Key size={14} color="var(--accent-blue-light)" style={{ flexShrink: 0 }} />
              <div>The API key is sent as <code style={{ fontFamily: 'JetBrains Mono, monospace', background: 'var(--border-subtle)', padding: '1px 5px', borderRadius: 3 }}>X-API-Key</code> in request headers. Keep it secret.</div>
            </div>
          </div>
        );

      case 'security':
        return (
          <div>
            <div className="settings-section-title">Security Settings</div>
            <div className="settings-section-desc">Manage your password and active sessions</div>

            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 14, color: 'var(--text-primary)' }}>Change Password</div>

            <div className="form-group">
              <label className="form-label">Current Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="form-input"
                  type={showPw ? 'text' : 'password'}
                  value={pw.current}
                  onChange={e => setPw(p => ({ ...p, current: e.target.value }))}
                  placeholder="••••••••"
                  style={{ paddingRight: 40 }}
                />
                <button type="button" className="input-addon-right" onClick={() => setShowPw(v => !v)}>
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="form-group">
                <label className="form-label">New Password</label>
                <input className="form-input" type="password" value={pw.next} onChange={e => setPw(p => ({ ...p, next: e.target.value }))} placeholder="••••••••" />
              </div>
              <div className="form-group">
                <label className="form-label">Confirm New Password</label>
                <input className="form-input" type="password" value={pw.confirm} onChange={e => setPw(p => ({ ...p, confirm: e.target.value }))} placeholder="••••••••" />
              </div>
            </div>

            <div className="divider" />
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 14, color: 'var(--text-primary)' }}>Active Sessions</div>

            {[
              { device: 'Chrome on Windows 11', location: 'New Delhi, IN', time: 'Now — Current session', current: true },
              { device: 'Firefox on Ubuntu', location: 'Ghaziabad, IN', time: '2 hours ago', current: false },
            ].map((session, i) => (
              <div key={i} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '12px 0', borderBottom: '1px solid var(--border-subtle)' }}>
                <div>
                  <div style={{ fontSize: 13, fontWeight: 500, color: 'var(--text-primary)' }}>{session.device}</div>
                  <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 2 }}>{session.location} · {session.time}</div>
                </div>
                {session.current ? (
                  <span className="tag" style={{ background: 'var(--success-bg)', color: 'var(--success)' }}>Current</span>
                ) : (
                  <button className="btn btn-danger btn-sm">Revoke</button>
                )}
              </div>
            ))}
          </div>
        );

      default: return null;
    }
  };

  return (
    <div>
      <div className="page-header flex justify-between items-center">
        <div>
          <div className="page-title">Settings</div>
          <div className="page-subtitle">Manage your profile, preferences, and system configuration</div>
        </div>
        <button className="btn btn-primary" onClick={handleSave}>
          <Save size={14} /> {saved ? 'Saved!' : 'Save Changes'}
        </button>
      </div>

      <div className="settings-grid">
        {/* Settings nav */}
        <div className="card card-sm" style={{ alignSelf: 'start' }}>
          <div className="settings-nav">
            {SECTIONS.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                className={`settings-nav-item${active === id ? ' active' : ''}`}
                onClick={() => setActive(id)}
                style={{ background: 'none', border: active === id ? undefined : '1px solid transparent' }}
              >
                <Icon size={14} />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Settings content */}
        <div className="card">
          {renderSection()}
        </div>
      </div>
    </div>
  );
}
