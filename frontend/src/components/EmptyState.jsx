export default function EmptyState({ message, compact = false }) {
  return <div className={`empty-state ${compact ? "compact" : ""}`.trim()}>{message}</div>;
}
