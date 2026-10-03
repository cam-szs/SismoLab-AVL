import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";
const emptyForm = {
  event_id: "",
  magnitude: "",
  depth_km: "",
  x_km: "",
  y_km: "",
  station: "ST-",
};

async function fetchJson(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "Error del backend");
  }
  return response.json();
}

export default function App() {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const [form, setForm] = useState(emptyForm);

  const refreshState = async () => {
    try {
      const nextState = await fetchJson(`${API_URL}/api/state`);
      setState(nextState);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo consultar el backend");
    }
  };

  useEffect(() => {
    refreshState();
    const timer = window.setInterval(refreshState, 3000);
    return () => window.clearInterval(timer);
  }, []);

  const updateMode = async (mode) => {
    try {
      const nextState = await fetchJson(`${API_URL}/api/scenario/mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      setState((previous) => ({ ...previous, mode: nextState.mode, clock: nextState.clock, scenario: nextState }));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo cambiar el modo");
    }
  };

  const advanceClock = async (amount = 1) => {
    try {
      const nextState = await fetchJson(`${API_URL}/api/scenario/clock`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ amount }),
      });
      setState((previous) => ({ ...previous, mode: nextState.mode, clock: nextState.clock, scenario: nextState }));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo avanzar el reloj");
    }
  };

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const submitReport = async (event) => {
    event.preventDefault();
    try {
      await fetchJson(`${API_URL}/api/reports`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_id: Number(form.event_id),
          magnitude: Number(form.magnitude),
          depth_km: Number(form.depth_km),
          x_km: Number(form.x_km),
          y_km: Number(form.y_km),
          station: form.station,
          revision: 1,
        }),
      });
      setForm(emptyForm);
      await refreshState();
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo enviar el reporte");
    }
  };

  const processNextReport = async () => {
    try {
      const nextState = await fetchJson(`${API_URL}/api/queue/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      setState((previous) => ({
        ...previous,
        queue: nextState.queue,
        events: nextState.events,
        metrics: { ...(previous?.metrics ?? {}), ...nextState.metrics },
      }));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo procesar la cola");
    }
  };

  const archiveEvent = async (eventId) => {
    try {
      await fetchJson(`${API_URL}/api/archive`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: eventId }),
      });
      await refreshState();
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo archivar el evento");
    }
  };

  const recoverEvent = async (eventId) => {
    try {
      await fetchJson(`${API_URL}/api/recover`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ event_id: eventId }),
      });
      await refreshState();
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo recuperar el evento");
    }
  };

  const saveState = async () => {
    try {
      const payload = await fetchJson(`${API_URL}/api/persist`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ state: state ?? {}, path: "data/scenario_state.json" }),
      });
      setState((previous) => ({ ...(previous ?? {}), ...payload.state }));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo guardar el estado");
    }
  };

  const loadSavedState = async () => {
    try {
      const payload = await fetchJson(`${API_URL}/api/load`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ path: "data/scenario_state.json" }),
      });
      setState(payload.state ?? payload);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo cargar el estado guardado");
    }
  };

  const queueItems = state?.queue ?? [];
  const activeEvents = state?.events ?? [];
  const archivedEvents = state?.history?.archived ?? [];
  const associations = state?.associations ?? [];
  const mapPoints = activeEvents.map((event) => ({
    id: event.id,
    left: Math.min(90, Math.max(8, (event.epicenter?.x ?? 0) / 10)),
    top: Math.min(90, Math.max(8, (event.epicenter?.y ?? 0) / 10)),
  }));

  return (
    <main className="shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">OBSERVATORIO SISMICO SIMULADO</p>
          <h1>SismoLab <span>AVL</span></h1>
        </div>
        <div className={`connection ${error ? "offline" : "online"}`}>
          <i /> {error ? "Backend desconectado" : "Backend conectado"}
        </div>
      </header>

      {error && <p className="error">{error}. Ejecuta la API en el puerto 8000.</p>}

      <section className="hero-panel">
        <div>
          <p className="eyebrow">CENTRO DE CONTROL</p>
          <h2>El catálogo activo toma forma en tiempo real.</h2>
          <p className="lede">
            El frontend ya consulta el backend. El modo de ejecución y el reloj del escenario se
            sincronizan con la API para reflejar el estado real del observatorio.
          </p>
        </div>
        <div className="mode-badge">
          <strong>{state?.mode ?? "--"}</strong>
          <span>modo de ejecución</span>
        </div>
      </section>

      <section className="metrics" aria-label="Métricas del escenario">
        {[
          ["Reloj", state?.clock ?? 0],
          ["Eventos activos", state?.metrics?.active ?? "--"],
          ["En cola", state?.queue?.length ?? "--"],
          ["Pendientes", state?.metrics?.pending ?? "--"],
        ].map(([label, value]) => (
          <article className="metric" key={label}>
            <strong>{value}</strong>
            <span>{label}</span>
          </article>
        ))}
      </section>

      <section className="scenario-controls" aria-label="Controles del escenario">
        <div className="scenario-card">
          <div className="card-heading">
            <span>04 / SIMULACIÓN</span>
            <b>MODOS</b>
          </div>
          <div className="mode-switcher">
            {['W', 'R', 'L', 'T'].map((mode) => (
              <button
                key={mode}
                type="button"
                className={state?.mode === mode ? "active" : ""}
                onClick={() => updateMode(mode)}
              >
                {mode}
              </button>
            ))}
          </div>
        </div>

        <div className="scenario-card">
          <div className="card-heading">
            <span>05 / TIEMPO</span>
            <b>RELOJ</b>
          </div>
          <div className="clock-actions">
            <button type="button" onClick={() => advanceClock(1)}>+1</button>
            <button type="button" onClick={() => advanceClock(5)}>+5</button>
            <button type="button" onClick={() => advanceClock(10)}>+10</button>
          </div>
        </div>
      </section>

      <section className="state-actions" aria-label="Persistencia del escenario">
        <button type="button" className="action-button" onClick={saveState}>Guardar estado</button>
        <button type="button" className="action-button secondary" onClick={loadSavedState}>Cargar guardado</button>
      </section>

      <section className="workspace-grid">
        <article className="workspace-card tree-card">
          <div className="card-heading">
            <span>01 / ESTRUCTURA</span>
            <b>AVL</b>
          </div>
          <div className="event-list" aria-live="polite">
            {activeEvents.length === 0 ? (
              <div className="empty-state compact">Sin eventos activos</div>
            ) : (
              activeEvents.map((event) => (
                <div className="event-item" key={event.id}>
                  <div className="event-item-header">
                    <div>
                      <strong>#{event.id}</strong>
                      <span>M {event.magnitude.toFixed(1)} · {event.depth_km.toFixed(1)} km</span>
                    </div>
                    <button type="button" className="archive-button" onClick={() => archiveEvent(event.id)}>
                      Archivar
                    </button>
                  </div>
                  <small>rev {event.revision} · {event.status}</small>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="workspace-card map-card">
          <div className="card-heading">
            <span>02 / TERRITORIO</span>
            <b>MAPA</b>
          </div>
          <div className="map-grid" aria-label="Mapa de eventos">
            {mapPoints.map((point) => (
              <span
                key={point.id}
                className="map-point"
                style={{ left: `${point.left}%`, top: `${point.top}%` }}
                title={`Evento #${point.id}`}
              />
            ))}
          </div>
          <div className="association-list" aria-live="polite">
            {associations.length === 0 ? (
              <span className="empty-association">Sin asociaciones activas</span>
            ) : (
              associations.slice(0, 4).map((item) => (
                <div className="association-item" key={`${item.source_id}-${item.reference_id}`}>
                  <strong>#{item.source_id}</strong>
                  <span>→ #{item.reference_id}</span>
                  <small>{item.distance_km} km · {item.time_hours} h</small>
                </div>
              ))
            )}
          </div>
        </article>

        <article className="workspace-card queue-card">
          <div className="card-heading">
            <span>03 / RECEPCIÓN</span>
            <b>FIFO</b>
          </div>

          <form className="report-form" onSubmit={submitReport}>
            <div className="field-grid">
              <label>
                <span>ID</span>
                <input name="event_id" value={form.event_id} onChange={handleInputChange} type="number" min="1" required />
              </label>
              <label>
                <span>Magnitud</span>
                <input name="magnitude" value={form.magnitude} onChange={handleInputChange} type="number" step="0.1" min="0" required />
              </label>
              <label>
                <span>Profundidad</span>
                <input name="depth_km" value={form.depth_km} onChange={handleInputChange} type="number" step="0.1" min="0" required />
              </label>
              <label>
                <span>X</span>
                <input name="x_km" value={form.x_km} onChange={handleInputChange} type="number" step="0.1" required />
              </label>
              <label>
                <span>Y</span>
                <input name="y_km" value={form.y_km} onChange={handleInputChange} type="number" step="0.1" required />
              </label>
              <label>
                <span>Estación</span>
                <input name="station" value={form.station} onChange={handleInputChange} type="text" required />
              </label>
            </div>
            <button className="submit-report" type="submit">Enviar reporte</button>
          </form>

          <button className="process-report" type="button" onClick={processNextReport}>
            Procesar siguiente
          </button>

          <div className="queue-list" aria-live="polite">
            {queueItems.length === 0 ? (
              <div className="empty-state compact">Sin reportes pendientes</div>
            ) : (
              queueItems.map((item, index) => (
                <div className="queue-item" key={`${item.event_id ?? item.id ?? 'event'}-${index}`}>
                  <strong>#{item.event_id ?? item.id}</strong>
                  <span>{item.station}</span>
                  <small>M {item.magnitude} · {item.depth_km} km</small>
                </div>
              ))
            )}
          </div>
        </article>
      </section>

      <section className="archive-panel">
        <article className="workspace-card archive-card">
          <div className="card-heading">
            <span>06 / HISTORIAL</span>
            <b>ARCHIVADOS</b>
          </div>

          <div className="event-list" aria-live="polite">
            {archivedEvents.length === 0 ? (
              <div className="empty-state compact">Sin eventos archivados</div>
            ) : (
              archivedEvents.map((event) => (
                <div className="event-item archive-item" key={event.id ?? event.event_id}>
                  <div className="event-item-header">
                    <div>
                      <strong>#{event.id ?? event.event_id}</strong>
                      <span>M {Number(event.magnitude ?? 0).toFixed(1)} · {Number(event.depth_km ?? 0).toFixed(1)} km</span>
                    </div>
                    <button
                      type="button"
                      className="recover-button"
                      onClick={() => recoverEvent(event.id ?? event.event_id)}
                    >
                      Recuperar
                    </button>
                  </div>
                  <small>rev {event.revision ?? 1} · {event.status ?? "archived"}</small>
                </div>
              ))
            )}
          </div>
        </article>
      </section>
    </main>
  );
}