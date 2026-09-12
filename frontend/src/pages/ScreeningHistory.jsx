import { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Filter, ScanLine, ChevronRight, AlertTriangle, Loader, ChevronLeft } from 'lucide-react';
import Badge from '../components/ui/Badge';
import { getScreenings } from '../services/api';
import { statusToDecision, formatTimestamp, riskColor } from '../services/screeningHelpers';

const DECISIONS = ['All', 'Verified', 'Suspicious', 'Rejected'];
const RISK_LEVELS = ['All', 'Low (0–30)', 'Medium (31–60)', 'High (61–100)'];
const PAGE_SIZE = 50; // fetch batch

function matchesRisk(score, level) {
  if (level === 'All') return true;
  if (score == null) return false;
  if (level === 'Low (0–30)') return score <= 30;
  if (level === 'Medium (31–60)') return score > 30 && score <= 60;
  return score > 60;
}

export default function ScreeningHistory() {
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [offset, setOffset] = useState(0);

  // Filter / sort state
  const [search, setSearch] = useState('');
  const [decision, setDecision] = useState('All');
  const [risk, setRisk] = useState('All');
  const [sortBy, setSortBy] = useState('time');
  const [sortDir, setSortDir] = useState('desc');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const data = await getScreenings(PAGE_SIZE, offset);
        if (!cancelled) {
          setItems(data.items || []);
          setTotal(data.total || 0);
        }
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load screening history.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, [offset]);

  const filtered = useMemo(() => {
    let data = items.map(s => ({
      ...s,
      _decision: statusToDecision(s.status),
    }));

    if (search.trim()) {
      const q = search.toLowerCase();
      data = data.filter(s =>
        s.student_id?.toLowerCase().includes(q) ||
        s.screening_id.toLowerCase().includes(q) ||
        s.status?.toLowerCase().includes(q)
      );
    }

    if (decision !== 'All') data = data.filter(s => s._decision === decision);
    if (risk !== 'All') data = data.filter(s => matchesRisk(s.risk_score, risk));

    data.sort((a, b) => {
      if (sortBy === 'time') {
        const diff = new Date(a.created_at) - new Date(b.created_at);
        return sortDir === 'asc' ? diff : -diff;
      }
      if (sortBy === 'risk') {
        const sa = a.risk_score ?? 0, sb = b.risk_score ?? 0;
        return sortDir === 'asc' ? sa - sb : sb - sa;
      }
      return 0;
    });

    return data;
  }, [items, search, decision, risk, sortBy, sortDir]);

  const toggleSort = (field) => {
    if (sortBy === field) setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    else { setSortBy(field); setSortDir('desc'); }
  };

  const canPrev = offset > 0;
  const canNext = offset + PAGE_SIZE < total;

  return (
    <div>
      <div className="page-header flex justify-between items-center">
        <div>
          <div className="page-title">Screening History</div>
          <div className="page-subtitle">{loading ? '…' : `${total} total screenings on record`}</div>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/screening/new')}>
          <ScanLine size={14} /> New Screening
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="info-box" style={{ marginBottom: 20, background: 'var(--danger-bg)', borderColor: 'var(--danger)' }}>
          <AlertTriangle size={15} color="var(--danger)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--danger)', fontSize: 13 }}>{error}</span>
        </div>
      )}

      {/* Filters */}
      <div className="card mb-6" style={{ marginBottom: 20 }}>
        <div className="filter-bar" style={{ marginBottom: 0 }}>
          <div className="search-wrap" style={{ flex: 1, position: 'relative' }}>
            <Search className="search-icon" size={15} />
            <input
              className="form-input"
              type="text"
              placeholder="Search by student ID, screening ID, or status…"
              value={search}
              onChange={e => setSearch(e.target.value)}
              style={{ paddingLeft: 36 }}
            />
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <Filter size={14} color="var(--text-muted)" />
            <select className="filter-select" value={decision} onChange={e => setDecision(e.target.value)}>
              {DECISIONS.map(d => <option key={d}>{d}</option>)}
            </select>
            <select className="filter-select" value={risk} onChange={e => setRisk(e.target.value)}>
              {RISK_LEVELS.map(r => <option key={r}>{r}</option>)}
            </select>
          </div>
        </div>
      </div>

      {/* Table */}
      {loading ? (
        <div style={{ padding: '60px 0', textAlign: 'center', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10 }}>
          <Loader size={16} style={{ animation: 'spin 1s linear infinite' }} />
          Loading screenings…
        </div>
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Screening ID</th>
                <th>Student ID</th>
                <th>Decision</th>
                <th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('risk')}
                >
                  Risk Score {sortBy === 'risk' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th>Face Confidence</th>
                <th
                  style={{ cursor: 'pointer', userSelect: 'none' }}
                  onClick={() => toggleSort('time')}
                >
                  Timestamp {sortBy === 'time' ? (sortDir === 'asc' ? '↑' : '↓') : ''}
                </th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={7}>
                    <div className="empty-state">
                      <div className="empty-state-icon"><Search size={36} /></div>
                      <div className="empty-state-title">
                        {items.length === 0 ? 'No screenings yet' : 'No screenings match your filters'}
                      </div>
                      <div>{items.length === 0 ? 'Run your first screening to see data here.' : 'Try adjusting the search or filter criteria.'}</div>
                    </div>
                  </td>
                </tr>
              ) : filtered.map(s => {
                const faceConf = s.face_result?.confidence ?? null;
                return (
                  <tr key={s.screening_id} onClick={() => navigate(`/screening/details/${s.screening_id}`)}>
                    <td className="td-mono">{s.screening_id.slice(0, 13)}…</td>
                    <td className="td-mono">{s.student_id || '—'}</td>
                    <td><Badge decision={s._decision} /></td>
                    <td>
                      <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 14, fontWeight: 700, color: riskColor(s.risk_score) }}>
                        {s.risk_score ?? '—'}
                        {s.risk_score != null && <span style={{ fontSize: 10, fontWeight: 400, color: 'var(--text-muted)', marginLeft: 2 }}>/100</span>}
                      </span>
                    </td>
                    <td>
                      {faceConf != null ? (
                        <div className="confidence-bar-wrap">
                          <div className="confidence-bar" style={{ width: 60 }}>
                            <div
                              className="confidence-fill"
                              style={{
                                width: `${faceConf * 100}%`,
                                background: faceConf >= 0.75 ? 'var(--success)' : 'var(--danger)',
                              }}
                            />
                          </div>
                          <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 11 }}>
                            {(faceConf * 100).toFixed(0)}%
                          </span>
                        </div>
                      ) : (
                        <span style={{ color: 'var(--text-muted)', fontSize: 12 }}>N/A</span>
                      )}
                    </td>
                    <td className="td-mono">
                      {formatTimestamp(s.created_at)}
                    </td>
                    <td>
                      <ChevronRight size={15} color="var(--text-muted)" />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Footer: count + pagination */}
      <div style={{ marginTop: 16, display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: 12, color: 'var(--text-muted)' }}>
        <span>Showing {filtered.length} of {items.length} loaded · {total} total</span>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className="btn btn-secondary btn-sm"
            disabled={!canPrev}
            onClick={() => setOffset(o => Math.max(0, o - PAGE_SIZE))}
          >
            <ChevronLeft size={13} /> Prev
          </button>
          <button
            className="btn btn-secondary btn-sm"
            disabled={!canNext}
            onClick={() => setOffset(o => o + PAGE_SIZE)}
          >
            Next <ChevronRight size={13} />
          </button>
        </div>
      </div>
    </div>
  );
}
