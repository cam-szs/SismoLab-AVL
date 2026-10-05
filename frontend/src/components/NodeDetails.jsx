function formatNumber(value, digits = 1) {
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric.toFixed(digits) : "—";
}

const STATUS_LABELS = {
  active: "Activo",
  archived: "Archivado",
  deleted: "Eliminado",
};

function AssociationRows({ title, items, emptyMessage }) {
  return (
    <div className="node-associations">
      <span className="node-modal-eyebrow">{title}</span>
      {items.length === 0 ? (
        <small>{emptyMessage}</small>
      ) : (
        <ul>
          {items.map((item) => (
            <li key={item.event_id}>
              <strong>#{item.event_id}</strong>
              <span>{STATUS_LABELS[item.status] ?? item.status}</span>
              <small>{item.distance_km} km · {item.time_hours} h{item.is_reference ? " · referencia elegida" : ""}</small>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function NodeDetails({
  details,
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
  if (!details) return null;
  const { status, event_id: eventId } = details;
  const event = details.event ?? {};
  const location = details.location ?? {};
  const associations = details.associations ?? { candidates: [], referenced_by: [] };
  const isActive = status === "active";

  const rows = status === "deleted" ? [
    ["Estado", "Eliminado (identificador retirado)"],
    ["Recuperación", "Solo al deshacer la eliminación o restaurar una versión"],
  ] : [
    ["Estado", STATUS_LABELS[status] ?? status],
    ["Clave (P, M, I)", details.key],
    ["Prioridad", event.priority],
    ["Magnitud", formatNumber(event.magnitude)],
    ["Profundidad hipocentro", `${formatNumber(event.depth_km)} km`],
    ["Epicentro", `(${formatNumber(event.epicenter?.x)}, ${formatNumber(event.epicenter?.y)}) km`],
    ["Zona poblada", event.populated_zone ? "Sí" : "No"],
    ["Ocurrencia (UTC)", event.occurred_at ?? "—"],
    ["Revisión", event.revision ?? "—"],
    ["Estaciones", (event.stations ?? []).join(", ") || "—"],
    ["Atención", event.status === "reviewed" ? "Revisado" : "Pendiente"],
    ...(isActive ? [
      ["Profundidad del nodo", location.node_depth],
      ["Nodos visitados por clave", location.nodes_visited],
      ["Altura del nodo", location.height],
      ["Factor de balance", location.balance_factor],
      ["Acceso costoso", location.expensive_access
        ? `Sí (profundidad ${location.node_depth} > L = ${details.depth_limit})`
        : `No (L = ${details.depth_limit})`],
      ["Hijo izquierdo", location.left_id ? `#${location.left_id}` : "—"],
      ["Hijo derecho", location.right_id ? `#${location.right_id}` : "—"],
    ] : []),
  ];

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div
        className="node-modal"
        role="dialog"
        aria-modal="true"
        aria-label={`Detalles del evento ${eventId}`}
        onClick={(domEvent) => domEvent.stopPropagation()}
      >
        <div className="node-modal-header">
          <div>
            <span className="node-modal-eyebrow">CONSULTA POR IDENTIFICADOR</span>
            <h3>Evento #{eventId}</h3>
          </div>
          <button type="button" className="modal-close" onClick={onClose} aria-label="Cerrar">
            ×
          </button>
        </div>

        <dl className="node-fields">
          {rows.map(([label, value]) => (
            <div className="node-field" key={label}>
              <dt>{label}</dt>
              <dd>{value ?? "—"}</dd>
            </div>
          ))}
        </dl>

        {status !== "deleted" && (
          <div className="node-association-grid">
            <AssociationRows
              title="CANDIDATOS A REFERENCIA"
              items={associations.candidates}
              emptyMessage="Sin candidatos: queda sin asociación"
            />
            <AssociationRows
              title="LO USAN COMO REFERENCIA"
              items={associations.referenced_by}
              emptyMessage="Ningún evento lo usa como referencia"
            />
          </div>
        )}

        {isActive && editMode ? (
          <form className="node-edit" onSubmit={onSubmitEdit}>
            <p className="node-edit-hint">
              La corrección genera la revisión {Number(event.revision ?? 0) + 1}, recalcula zona y prioridad
              y deja el evento pendiente.
            </p>
            <div className="field-grid">
              {[
                ["magnitude", "Magnitud", "number"],
                ["depth_km", "Profundidad (km)", "number"],
                ["x_km", "Epicentro X (km)", "number"],
                ["y_km", "Epicentro Y (km)", "number"],
                ["occurred_at", "Ocurrencia (UTC)", "datetime-local"],
              ].map(([name, label, type]) => (
                <label key={name}>
                  <span>{label}</span>
                  <input
                    name={name}
                    value={editForm?.[name] ?? ""}
                    onChange={onEditChange}
                    type={type}
                    step={type === "number" ? "0.1" : "1"}
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
        ) : isActive ? (
          <div className="node-modal-actions">
            <button
              type="button"
              className="action-button"
              onClick={onReview}
              disabled={busy || event.status === "reviewed"}
            >
              {event.status === "reviewed" ? "Ya revisado" : "Marcar revisado"}
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
        ) : null}
      </div>
    </div>
  );
}
