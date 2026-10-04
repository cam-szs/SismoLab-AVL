export default function NodePanel({
  node,
  onClose,
  onReview,
  onArchive,
  onDelete,
  busy = false,
}) {
  const eventId = node?.event?.id ?? node?.key?.id ?? node?.key?.event_id ?? "?";
  const magnitude = Number(node?.event?.magnitude ?? node?.key?.magnitude_tenths / 10 ?? 0).toFixed(1);
  const depth = Number(node?.event?.depth_km ?? node?.key?.depth_km ?? 0).toFixed(1);

  return (
    <div className="node-details" aria-live="polite">
      <div className="node-header">
        <div>
          <strong>Nodo #{eventId}</strong>
          <small>M {magnitude} · {depth} km</small>
        </div>
        <button type="button" className="close-button" onClick={onClose} disabled={busy}>Cerrar</button>
      </div>

      <div className="node-actions">
        <button type="button" onClick={onReview} disabled={busy}>Revisar</button>
        <button type="button" onClick={onArchive} disabled={busy}>Archivar</button>
        <button type="button" onClick={onDelete} disabled={busy}>Eliminar</button>
      </div>
    </div>
  );
}
