import EmptyState from "./EmptyState";

export default function EventList({
  title,
  events = [],
  kind = "active",
  emptyMessage = "Sin eventos",
  onOpen,
  onRecover,
  busy = false,
}) {
  return (
    <div className="event-list" aria-live="polite" aria-label={title}>
      {events.length === 0 ? (
        <EmptyState message={emptyMessage} compact />
      ) : (
        events.map((event) => {
          const id = event.id ?? event.event_id;
          const magnitude = Number(event.magnitude ?? 0).toFixed(1);
          const depth = Number(event.depth_km ?? 0).toFixed(1);
          const status = event.status ?? "pending";
          const revision = event.revision ?? 1;

          return (
            <div className="event-item" key={id}>
              <div className="event-item-header">
                <div>
                  <strong>Evento #{id}</strong>
                  <span>
                    {kind === "archive" ? `M ${magnitude} · ${depth} km` : `M ${magnitude} · ${depth} km`}
                  </span>
                </div>

                {kind === "archive" && onRecover ? (
                  <button
                    type="button"
                    className="recover-button"
                    onClick={() => onRecover?.(id)}
                    disabled={busy}
                  >
                    Recuperar
                  </button>
                ) : (
                  <div className="event-actions">
                    <button
                      type="button"
                      className="edit-button"
                      onClick={() => onOpen?.(id)}
                      disabled={busy}
                    >
                      Abrir
                    </button>
                  </div>
                )}
              </div>
              <small>rev {revision} · {status}</small>
            </div>
          );
        })
      )}
    </div>
  );
}
