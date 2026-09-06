export default function Badge({ decision }) {
  const cls = {
    Verified: 'badge badge-verified',
    Suspicious: 'badge badge-suspicious',
    Rejected: 'badge badge-rejected',
  }[decision] || 'badge badge-rejected';

  return (
    <span className={cls}>
      <span className="badge-dot" />
      {decision}
    </span>
  );
}
