import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, CheckCircle, AlertTriangle, XCircle, ScanLine, TrendingUp
} from 'lucide-react';
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import StatCard from '../components/ui/StatCard';
import Badge from '../components/ui/Badge';
import { getStatsSummary, getStatsTrend, getScreenings } from '../services/api';
import { statusToDecision, formatTime, riskColor } from '../services/screeningHelpers';
import { PIPELINE_STEPS } from '../data/mockData';

const CUSTOM_TOOLTIP = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 8, padding: '10px 14px', fontSize: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 6, color: 'var(--text-primary)' }}>{label}</div>
      {payload.map(p => (
        <div key={p.dataKey} style={{ color: p.color }}>{p.name}: {p.value}</div>
      ))}
    </div>
  );
};

const PIE_COLORS = { Low: '#10b981', Medium: '#f59e0b', High: '#ef4444' };

export default function Dashboard() {
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [trend, setTrend] = useState([]);
  const [recent, setRecent] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError('');
      try {
        const [sumData, trendData, screeningsData] = await Promise.all([
          getStatsSummary(),
          getStatsTrend(),
          getScreenings(6, 0),
        ]);
        if (cancelled) return;
        setSummary(sumData);
        // Map trend data: { date, count } → { day: "Sep 01", count }
        setTrend(
          (trendData.data || []).map(d => ({
            day: new Date(d.date + 'T00:00:00').toLocaleDateString('en-IN', { day: '2-digit', month: 'short' }),
            count: d.count,
          }))
        );
        setRecent(screeningsData.items || []);
      } catch (err) {
        if (!cancelled) setError(err.message || 'Failed to load dashboard data.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => { cancelled = true; };
  }, []);

  // Build pie chart data from summary
  const piData = summary
    ? [
        { label: 'Low', value: summary.verified, color: PIE_COLORS.Low },
        { label: 'Medium', value: summary.suspicious, color: PIE_COLORS.Medium },
        { label: 'High', value: summary.rejected, color: PIE_COLORS.High },
      ]
    : [];

  return (
    <div>
      <div className="page-header flex justify-between items-center">
        <div>
          <div className="page-title">Operations Dashboard</div>
          <div className="page-subtitle">Real-time overview of document screening activity</div>
        </div>
        <button className="btn btn-primary" onClick={() => navigate('/screening/new')}>
          <ScanLine size={15} />
          New Screening
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="info-box" style={{ marginBottom: 20, background: 'var(--danger-bg)', borderColor: 'var(--danger)' }}>
          <AlertTriangle size={15} color="var(--danger)" style={{ flexShrink: 0 }} />
          <span style={{ color: 'var(--danger)', fontSize: 13 }}>{error}</span>
        </div>
      )}

      {/* Stat cards */}
      <div className="stat-grid">
        <StatCard label="Total Screenings" value={loading ? '…' : (summary?.total ?? 0)} variant="total" icon={Activity} />
        <StatCard label="Verified" value={loading ? '…' : (summary?.verified ?? 0)} variant="verified" icon={CheckCircle} />
        <StatCard label="Suspicious" value={loading ? '…' : (summary?.suspicious ?? 0)} variant="suspicious" icon={AlertTriangle} />
        <StatCard label="Rejected" value={loading ? '…' : (summary?.rejected ?? 0)} variant="rejected" icon={XCircle} />
      </div>

      {/* Charts row */}
      <div className="chart-grid">
        {/* Line chart — 7-day trend */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">
              <TrendingUp className="card-title-icon" size={16} />
              Screening Activity — Last 7 Days
            </div>
          </div>
          {loading ? (
            <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Loading…
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <LineChart data={trend} margin={{ top: 4, right: 8, left: -20, bottom: 0 }}>
                <XAxis dataKey="day" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} allowDecimals={false} />
                <Tooltip content={<CUSTOM_TOOLTIP />} />
                <Line type="monotone" dataKey="count" name="Screenings" stroke="#3b82f6" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Pie chart — risk distribution from summary */}
        <div className="card">
          <div className="card-header">
            <div className="card-title">Risk Distribution</div>
          </div>
          {loading ? (
            <div style={{ height: 220, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
              Loading…
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={220}>
              <PieChart>
                <Pie
                  data={piData}
                  cx="50%"
                  cy="45%"
                  innerRadius={55}
                  outerRadius={80}
                  dataKey="value"
                  nameKey="label"
                  paddingAngle={3}
                >
                  {piData.map((entry, i) => (
                    <Cell key={i} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v, n) => [v, n]}
                  contentStyle={{ background: 'var(--bg-card)', border: '1px solid var(--border-default)', borderRadius: 8, fontSize: 12 }}
                />
                <Legend
                  iconType="circle"
                  iconSize={8}
                  formatter={(v) => <span style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{v}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Recent screenings table */}
      <div className="card">
        <div className="card-header">
          <div className="card-title">
            <Activity className="card-title-icon" size={16} />
            Recent Screenings
          </div>
          <button className="btn btn-secondary btn-sm" onClick={() => navigate('/screening/history')}>
            View All
          </button>
        </div>

        {loading ? (
          <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            Loading recent screenings…
          </div>
        ) : recent.length === 0 ? (
          <div style={{ padding: '32px 0', textAlign: 'center', color: 'var(--text-muted)', fontSize: 13 }}>
            No screenings yet.
          </div>
        ) : (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>Screening ID</th>
                  <th>Student ID</th>
                  <th>Decision</th>
                  <th>Risk Score</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {recent.map(s => {
                  const decision = statusToDecision(s.status);
                  return (
                    <tr key={s.screening_id} onClick={() => navigate(`/screening/details/${s.screening_id}`)}>
                      <td className="td-mono">{s.screening_id.slice(0, 13)}…</td>
                      <td className="td-mono">{s.student_id || '—'}</td>
                      <td><Badge decision={decision} /></td>
                      <td>
                        <span style={{ fontFamily: 'JetBrains Mono, monospace', fontSize: 13, fontWeight: 700, color: riskColor(s.risk_score) }}>
                          {s.risk_score ?? '—'}
                        </span>
                      </td>
                      <td className="td-mono">{formatTime(s.created_at)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
