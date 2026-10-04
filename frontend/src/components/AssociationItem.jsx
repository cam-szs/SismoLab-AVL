export default function AssociationItem({ sourceId, referenceId, distance, timeHours }) {
  return (
    <div className="association-item" aria-label={`Asociación #${sourceId} → #${referenceId}`}>
      <strong>#{sourceId}</strong>
      <span>→ #{referenceId}</span>
      <small>{distance} km · {timeHours} h</small>
    </div>
  );
}
