function formatNumber(value, digits = 1) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(digits) : "—";
}

export default function NodeDetails({
  node,
  editMode,
  editForm,
  onEditChange,
  onStartEdit,
  onCancelEdit,
  onSubmitEdit,
  onReview,
  onArchive,
  onDelete,
  onClose,
  busy,
}) {
  if (!node) return null;
  const event = node.event ?? {};
  const key = node.key ?? {};
  const status = event.status ?? "pending";
  const rows = [
    ["Identificador", `#${event.id ?? key.event_id}`],
    ["Clave (P, M, I)", `(${key.priority}, ${formatNumber(key.magnitude_tenths / 10)}, ${key.event_id})`],
    ["Prioridad", key.priority],
    ["Magnitud", formatNumber(event.magnitude)],
    ["Profundidad", `${formatNumber(event.depth_km)} km`],
    ["Epicentro X", `${formatNumber(event.epicenter?.x)} km`],
    ["Epicentro Y", `${formatNumber(event.epicenter?.y)} km`],
    ["Zona poblada", event.populated_zone ? "Sí" : "No"],
    ["Ocurrencia (UTC)", event.occurred_at ?? "—"],
    ["Revisión", event.revision ?? "—"],
    ["Estaciones", (event.stations ?? []).join(", ") || "—"],
    ["Estado", status === "reviewed" ? "Revisado" : "Pendiente"],
    ["Altura en el árbol", node.height],
    ["Factor de balanceo", node.factor_balanceo],
    ["Hijo izquierdo", node.izquierdo ? `#${node.izquierdo.key.event_id}` : "—"],
    ["Hijo derecho", node.derecho ? `#${node.derecho.key.event_id}` : "—"],
  ];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="node-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Detalles del evento ${event.id ?? key.event_id}`}
        onClick={(domEvent) => domEvent.stopPropagation()}
      >
        <div className="node-modal-header">
          <div>
            <span className="node-modal-eyebrow">NODO DEL ÁRBOL</span>
            <h3>Evento #{event.id ?? key.event_id}</h3>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <dl className="node-fields">
          {rows.map(([label, value]) => (
            <div className="node-field" key={label}>
              <dt>{label}</dt>
              <dd>{value}</dd>
            </div>
          ))}
        </dl>

        {editMode ? (
          <form className="node-edit" onSubmit={onSubmitEdit}>
            <p className="node-edit-hint">Edita los valores y guarda para generar una nueva revisión.</p>
            <div className="field-grid">
              {[
                ["magnitude", "Magnitud"],
                ["depth_km", "Profundidad (km)"],
                ["x_km", "Epicentro X (km)"],
                ["y_km", "Epicentro Y (km)"],
              ].map(([name, label]) => (
                <label key={name}>
                  <span>{label}</span>
                  <input
                    name={name}
                    value={editForm?.[name] ?? ""}
                    onChange={onEditChange}
                    type="number"
                    step="0.1"
                    required
                  />
                </label>
              ))}
            </div>
            <div className="node-modal-actions">
              <button type="submit" className="action-button" disabled={busy}>
                {busy ? "Guardando..." : "Guardar corrección"}
              </button>
              <button type="button" className="action-button secondary" onClick={onCancelEdit} disabled={busy}>
                Cancelar
              </button>
            </div>
          </form>
        ) : (
          <div className="node-modal-actions">
            <button
              type="button"
              className="action-button"
              onClick={onReview}
              disabled={busy || status === "reviewed"}
            >
              {status === "reviewed" ? "Ya revisado" : "Marcar revisado"}
            </button>
            <button type="button" className="action-button secondary" onClick={onStartEdit} disabled={busy}>
              Corregir
            </button>
            <button type="button" className="action-button secondary" onClick={onArchive} disabled={busy}>
              Archivar
            </button>
            <button type="button" className="action-button danger" onClick={onDelete} disabled={busy}>
              Eliminar
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
