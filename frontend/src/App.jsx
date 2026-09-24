import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

export default function App() {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch(`${API_URL}/api/state`)
      .then((response) => {
        if (!response.ok) throw new Error("No se pudo consultar el backend");
        return response.json();
      })
      .then(setState)
      .catch((reason) => setError(reason.message));
  }, []);

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
          <h2>El catálogo activo tomará forma aquí.</h2>
          <p className="lede">
            Esta primera pantalla confirma la conexión entre React y Python. Las decisiones de prioridad,
            orden y balance vivirán en el backend.
          </p>
        </div>
        <div className="mode-badge"><strong>{state?.mode ?? "--"}</strong><span>modo de ejecución</span></div>
      </section>

      <section className="metrics" aria-label="Métricas del escenario">
        {[
          ["Eventos activos", state?.metrics.active ?? "--"],
          ["En cola", state?.queue.length ?? "--"],
          ["Pendientes", state?.metrics.pending ?? "--"],
          ["Acceso costoso", state?.metrics.expensive_access ?? "--"],
        ].map(([label, value]) => <article className="metric" key={label}><strong>{value}</strong><span>{label}</span></article>)}
      </section>

      <section className="workspace-grid">
        <article className="workspace-card tree-card"><div className="card-heading"><span>01 / ESTRUCTURA</span><b>AVL</b></div><div className="empty-state">El árbol aparecerá cuando el dominio esté conectado.</div></article>
        <article className="workspace-card map-card"><div className="card-heading"><span>02 / TERRITORIO</span><b>MAPA</b></div><div className="map-grid"><span /><span /><span /><span /><span /><span /></div></article>
        <article className="workspace-card queue-card"><div className="card-heading"><span>03 / RECEPCIÓN</span><b>FIFO</b></div><div className="empty-state">Sin reportes pendientes</div></article>
      </section>
    </main>
  );
}