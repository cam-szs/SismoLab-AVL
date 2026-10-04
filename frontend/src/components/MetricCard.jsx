export default function MetricCard({ label, value }) {
  return (
    <article className="metric" aria-label={label}>
      <strong>{value}</strong>
      <span>{label}</span>
    </article>
  );
}
