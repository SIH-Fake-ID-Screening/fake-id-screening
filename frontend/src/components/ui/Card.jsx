export default function Card({ children, className = '', size = '' }) {
  return (
    <div className={`card${size ? ` card-${size}` : ''} ${className}`}>
      {children}
    </div>
  );
}
