const RISK_COLOR = (score) => {
  if (score <= 30) return { stroke: '#10b981', text: '#10b981', label: 'LOW' };
  if (score <= 60) return { stroke: '#f59e0b', text: '#f59e0b', label: 'MEDIUM' };
  return { stroke: '#ef4444', text: '#ef4444', label: 'HIGH' };
};

export default function RiskMeter({ score }) {
  const { stroke, text, label } = RISK_COLOR(score);
  const r = 70;
  const cx = 90;
  const cy = 90;
  const circumference = Math.PI * r; // half arc
  const dashOffset = circumference - (score / 100) * circumference;

  return (
    <div className="risk-meter-wrap">
      <svg width="180" height="110" className="risk-arc-svg">
        {/* Background arc */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke="var(--border-subtle)"
          strokeWidth="10"
          strokeLinecap="round"
        />
        {/* Progress arc */}
        <path
          d={`M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`}
          fill="none"
          stroke={stroke}
          strokeWidth="10"
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          style={{ transition: 'stroke-dashoffset 0.8s ease', filter: `drop-shadow(0 0 6px ${stroke}60)` }}
        />
        {/* Score */}
        <text
          x={cx}
          y={cy - 8}
          textAnchor="middle"
          className="risk-score-label"
          fill={text}
          fontSize="36"
          fontWeight="800"
          fontFamily="JetBrains Mono, monospace"
        >
          {score}
        </text>
        <text
          x={cx}
          y={cy + 14}
          textAnchor="middle"
          fontSize="11"
          fill="var(--text-muted)"
          fontWeight="600"
          letterSpacing="1.5"
          fontFamily="Inter, sans-serif"
        >
          {label} RISK
        </text>
        <text
          x={cx - r + 4}
          y={cy + 18}
          fontSize="10"
          fill="var(--text-muted)"
          fontFamily="JetBrains Mono, monospace"
        >0</text>
        <text
          x={cx + r - 14}
          y={cy + 18}
          fontSize="10"
          fill="var(--text-muted)"
          fontFamily="JetBrains Mono, monospace"
        >100</text>
      </svg>
      <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>Risk Score</div>
    </div>
  );
}
