export default function StatCard({ label, value, variant, icon: Icon, change }) {
  return (
    <div className={`stat-card ${variant}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      {change && <div className="stat-change">{change}</div>}
      {Icon && (
        <div className="stat-icon-bg">
          <Icon size={60} />
        </div>
      )}
    </div>
  );
}
