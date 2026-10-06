export default function SectionHeader({ label, title, className = "" }) {
  return (
    <div className={`card-heading ${className}`.trim()}>
      <span>{label}</span>
      <b>{title}</b>
    </div>
  );
}
