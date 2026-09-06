import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import {
  CheckCircle2, XCircle, AlertTriangle, ArrowLeft, Shield,
  User, Database, Fingerprint, ShieldAlert, ScanLine, History, Loader
} from 'lucide-react';
import Badge from '../components/ui/Badge';
import RiskMeter from '../components/ui/RiskMeter';
import { getScreeningById } from '../services/api';
import {
  statusToDecision, statusToReason, formatTimestamp, riskColor
} from '../services/screeningHelpers';

const SectionCard = ({ title, icon: Icon, children }) => (
  <div className="card mb-4" style={{ marginBottom: 16 }}>
    <div className="card-header" style={{ marginBottom: 16 }}>
      <div className="card-title">
        <Icon size={15} color="var(--accent-blue-light)" />
        {title}
      </div>
    </div>
    {children}
  </div>
);

const DetailRow = ({ label, value, mono = false, children }) => (
  <div className="detail-row">
    <span className="detail-label">{label}</span>
    {children || (
      <span className={`detail-value${mono ? ' mono' : ''}`}>{value ?? '—'}</span>
    )}
  </div>
);

export default function ScreeningResult() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Prefer data passed via navigation state (freshly submitted), then fetch by ID
  const [record, setRecord] = useState(location.state?.result || null);
  const [loading, setLoading] = useState(!record);
  const [error, setError] = useState('');

  useEffect(() => {
    if (record) return; // already have data from navigation state
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await getScreeningById(id);
        if (!cancelled) setRecord(data);
      } catch (err) {
        if (!cancelled) {
          setError(
            err.status === 404
              ? 'Screening record not found.'
              : err.message || 'Failed to load screening result.'
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [id, record]);

  if (loading) {
    return (
      <div style={{ padding: '80px 0', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
        <Loader size={18} style={{ animation: 'spin 1s linear infinite' }} />
        Loading screening result…
      </div>
    );
  }

  if (error) {
    return (
      <div>
        <div className="page-header">
          <div className="page-title">Screening Result</div>
        </div>
        <div className="info-box" style={{ background: 'var(--danger-bg)', borderColor: 'var(--danger)' }}>
          <AlertTriangle size={15} color="var(--danger)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--danger)', fontSize: 13 }}>{error}</span>
        </div>
        <div style={{ marginTop: 16 }}>
          <button className="btn btn-secondary" onClick={() => navigate(-1)}>
            <ArrowLeft size={14} /> Back
          </button>
        </div>
      </div>
    );
  }

  // ---- Derive display values from backend fields ----
  // `record` is a ScreeningResponse (fresh) or ScreeningRecordSchema (from DB)
  const decision = statusToDecision(record.status);
  const decisionColor = { Verified: 'var(--success)', Suspicious: 'var(--warning)', Rejected: 'var(--danger)' }[decision];
  const DecisionIcon = { Verified: CheckCircle2, Suspicious: AlertTriangle, Rejected: XCircle }[decision];

  // Normalise face data — ScreeningResponse uses `face_verification`, DB record uses `face_result`
  const faceData = record.face_verification ?? record.face_result ?? null;

  // OCR data — ScreeningResponse doesn't carry ocr_result in the response body;
  // DB record stores it in `ocr_result` JSON.
  const ocrData = record.ocr_result ?? null;

  // Validation issues — DB record stores { message: "..." }; handle gracefully
  const validationMsg =
    record.validation_issues?.message
    || statusToReason(record.status, record.message);

  const timestamp = record.created_at ?? null;
  const riskScore = record.risk_score ?? null;

  // Student data from ScreeningResponse.student or DB db_verification_result
  const student = record.student ?? record.db_verification_result ?? null;

  return (
    <div>
      {/* Header */}
      <div className="page-header flex justify-between items-center">
        <div>
          <div className="page-title">Screening Result</div>
          <div className="page-subtitle" style={{ fontFamily: 'JetBrains Mono, monospace' }}>
            ID: {record.screening_id}
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <button className="btn btn-secondary" onClick={() => navigate('/screening/history')}>
            <History size={14} /> History
          </button>
          <button className="btn btn-primary" onClick={() => navigate('/screening/new')}>
            <ScanLine size={14} /> New Screening
          </button>
        </div>
      </div>

      {/* Hero result banner */}
      <div className="result-hero" style={{ marginBottom: 24 }}>
        <RiskMeter score={riskScore ?? 0} />

        <div>
          <div style={{ marginBottom: 12 }}>
            <Badge decision={decision} />
          </div>
          <div className="result-decision" style={{ color: decisionColor }}>
            <DecisionIcon size={26} style={{ display: 'inline', verticalAlign: 'middle', marginRight: 10 }} />
            {decision}
          </div>
          {timestamp && (
            <div className="result-id" style={{ marginTop: 8 }}>
              Screened: {formatTimestamp(timestamp)}
            </div>
          )}
          <div style={{
            marginTop: 14, padding: '12px 16px',
            background: `${decisionColor}12`,
            border: `1px solid ${decisionColor}30`,
            borderRadius: 8, fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6,
          }}>
            {validationMsg}
          </div>
        </div>
      </div>

      {/* Details grid */}
      <div className="result-detail-grid">
        {/* OCR Data */}
        <SectionCard title="OCR Extracted Data" icon={ScanLine}>
          {(ocrData || student) ? (
            <>
              <DetailRow label="Name" value={ocrData?.name || student?.name} />
              <DetailRow label="Student ID" value={ocrData?.student_id || student?.student_id} mono />
              <DetailRow label="College" value={ocrData?.college || student?.college} />
              <DetailRow label="Course" value={ocrData?.course || student?.course} />
              <DetailRow label="Date of Birth" value={ocrData?.dob || student?.dob} mono />
              <DetailRow label="Valid Until" value={ocrData?.valid_till || student?.valid_till} mono />
            </>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>
              OCR data not available for this record.
            </div>
          )}
        </SectionCard>

        {/* Database Verification */}
        <SectionCard title="Database Verification" icon={Database}>
          <DetailRow label="Record Found">
            <span style={{ color: student ? 'var(--success)' : 'var(--danger)', fontWeight: 600, fontSize: 13 }}>
              {student ? '✓ Match Found' : '✗ Not Found'}
            </span>
          </DetailRow>
          {student && (
            <>
              <DetailRow label="Account Status">
                <span className="tag" style={{
                  background: student.status === 'active' ? 'var(--success-bg)' : 'var(--danger-bg)',
                  color: student.status === 'active' ? 'var(--success)' : 'var(--danger)',
                }}>
                  {student.status ?? '—'}
                </span>
              </DetailRow>
              <DetailRow label="Blacklisted">
                <span style={{ color: student.blacklisted ? 'var(--danger)' : 'var(--success)', fontWeight: 600, fontSize: 13 }}>
                  {student.blacklisted ? '⚠ YES' : '✓ No'}
                </span>
              </DetailRow>
              <DetailRow label="DB Name" value={student.name} />
              <DetailRow label="DB Course" value={student.course} />
              <DetailRow label="DB College" value={student.college} />
            </>
          )}
        </SectionCard>

        {/* Face Verification */}
        <SectionCard title="Face Verification" icon={Fingerprint}>
          {faceData ? (
            <>
              <DetailRow label="Match Result">
                <span style={{ color: faceData.match ? 'var(--success)' : 'var(--danger)', fontWeight: 600, fontSize: 13 }}>
                  {faceData.match ? '✓ Match Confirmed' : '✗ Mismatch'}
                </span>
              </DetailRow>
              <DetailRow label="Confidence Score">
                <div className="confidence-bar-wrap">
                  <div className="confidence-bar" style={{ width: 100 }}>
                    <div
                      className="confidence-fill"
                      style={{
                        width: `${(faceData.confidence ?? 0) * 100}%`,
                        background: (faceData.confidence ?? 0) >= 0.75 ? 'var(--success)' : 'var(--danger)',
                      }}
                    />
                  </div>
                  <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 12, fontWeight: 700, color: (faceData.confidence ?? 0) >= 0.75 ? 'var(--success)' : 'var(--danger)' }}>
                    {((faceData.confidence ?? 0) * 100).toFixed(0)}%
                  </span>
                </div>
              </DetailRow>
              <DetailRow label="Threshold" value="75% minimum" />
            </>
          ) : (
            <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>
              Face verification was not performed for this screening.
            </div>
          )}
        </SectionCard>

        {/* Tampering — backend doesn't populate this yet; show N/A gracefully */}
        <SectionCard title="Tampering Detection" icon={ShieldAlert}>
          <div style={{ color: 'var(--text-muted)', fontSize: 13, padding: '8px 0' }}>
            Tampering analysis not available for this record.
          </div>
        </SectionCard>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', gap: 12, marginTop: 8 }}>
        <button className="btn btn-secondary" onClick={() => navigate(-1)}>
          <ArrowLeft size={14} /> Back
        </button>
        <button className="btn btn-ghost" onClick={() => navigate(`/screening/details/${record.screening_id}`)}>
          View Full Details
        </button>
      </div>
    </div>
  );
}
