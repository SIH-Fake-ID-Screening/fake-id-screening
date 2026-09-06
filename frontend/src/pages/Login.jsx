import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Shield, Mail, Lock, Eye, EyeOff, KeyRound, AlertCircle } from 'lucide-react';

export default function Login() {
  const navigate = useNavigate();
  const [form, setForm] = useState({ email: 'r.kumar@sih-verify.gov.in', password: '', mfa: '' });
  const [showPw, setShowPw] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [step, setStep] = useState(1); // 1 = credentials, 2 = MFA

  const handleCredentials = async (e) => {
    e.preventDefault();
    if (!form.email || !form.password) { setError('Please fill in all fields.'); return; }
    setError('');
    setLoading(true);
    await new Promise(r => setTimeout(r, 1200));
    setLoading(false);
    setStep(2);
  };

  const handleMFA = async (e) => {
    e.preventDefault();
    setLoading(true);
    await new Promise(r => setTimeout(r, 1000));
    setLoading(false);
    navigate('/dashboard');
  };

  return (
    <div className="login-page">
      <div className="login-bg-glow" />
      <div className="login-card">
        <div className="login-header">
          <div className="login-logo">
            <Shield size={26} color="white" />
          </div>
          <div className="login-title">SIH-Verify Portal</div>
          <div className="login-subtitle">
            AI-Based Fake Identity &amp; Document Screening System
          </div>
        </div>

        <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
          {['Credentials', 'MFA Verification'].map((s, i) => (
            <div
              key={s}
              style={{
                flex: 1, height: 3, borderRadius: 2,
                background: step > i ? 'var(--accent-blue)' : 'var(--border-subtle)',
                transition: 'background 0.3s',
              }}
            />
          ))}
        </div>

        {step === 1 ? (
          <form onSubmit={handleCredentials}>
            <div className="form-group">
              <label className="form-label">Official Email Address</label>
              <div className="form-input-icon" style={{ position: 'relative' }}>
                <Mail className="input-icon" size={16} />
                <input
                  className="form-input"
                  type="email"
                  placeholder="officer@sih-verify.gov.in"
                  value={form.email}
                  onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                  style={{ paddingLeft: 40 }}
                />
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Password</label>
              <div style={{ position: 'relative' }}>
                <Lock size={16} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} />
                <input
                  className="form-input"
                  type={showPw ? 'text' : 'password'}
                  placeholder="••••••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  style={{ paddingLeft: 40, paddingRight: 40 }}
                />
                <button
                  type="button"
                  className="input-addon-right"
                  onClick={() => setShowPw(v => !v)}
                >
                  {showPw ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            {error && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--danger)', fontSize: 12, marginBottom: 14 }}>
                <AlertCircle size={14} /> {error}
              </div>
            )}

            <button
              type="submit"
              className="btn btn-primary w-full"
              style={{ justifyContent: 'center', marginTop: 4 }}
              disabled={loading}
            >
              {loading ? (
                <>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ animation: 'spin 1s linear infinite' }}>
                    <path d="M21 12a9 9 0 1 1-6.219-8.56" />
                  </svg>
                  Authenticating…
                </>
              ) : 'Continue'}
            </button>
          </form>
        ) : (
          <form onSubmit={handleMFA}>
            <div style={{ textAlign: 'center', marginBottom: 20 }}>
              <KeyRound size={32} color="var(--accent-blue-light)" style={{ margin: '0 auto 10px' }} />
              <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 4 }}>MFA Verification</div>
              <div style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                Enter the 6-digit code from your authenticator app
              </div>
            </div>

            <div className="form-group">
              <label className="form-label">Authentication Code</label>
              <input
                className="form-input"
                type="text"
                placeholder="000000"
                maxLength={6}
                value={form.mfa}
                onChange={e => setForm(f => ({ ...f, mfa: e.target.value.replace(/\D/g, '') }))}
                style={{ textAlign: 'center', fontSize: 22, fontFamily: 'JetBrains Mono, monospace', letterSpacing: 10 }}
                autoFocus
              />
            </div>

            <button
              type="submit"
              className="btn btn-primary w-full"
              style={{ justifyContent: 'center' }}
              disabled={loading || form.mfa.length < 6}
            >
              {loading ? 'Verifying…' : 'Verify & Login'}
            </button>

            <button
              type="button"
              className="btn btn-ghost w-full"
              style={{ justifyContent: 'center', marginTop: 8 }}
              onClick={() => setStep(1)}
            >
              Back
            </button>
          </form>
        )}

        <div className="login-divider" />
        <div className="security-notice">
          <Shield size={13} color="var(--accent-blue-light)" style={{ flexShrink: 0 }} />
          <span>This system is for authorized government personnel only. All access attempts are logged and monitored.</span>
        </div>
      </div>
    </div>
  );
}
