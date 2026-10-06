import ActionButton from "./components/ActionButton";
import AssociationItem from "./components/AssociationItem";
import ClockControls from "./components/ClockControls";
import EmptyState from "./components/EmptyState";
import EventList from "./components/EventList";
import MetricCard from "./components/MetricCard";
import ModeSwitcher from "./components/ModeSwitcher";
import NodeDetails from "./components/NodeDetails";
import ParameterGrid from "./components/ParameterGrid";
import QueueItem from "./components/QueueItem";
import SectionHeader from "./components/SectionHeader";
import TerritoryMap from "./components/TerritoryMap";
import TreeView from "./components/TreeView";
import WorkspaceCard from "./components/WorkspaceCard";
import { useScenarioState } from "./hooks/useScenarioState";

function TopBar({ loading, error }) {
  return (
    <header className="topbar">
      <div>
        <p className="eyebrow">OBSERVATORIO SISMICO SIMULADO</p>
        <h1>SismoLab <span>AVL</span></h1>
      </div>
      <div className={`connection ${error ? "offline" : "online"}`}>
        <i /> {loading ? "Sincronizando..." : error ? "Backend desconectado" : "Backend conectado"}
      </div>
    </header>
  );
}

function HeroPanel({ mode }) {
  return (
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
        <strong>{mode ?? "--"}</strong>
        <span>modo de ejecución</span>
      </div>
    </section>
  );
}

function MetricCards({ state, avlMetrics }) {
  const metrics = [
    ["Reloj", state?.clock ?? 0],
    ["Eventos activos", state?.metrics?.active ?? "--"],
    ["Históricos", state?.metrics?.archived ?? "--"],
    ["En cola", state?.queue?.length ?? "--"],
    ["Pendientes de atención", state?.metrics?.pending_attention ?? "--"],
    ["Altura AVL", avlMetrics.height ?? "--"],
    ["Hojas AVL", avlMetrics.leaves ?? "--"],
    ["Acceso costoso", state?.metrics?.expensive_access ?? "--"],
    ["Balance", avlMetrics.balanced === false ? "Requiere recuperación" : "OK"],
  ];

  return (
    <section className="metrics" aria-label="Métricas del escenario">
      {metrics.map(([label, value]) => (
        <MetricCard key={label} label={label} value={value} />
      ))}
    </section>
  );
}

function ScenarioControls({ state, action, updateMode, updateParameters, advanceClock }) {
  return (
    <section className="scenario-controls" aria-label="Controles del escenario">
      <div className="scenario-card">
        <SectionHeader index="04" label="SIMULACIÓN" title="MODOS" />
        <ModeSwitcher
          value={state?.mode}
          modes={[
            { value: "normal", label: "Normal" },
            { value: "stress", label: "Estrés" },
          ]}
          onChange={updateMode}
          disabled={Boolean(action)}
        />
        <ParameterGrid
          parameters={[
            { key: "W", label: "Ventana (h)", value: state?.parameters?.W ?? "", min: 0.1, step: 0.1 },
            { key: "R", label: "Distancia (km)", value: state?.parameters?.R ?? "", min: 0.1, step: 0.1 },
            { key: "L", label: "Límite de profundidad", value: state?.parameters?.L ?? "", min: 0, step: 1 },
            { key: "T", label: "Antigüedad (h)", value: state?.parameters?.T ?? "", min: 0.1, step: 0.1 },
          ]}
          onChange={updateParameters}
        />
      </div>

      <div className="scenario-card">
        <SectionHeader index="05" label="TIEMPO" title="RELOJ" />
        <ClockControls
          onAdvance={advanceClock}
          simulationTime={state?.simulation_time}
          disabled={Boolean(action)}
        />
      </div>
    </section>
  );
}

function StateActions({
  action,
  recoverBalance,
  downloadState,
  loadJsonFile,
  undoLastAction,
  archiveBranch,
}) {
  return (
    <section className="state-actions" aria-label="Persistencia del escenario">
      <ActionButton
        label="Recuperar AVL"
        onClick={recoverBalance}
        isLoading={action === "recover-balance"}
        disabled={Boolean(action)}
      />
      <ActionButton label="Exportar JSON" onClick={downloadState} />
      <label className="action-button secondary file-action">
        {action === "load-file" ? "Cargando..." : "Cargar topología JSON"}
        <input type="file" accept="application/json,.json" onChange={(event) => loadJsonFile(event, "topology")} disabled={Boolean(action)} />
      </label>
      <label className="action-button secondary file-action">
        {action === "load-file" ? "Cargando..." : "Cargar inserciones JSON"}
        <input type="file" accept="application/json,.json" onChange={(event) => loadJsonFile(event, "insertions")} disabled={Boolean(action)} />
      </label>
      <ActionButton
        label="Deshacer"
        onClick={undoLastAction}
        isLoading={action === "undo"}
        secondary
        disabled={Boolean(action)}
      />
      <ActionButton
        label="Archivar rama elegible"
        onClick={archiveBranch}
        isLoading={action === "archive-branch"}
        secondary
        disabled={Boolean(action)}
      />
    </section>
  );
}

function TreeSection({ state, avlMetrics, bstMetrics, openNode, openEvent, action, activeEvents }) {
  return (
    <WorkspaceCard className="tree-card" index="01" label="ESTRUCTURA" title="AVL VS BST">
      <div className="avl-summary">
        <span>
          {state?.mode === "stress"
            ? `Modo estrés: rotaciones aplazadas${avlMetrics.balanced === false ? " · el árbol NO cumple la condición AVL" : ""}`
            : "Modo normal: AVL balanceado"}
        </span>
        <small>{avlMetrics.size ?? 0} nodos · {avlMetrics.leaves ?? 0} hojas</small>
      </div>
      <div className="avl-tree" aria-label="Estructura del árbol AVL">
        <div className="tree-compare">
          <div className="tree-panel">
            <div className="tree-panel-title">
              AVL · altura {avlMetrics.height ?? 0}{avlMetrics.balanced === false ? " · desbalanceado (estrés)" : ""}
            </div>
            {state?.avl ? (
              <TreeView
                root={state.avl}
                tone="avl"
                onSelect={(node) => openNode(node)}
                depthLimit={state?.parameters?.L ?? null}
              />
            ) : (
              <EmptyState message="Sin estructura AVL" compact />
            )}
          </div>
          <div className="tree-panel">
            <div className="tree-panel-title bst">BST sin rotaciones · altura {bstMetrics.height ?? 0}</div>
            {state?.bst ? (
              <TreeView root={state.bst} tone="bst" onSelect={(node) => openNode(node)} />
            ) : (
              <EmptyState message="Sin estructura BST" compact />
            )}
          </div>
        </div>
        <div className="tree-legend">
          <span><i className="dot prio-3" /> Prioridad alta</span>
          <span><i className="dot prio-2" /> Media</span>
          <span><i className="dot prio-1" /> Baja</span>
          <span><i className="ring" /> Acceso costoso (profundidad &gt; L = {state?.parameters?.L ?? "—"})</span>
          <span>b = factor de balance · ✓ revisado · • pendiente</span>
        </div>
      </div>
      <EventList
        title="Eventos activos"
        events={activeEvents}
        kind="active"
        emptyMessage="Sin eventos activos"
        onOpen={(eventId) => openEvent(eventId)}
        busy={Boolean(action)}
      />
    </WorkspaceCard>
  );
}

function MapPanel({ zones, mapPoints, associations, openEvent }) {
  const references = associations.filter((item) => item.is_reference);
  return (
    <WorkspaceCard className="map-card" index="02" label="TERRITORIO" title="MAPA">
      <TerritoryMap zones={zones} points={mapPoints} associations={associations} onSelect={openEvent} />
      <div className="association-list" aria-live="polite">
        {references.length === 0 ? (
          <span className="empty-association">Sin asociaciones activas</span>
        ) : (
          references.slice(0, 4).map((item) => (
            <AssociationItem
              key={`${item.source_id}-${item.reference_id}`}
              sourceId={item.source_id}
              referenceId={item.reference_id}
              distance={item.distance_km}
              timeHours={item.time_hours}
            />
          ))
        )}
      </div>
    </WorkspaceCard>
  );
}

function QueuePanel({ form, handleInputChange, submitReport, processNextReport, queueItems, action, autoProcess, setAutoProcess, stepDelay, setStepDelay, stations, loadBurstFile }) {
  return (
    <article className="workspace-card queue-card">
      <SectionHeader index="03" label="RECEPCIÓN" title="FIFO" />

      <form className="report-form" onSubmit={submitReport}>
        <div className="field-grid">
          <label>
            <span>ID</span>
            <input name="event_id" value={form.event_id} onChange={handleInputChange} type="number" min="1" required />
          </label>
          <label>
            <span>Magnitud</span>
            <input name="magnitude" value={form.magnitude} onChange={handleInputChange} type="number" step="0.1" min="-2" max="10" required />
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
          <StationSelect value={form.station} onChange={handleInputChange} stations={stations} />
          <label>
            <span>Revisión</span>
            <input name="revision" value={form.revision} onChange={handleInputChange} type="number" min="1" step="1" required />
          </label>
          <label>
            <span>Ocurrencia (UTC)</span>
            <input name="occurred_at" value={form.occurred_at} onChange={handleInputChange} type="datetime-local" step="1" />
          </label>
        </div>
        <button className="submit-report" type="submit">Encolar reporte</button>
      </form>
      <label className="action-button secondary file-action burst-action">
        {action === "load-burst" ? "Cargando..." : "Cargar ráfaga JSON"}
        <input type="file" accept="application/json,.json" onChange={loadBurstFile} disabled={Boolean(action)} />
      </label>

      <button className="process-report" type="button" onClick={processNextReport} disabled={Boolean(action) || autoProcess}>
        Procesar siguiente reporte
      </button>
      <div className="auto-process">
        <label>
          <span>Pausa entre pasos (ms)</span>
          <input
            type="number"
            min="200"
            step="100"
            value={stepDelay}
            onChange={(event) => setStepDelay(Math.max(200, Number(event.target.value) || 200))}
            disabled={autoProcess}
          />
        </label>
        <button
          type="button"
          className={`action-button ${autoProcess ? "danger" : "secondary"}`}
          onClick={() => setAutoProcess(!autoProcess)}
          disabled={!autoProcess && queueItems.length === 0}
        >
          {autoProcess ? "Pausar" : "Procesamiento continuo"}
        </button>
      </div>
      <p className="form-help">
        La recepción primero encola el reporte. Al procesarlo se decide si es alta, confirmación, corrección,
        conflicto o reporte antiguo. Sin fecha se usa el reloj de simulación.
      </p>

      <div className="queue-list" aria-live="polite">
        {queueItems.length === 0 ? (
          <EmptyState message="Sin reportes pendientes" compact />
        ) : (
          queueItems.map((item, index) => (
            <QueueItem
              key={`${item.event_id ?? item.id ?? 'event'}-${index}`}
              id={item.event_id ?? item.id}
              station={item.station}
              magnitude={item.magnitude}
              depth={item.depth_km}
              revision={item.revision}
              position={index + 1}
            />
          ))
        )}
      </div>
    </article>
  );
}

function ArchivePanel({ archivedEvents, openEvent, action }) {
  return (
    <section className="archive-panel">
      <article className="workspace-card archive-card">
        <SectionHeader index="06" label="HISTORIAL" title="ARCHIVADOS" />

        <EventList
          title="Eventos archivados"
          events={archivedEvents}
          kind="archive"
          emptyMessage="Sin eventos archivados"
          onOpen={(eventId) => openEvent(eventId)}
          busy={Boolean(action)}
        />
      </article>
    </section>
  );
}

const AUDIT_KINDS = {
  order: "Orden por K",
  uniqueness: "Unicidad",
  reference: "Referencia",
  height: "Altura almacenada",
  metadata: "Metadatos",
  balance: "Desbalance",
  balance_expected: "Desbalance esperado (estrés)",
};

function IndicatorsPanel({ state }) {
  const counters = state?.counters ?? { stats: {}, rotations: {} };
  const rotations = counters.rotations ?? {};
  const indicators = state?.metrics?.indicators ?? {};
  const byPriority = state?.metrics?.by_priority ?? {};
  const traversals = state?.traversals ?? {};
  const groups = [
    ["Reportes", [
      ["Correcciones aceptadas", indicators.accepted_corrections],
      ["Reportes descartados", indicators.discarded_reports],
      ["Conflictos", indicators.conflicts],
      ["Altas", counters.stats?.created],
      ["Confirmaciones", counters.stats?.confirmations],
    ]],
    ["Archivo y eliminación", [
      ["Archivos masivos", indicators.archive_operations],
      ["Eventos archivados", indicators.archived_events],
      ["Eliminaciones", counters.stats?.deletions],
      ["Recuperaciones globales", counters.stats?.recoveries],
    ]],
    ["Balanceo", [
      ["Casos LL", rotations.LL],
      ["Casos RR", rotations.RR],
      ["Casos LR", rotations.LR],
      ["Casos RL", rotations.RL],
      ["Giros a la izquierda", rotations.rotate_left],
      ["Giros a la derecha", rotations.rotate_right],
    ]],
    ["Catálogo", [
      ["Prioridad alta", byPriority["3"]],
      ["Prioridad media", byPriority["2"]],
      ["Prioridad baja", byPriority["1"]],
      ["Pendientes de atención", state?.metrics?.pending_attention],
      ["Acceso costoso", state?.metrics?.expensive_access],
    ]],
  ];
  const traversalRows = [
    ["Inorden", traversals.inorder],
    ["Preorden", traversals.preorder],
    ["Postorden", traversals.postorder],
    ["Por niveles", traversals.level_order],
  ];

  return (
    <article className="workspace-card">
      <SectionHeader index="11" label="INDICADORES" title="CONTADORES Y RECORRIDOS" />
      <div className="indicator-groups">
        {groups.map(([title, rows]) => (
          <dl key={title}>
            <dt className="indicator-title">{title}</dt>
            {rows.map(([label, value]) => (
              <div key={label}><dt>{label}</dt><dd>{value ?? 0}</dd></div>
            ))}
          </dl>
        ))}
      </div>
      <p className="form-help">Un caso LR o RL cuenta como un caso y dos giros elementales.</p>
      <dl className="traversals">
        {traversalRows.map(([label, ids]) => (
          <div key={label}>
            <dt>{label}</dt>
            <dd>{ids?.length ? ids.map((id) => `#${id}`).join(" → ") : "—"}</dd>
          </div>
        ))}
      </dl>
    </article>
  );
}

const ORDER_LABELS = {
  given: "Orden de llegada",
  ascending: "Ascendente por K",
  descending: "Descendente por K",
  random: "Aleatorio (semilla fija)",
};

function ComparisonPanel({ comparison, loadComparison, action }) {
  return (
    <article className="workspace-card">
      <SectionHeader index="12" label="DESEMPEÑO" title="AVL VS BST POR ORDEN" />
      <div className="panel-actions">
        <ActionButton
          label="Comparar órdenes de inserción"
          onClick={loadComparison}
          isLoading={action === "compare"}
          secondary
          disabled={Boolean(action)}
        />
      </div>
      <p className="form-help">
        Inserta los eventos activos, con el mismo comparador, en un AVL y un BST nuevos para cada orden y
        busca todas las claves. Cada nodo visitado es una comparación. El catálogo no se modifica.
      </p>
      {comparison ? (
        <div className="comparison-table-wrap">
          <table className="comparison-table">
            <thead>
              <tr>
                <th rowSpan="2">Orden ({comparison.size} eventos)</th>
                <th colSpan="4">AVL</th>
                <th colSpan="4">BST</th>
              </tr>
              <tr>
                <th>Raíz</th><th>Altura</th><th>Hojas</th><th>Comp. (prom / máx)</th>
                <th>Raíz</th><th>Altura</th><th>Hojas</th><th>Comp. (prom / máx)</th>
              </tr>
            </thead>
            <tbody>
              {comparison.orders.map((row) => (
                <tr key={row.order}>
                  <th>{ORDER_LABELS[row.order] ?? row.order}</th>
                  {[row.avl, row.bst].map((tree, index) => (
                    [
                      <td key={`r${index}`}>{tree.root_id ? `#${tree.root_id}` : "—"}</td>,
                      <td key={`h${index}`}>{tree.height}</td>,
                      <td key={`l${index}`}>{tree.leaves}</td>,
                      <td key={`c${index}`}>{tree.average_comparisons} / {tree.max_comparisons}</td>,
                    ]
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : <EmptyState message="Pulsa comparar para medir ambos árboles" compact />}
    </article>
  );
}

const DELTA_LABELS = {
  created: "altas",
  corrections: "correcciones",
  confirmations: "confirmaciones",
  conflicts: "conflictos",
  stale: "antiguos",
  rejected_deleted: "rechazados (eliminado)",
  recoveries: "recuperaciones",
  deletions: "eliminaciones",
  archive_operations: "archivos masivos",
  archived_events: "archivados",
  rotate_left: "giros izq.",
  rotate_right: "giros der.",
  active: "activos",
  archived: "históricos",
  queue: "en cola",
};

const ACTION_LABELS = {
  "create event": "Crear evento",
  "correct event": "Corregir evento",
  "delete event": "Eliminar evento",
  "mark event reviewed": "Marcar revisado",
  "enqueue report": "Encolar reporte",
  "process queued report": "Procesar reporte",
  "archive eligible branch": "Archivar rama",
  "archive single event": "Archivar evento",
  "recover archived event": "Recuperar archivado",
  "global AVL recovery": "Recuperación global",
  "change execution mode": "Cambiar modo",
  "change scenario parameters": "Cambiar parámetros",
  "advance simulation clock": "Avanzar reloj",
  "load JSON": "Cargar JSON",
  "load JSON from path": "Cargar JSON",
  "save version": "Guardar versión",
  "restore version": "Restaurar versión",
  undo: "Deshacer",
};

function ActionLogPanel({ actions }) {
  return (
    <section className="archive-panel">
      <article className="workspace-card">
        <SectionHeader index="13" label="REGISTRO" title="HISTORIAL DE ACCIONES" />
        <p className="form-help">
          Cada acción muestra qué contadores cambió. Deshacer agrega una entrada; no borra la acción revertida.
        </p>
        {actions.length === 0 ? (
          <EmptyState message="Aún no hay acciones" compact />
        ) : (
          <ol className="action-log">
            {actions.map((item) => (
              <li key={item.sequence}>
                <span className="action-seq">{item.sequence}</span>
                <div>
                  <strong>{ACTION_LABELS[item.label] ?? item.label}</strong>
                  <small>{item.detail}</small>
                </div>
                <div className="action-delta">
                  {Object.entries(item.delta).map(([name, value]) => (
                    <span key={name} className={value > 0 ? "up" : "down"}>
                      {value > 0 ? "+" : ""}{value} {DELTA_LABELS[name] ?? name}
                    </span>
                  ))}
                </div>
                <time>{item.simulation_time.replace("T", " ").replace("Z", "")} · {item.mode}</time>
              </li>
            ))}
          </ol>
        )}
      </article>
    </section>
  );
}

function AuditVersionsPanel({ audit, versions, refreshAudit, listVersions, saveVersion, restoreVersion, action }) {
  const save = () => {
    const name = window.prompt("Nombre de la versión (ejemplo: demo-normal):");
    if (name) saveVersion(name);
  };

  return (
    <section className="audit-version-grid">
      <article className="workspace-card">
        <SectionHeader index="07" label="INTEGRIDAD" title="AUDITORÍA" />
        <div className="panel-actions">
          <ActionButton label="Actualizar auditoría" onClick={refreshAudit} secondary />
        </div>
        {audit ? (
          <div className="audit-summary">
            <strong>{audit.balanced ? "Estructura válida" : "Requiere revisión"}</strong>
            <small>Auditoría realizada a las {audit.checkedAt}; pulsa actualizar tras nuevos cambios.</small>
            <span>
              {audit.nodes_checked} nodos verificados · orden {audit.valid_order ? "correcto" : "INCORRECTO"} ·{" "}
              {audit.unbalanced_events?.length ?? 0} desbalanceados
              {audit.expected_unbalance && audit.unbalanced_events?.length ? " (esperado en modo estrés)" : ""}
            </span>
            {audit.issues?.length ? (
              <ul className="audit-issues">
                {audit.issues.map((issue, index) => (
                  <li key={`${issue.event_id}-${issue.kind}-${index}`} className={`issue-${issue.kind}`}>
                    <strong>#{issue.event_id}</strong>
                    <span>{AUDIT_KINDS[issue.kind] ?? issue.kind}</span>
                    <small>{issue.detail}</small>
                  </li>
                ))}
              </ul>
            ) : <small>Sin inconsistencias: orden global, unicidad, referencias, alturas y factores correctos.</small>}
          </div>
        ) : <EmptyState message="Pulsa actualizar para auditar el estado" compact />}
      </article>
      <article className="workspace-card">
        <SectionHeader index="08" label="PERSISTENCIA" title="VERSIONES" />
        <div className="panel-actions">
          <ActionButton label="Guardar versión" onClick={save} secondary disabled={Boolean(action)} />
          <ActionButton label="Actualizar lista" onClick={listVersions} secondary />
        </div>
        {versions.length === 0 ? (
          <EmptyState message="Sin versiones persistidas" compact />
        ) : (
          <ul className="version-list">
            {versions.map((name) => (
              <li key={name}>
                <span>{name}</span>
                <button type="button" onClick={() => restoreVersion(name)} disabled={Boolean(action)}>
                  {action === `version-restore-${name}` ? "..." : "Restaurar"}
                </button>
              </li>
            ))}
          </ul>
        )}
      </article>
    </section>
  );
}

const CREATE_FIELDS = [
  ["event_id", "ID", { type: "number", min: "1", max: "999999", step: "1" }],
  ["magnitude", "Magnitud", { type: "number", min: "-2", max: "10", step: "0.1" }],
  ["depth_km", "Profundidad (km)", { type: "number", min: "0", max: "700", step: "0.1" }],
  ["x_km", "Epicentro X (km)", { type: "number", min: "0", max: "1000", step: "0.1" }],
  ["y_km", "Epicentro Y (km)", { type: "number", min: "0", max: "1000", step: "0.1" }],
];

function StationSelect({ value, onChange, stations }) {
  return (
    <label>
      <span>Estación</span>
      <select name="station" value={value} onChange={onChange} required>
        {stations.map((station) => (
          <option key={station.code} value={station.code}>
            {station.code} ({station.x_km}, {station.y_km})
          </option>
        ))}
      </select>
    </label>
  );
}

function EventToolsPanel({ createForm, handleCreateChange, submitCreate, openEvent, action, stations }) {
  const lookup = (domEvent) => {
    domEvent.preventDefault();
    openEvent(new FormData(domEvent.currentTarget).get("lookup_id"));
  };

  return (
    <article className="workspace-card">
      <SectionHeader index="09" label="CATÁLOGO" title="CREAR Y CONSULTAR" />
      <form className="report-form" onSubmit={submitCreate}>
        <div className="field-grid">
          {CREATE_FIELDS.map(([name, label, attributes]) => (
            <label key={name}>
              <span>{label}</span>
              <input name={name} value={createForm[name]} onChange={handleCreateChange} required {...attributes} />
            </label>
          ))}
          <StationSelect value={createForm.station} onChange={handleCreateChange} stations={stations} />
          <label className="field-wide">
            <span>Ocurrencia (UTC, vacío = reloj)</span>
            <input name="occurred_at" value={createForm.occurred_at} onChange={handleCreateChange} type="datetime-local" step="1" />
          </label>
        </div>
        <button className="submit-report" type="submit" disabled={Boolean(action)}>
          {action === "create" ? "Creando..." : "Crear evento"}
        </button>
      </form>
      <p className="form-help">
        Se valida el rango de cada dato y que el ID no esté activo, archivado ni eliminado. La zona poblada y la
        prioridad se calculan; el evento inicia en revisión 1 y pendiente.
      </p>

      <form className="lookup-form" onSubmit={lookup}>
        <label>
          <span>Buscar por ID</span>
          <input name="lookup_id" type="number" min="1" step="1" required />
        </label>
        <button className="action-button secondary" type="submit" disabled={Boolean(action)}>Consultar</button>
      </form>
    </article>
  );
}

function QueriesPanel({ runQuery, queryResult, openEvent, action }) {
  const submit = (kind) => (domEvent) => {
    domEvent.preventDefault();
    runQuery(kind, Object.fromEntries(new FormData(domEvent.currentTarget)));
  };

  return (
    <article className="workspace-card">
      <SectionHeader index="10" label="ANÁLISIS" title="CONSULTAS" />
      <div className="query-forms">
        <form onSubmit={submit("top")}>
          <span className="query-title">Primeros k pendientes</span>
          <label><span>k</span><input name="k" type="number" min="1" step="1" defaultValue="5" required /></label>
          <button className="action-button secondary" type="submit" disabled={Boolean(action)}>Ejecutar</button>
        </form>
        <form onSubmit={submit("magnitude")}>
          <span className="query-title">Intervalo de magnitud</span>
          <label><span>Mín</span><input name="min" type="number" min="-2" max="10" step="0.1" defaultValue="4.5" required /></label>
          <label><span>Máx</span><input name="max" type="number" min="-2" max="10" step="0.1" defaultValue="10" required /></label>
          <button className="action-button secondary" type="submit" disabled={Boolean(action)}>Ejecutar</button>
        </form>
        <form onSubmit={submit("depth-dates")}>
          <span className="query-title">Profundidad ≤ H en fechas</span>
          <label><span>H máx (km)</span><input name="maxDepth" type="number" min="0" max="700" step="0.1" defaultValue="30" required /></label>
          <label><span>Desde (UTC)</span><input name="start" type="datetime-local" step="1" required /></label>
          <label><span>Hasta (UTC)</span><input name="end" type="datetime-local" step="1" required /></label>
          <button className="action-button secondary" type="submit" disabled={Boolean(action)}>Ejecutar</button>
        </form>
        <form onSubmit={submit("expensive")}>
          <span className="query-title">Acceso costoso (prioridad alta, profundidad &gt; L)</span>
          <button className="action-button secondary" type="submit" disabled={Boolean(action)}>Ejecutar</button>
        </form>
      </div>

      {queryResult && (
        <div className="query-result" aria-live="polite">
          <strong>{queryResult.title}</strong>
          <small>
            {queryResult.events.length} resultado(s) · {queryResult.nodesExamined} de {queryResult.treeSize} nodos
            del AVL examinados
          </small>
          {queryResult.events.length === 0 ? (
            <EmptyState message="Sin resultados" compact />
          ) : (
            <ul>
              {queryResult.events.map((event) => (
                <li key={event.id}>
                  <button type="button" onClick={() => openEvent(event.id)}>#{event.id}</button>
                  <span>({event.priority}, {Number(event.magnitude).toFixed(1)}, {event.id})</span>
                  <small>
                    H {event.depth_km} km · {event.occurred_at}
                    {event.node_depth != null && ` · profundidad ${event.node_depth} · ${event.nodes_visited} nodos visitados`}
                  </small>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </article>
  );
}

export default function App() {
  const {
    state,
    error,
    setError,
    connectionError,
    notice,
    setNotice,
    loading,
    action,
    form,
    createForm,
    handleCreateChange,
    submitCreate,
    details,
    openEvent,
    runQuery,
    queryResult,
    zones,
    stations,
    actions,
    comparison,
    loadComparison,
    loadBurstFile,
    autoProcess,
    setAutoProcess,
    stepDelay,
    setStepDelay,
    selectedId,
    editMode,
    editForm,
    openNode,
    closeNode,
    handleEditChange,
    submitNodeEdit,
    updateMode,
    updateParameters,
    advanceClock,
    handleInputChange,
    submitReport,
    processNextReport,
    recoverBalance,
    undoLastAction,
    archiveBranch,
    reviewEvent,
    deleteEvent,
    downloadState,
    loadJsonFile,
    refreshAudit,
    listVersions,
    saveVersion,
    restoreVersion,
    queueItems,
    activeEvents,
    archivedEvents,
    associations,
    avlMetrics,
    bstMetrics,
    mapPoints,
    audit,
    versions,
    setEditMode,
  } = useScenarioState();

  return (
    <main className="shell">
      <TopBar loading={loading} error={connectionError} />

      {connectionError && (
        <p className="error" role="alert">
          {connectionError}. Verifica que la API esté corriendo en el puerto 8000.
        </p>
      )}
      {/* Fixed toasts so the result of an action is visible wherever the user scrolled. */}
      <div className="toast-stack">
        {error && (
          <p className="toast toast-error" role="alert">
            <span>{error}</span>
            <button type="button" onClick={() => setError("")} aria-label="Cerrar aviso">×</button>
          </p>
        )}
        {notice && (
          <p className="toast toast-notice" role="status">
            <span>{notice}</span>
            <button type="button" onClick={() => setNotice("")} aria-label="Cerrar aviso">×</button>
          </p>
        )}
      </div>

      <HeroPanel mode={state?.mode} />

      <MetricCards state={state} avlMetrics={avlMetrics} />

      <section className="command-row">
        <ScenarioControls
          state={state}
          action={action}
          updateMode={updateMode}
          updateParameters={updateParameters}
          advanceClock={advanceClock}
        />

        <StateActions
          action={action}
          recoverBalance={recoverBalance}
          downloadState={downloadState}
          loadJsonFile={loadJsonFile}
          undoLastAction={undoLastAction}
          archiveBranch={archiveBranch}
        />
      </section>

      <section className="ops-grid">
        <div className="analysis-column">
          <TreeSection
            state={state}
            avlMetrics={avlMetrics}
            bstMetrics={bstMetrics}
            openNode={openNode}
            openEvent={openEvent}
            action={action}
            activeEvents={activeEvents}
          />
        </div>

        <div className="operations-column">
          <MapPanel zones={zones} mapPoints={mapPoints} associations={associations} openEvent={openEvent} />
          <QueuePanel
            form={form}
            handleInputChange={handleInputChange}
            submitReport={submitReport}
            processNextReport={processNextReport}
            queueItems={queueItems}
            action={action}
            autoProcess={autoProcess}
            setAutoProcess={setAutoProcess}
            stepDelay={stepDelay}
            setStepDelay={setStepDelay}
            stations={stations}
            loadBurstFile={loadBurstFile}
          />
        </div>
      </section>

      <section className="tools-grid">
        <EventToolsPanel
          createForm={createForm}
          handleCreateChange={handleCreateChange}
          submitCreate={submitCreate}
          openEvent={openEvent}
          action={action}
          stations={stations}
        />
        <QueriesPanel runQuery={runQuery} queryResult={queryResult} openEvent={openEvent} action={action} />
      </section>

      <section className="tools-grid">
        <IndicatorsPanel state={state} />
        <ComparisonPanel comparison={comparison} loadComparison={loadComparison} action={action} />
      </section>

      <ArchivePanel
        archivedEvents={archivedEvents}
        openEvent={openEvent}
        action={action}
      />
      <ActionLogPanel actions={actions} />
      <AuditVersionsPanel
        audit={audit}
        versions={versions}
        refreshAudit={refreshAudit}
        listVersions={listVersions}
        saveVersion={saveVersion}
        restoreVersion={restoreVersion}
        action={action}
      />

      <NodeDetails
        details={details}
        editMode={editMode}
        editForm={editForm}
        onEditChange={handleEditChange}
        onStartEdit={() => setEditMode(true)}
        onCancelEdit={() => setEditMode(false)}
        onSubmitEdit={submitNodeEdit}
        onReview={() => reviewEvent(selectedId)}
        onDelete={() => deleteEvent(selectedId)}
        onClose={closeNode}
        busy={Boolean(action)}
      />
    </main>
  );
}
