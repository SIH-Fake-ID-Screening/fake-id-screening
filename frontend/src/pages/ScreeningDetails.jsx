import { useParams, useNavigate } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  ArrowLeft, AlertTriangle, Download,
  Calendar, ShieldCheck, Cpu, Loader, CheckCircle2
} from 'lucide-react';
import Badge from '../components/ui/Badge';
import RiskMeter from '../components/ui/RiskMeter';
import { getScreeningById } from '../services/api';
import {
  statusToDecision, statusToReason, formatTimestamp, riskColor
} from '../services/screeningHelpers';

const Row = ({ label, value, mono }) => (
  <div className="detail-row">
    <span className="detail-label">{label}</span>
    <span className={`detail-value${mono ? ' mono' : ''}`}>{value ?? '—'}</span>
  </div>
);

export default function ScreeningDetails() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [s, setS] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await getScreeningById(id);
        if (!cancelled) setS(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err.status === 404
              ? 'Screening record not found.'
              : err.status === 400
              ? 'Invalid screening ID format.'
              : err.message || 'Failed to load screening details.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id]);

  if (loading) {
    return (
      <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
        <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
        Loading screening details…
      </div>
    );
  }

  if (error || !s) {
    return (
      <div>
        <div className="page-header">
          <button className="btn btn-ghost btn-sm" onClick={() => navigate('/screening/history')} style={{ marginBottom: 8, padding: '4px 0' }}>
            <ArrowLeft size={14} /> Back to History
          </button>
          <div className="page-title">Screening Details</div>
        </div>
        <div className="info-box" style={{ background: 'var(--danger-bg)', borderColor: 'var(--danger)' }}>
          <AlertTriangle size={15} color="var(--danger)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--danger)', fontSize: 13 }}>{error || 'Record not found.'}</span>
        </div>
        <button className="btn btn-secondary" style={{ marginTop: 16 }} onClick={() => navigate('/screening/history')}>
          <ArrowLeft size={14} /> Back to History
        </button>
      </div>
    );
  }

  // ---- Derive display values ----
  const decision = statusToDecision(s.status);
  const decisionColor = { Verified: 'var(--success)', Suspicious: 'var(--warning)', Rejected: 'var(--danger)' }[decision];

  const faceData = s.face_result ?? null;
  const ocrData = s.ocr_result ?? null;
  const student = s.db_verification_result ?? null;
  const issueMsg = s.validation_issues?.message || statusToReason(s.status, null);

  return (
    <div>
      <div className="page-header flex justify-between items-center">
        <div>
          <button
            className="btn btn-ghost btn-sm"
            onClick={() => navigate('/screening/history')}
            style={{ marginBottom: 8, padding: '4px 0' }}
          >
            <ArrowLeft size={14} /> Back to History
          </button>
          <div className="page-title">Screening Details</div>
          <div className="page-subtitle font-mono" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
            {s.screening_id}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={() => alert('PDF export coming soon.')}>
            <Download size={14} /> Export PDF
          </button>
        </div>
      </div>

      {/* Main layout: left content + right metadata panel */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: 20, alignItems: 'start' }}>
        {/* Left — main result */}
        <div>
          {/* Hero */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 28 }}>
              <RiskMeter score={s.risk_score ?? 0} />
              <div>
                <Badge decision={decision} />
                <div style={{ fontSize: 28, fontWeight: 800, color: decisionColor, marginTop: 8, letterSpacing: -0.5 }}>
                  {decision}
                </div>
                <div style={{
                  marginTop: 12, padding: '10px 14px',
                  background: `${decisionColor}12`,
                  border: `1px solid ${decisionColor}30`,
                  borderRadius: 8, fontSize: 13, color: 'var(--text-secondary)',
                  lineHeight: 1.6, maxWidth: 480,
                }}>
                  {issueMsg}
                </div>
              </div>
            </div>
          </div>

          {/* OCR */}
          <div className="card" style={{ marginBottom: 16 }}>
            <div className="card-title" style={{ marginBottom: 14 }}>
              <Cpu size={15} color="var(--accent-blue-light)" /> OCR Extracted Fields
            </div>
            {(ocrData || student) ? (
              <>
                <Row label="Full Name" value={ocrData?.name || student?.name} />
                <Row label="Student ID" value={ocrData?.student_id || student?.student_id} mono />
                <Row label="College" value={ocrData?.college || student?.college} />
                <Row label="Course / Branch" value={ocrData?.course || student?.course} />
                <Row label="Date of Birth" value={ocrData?.dob || student?.dob} mono />
                <Row label="Valid Until" value={ocrData?.valid_till || student?.valid_till} mono />
              </>
            ) : (
              <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>OCR data not available.</div>
            )}
          </div>

          {/* Database + Face */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="card">
              <div className="card-title" style={{ marginBottom: 14 }}>
                <ShieldCheck size={15} color="var(--accent-blue-light)" /> Database Match
              </div>
              <Row label="Record Found" value={student ? '✓ Yes' : '✗ No'} />
              <Row label="Account Status" value={student?.status ?? '—'} />
              <Row label="Blacklisted" value={student ? (student.blacklisted ? '⚠ Yes' : '✓ No') : '—'} />
            </div>

            <div className="card">
              <div className="card-title" style={{ marginBottom: 14 }}>
                <CheckCircle2 size={15} color="var(--accent-blue-light)" /> Face Verification
              </div>
              {faceData ? (
                <>
                  <Row
                    label="Face Match"
                    value={`${faceData.match ? '✓ Match' : '✗ Mismatch'} — ${((faceData.confidence ?? 0) * 100).toFixed(0)}%`}
                  />
                  <Row label="Confidence" value={`${((faceData.confidence ?? 0) * 100).toFixed(0)}%`} mono />
                </>
              ) : (
                <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>Skipped</div>
              )}
            </div>
          </div>
        </div>

        {/* Right — metadata panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card card-sm">
            <div className="card-title" style={{ marginBottom: 14, fontSize: 13 }}>
              <Calendar size={13} color="var(--accent-blue-light)" /> Session Metadata
            </div>
            <Row label="Timestamp" value={formatTimestamp(s.created_at)} mono />
            <Row label="Status Code" value={s.status} mono />
            <Row label="Decision" value={decision} />
            <Row label="Risk Score" value={s.risk_score != null ? `${s.risk_score} / 100` : '—'} mono />
            <Row label="Risk Level" value={s.risk_level} />
          </div>

          <div className="card card-sm">
            <div className="card-title" style={{ marginBottom: 14, fontSize: 13 }}>
              Pipeline Steps
            </div>
            {['Upload', 'OCR', 'Database', 'Face Match', 'Risk Analysis', 'Decision'].map(step => (
              <div key={step} className="detail-row" style={{ padding: '7px 0' }}>
                <span className="detail-label">{step}</span>
                <span style={{ fontSize: 11, color: 'var(--success)', fontWeight: 600 }}>✓ Done</span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
