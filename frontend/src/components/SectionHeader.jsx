export default function SectionHeader({ index, label, title, className = "" }) {
  return (
    <div className={`card-heading ${className}`.trim()}>
      <span>{index} / {label}</span>
      <b>{title}</b>
    </div>
  );
}
