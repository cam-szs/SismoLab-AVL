import ActionButton from "./components/ActionButton";
import AssociationItem from "./components/AssociationItem";
import ClockControls from "./components/ClockControls";
import EmptyState from "./components/EmptyState";
import EventList from "./components/EventList";
import MapPoint from "./components/MapPoint";
import MetricCard from "./components/MetricCard";
import ModeSwitcher from "./components/ModeSwitcher";
import NodeDetails from "./components/NodeDetails";
import NodePanel from "./components/NodePanel";
import ParameterGrid from "./components/ParameterGrid";
import QueueItem from "./components/QueueItem";
import SectionHeader from "./components/SectionHeader";
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
    ["En cola", state?.queue?.length ?? "--"],
    ["Pendientes", state?.metrics?.pending ?? "--"],
    ["Altura AVL", avlMetrics.height ?? "--"],
    ["Rotaciones", avlMetrics.rotations ?? "--"],
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
        <ClockControls onAdvance={advanceClock} />
      </div>
    </section>
  );
}

function StateActions({
  action,
  recoverBalance,
  saveState,
  downloadState,
  loadSavedState,
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
      <ActionButton label="Guardar en backend" onClick={saveState} />
      <ActionButton label="Descargar JSON" onClick={downloadState} secondary />
      <ActionButton label="Cargar guardado" onClick={loadSavedState} secondary />
      <label className="action-button secondary file-action">
        {action === "load-file" ? "Cargando..." : "Cargar archivo JSON"}
        <input type="file" accept="application/json,.json" onChange={loadJsonFile} disabled={Boolean(action)} />
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

function TreeSection({ state, avlMetrics, bstMetrics, selectedNode, editMode, editForm, openNode, handleEditChange, submitNodeEdit, reviewEvent, archiveEvent, deleteEvent, closeNode, selectedId, action, setEditMode, setEditForm, activeEvents }) {
  return (
    <WorkspaceCard className="tree-card" index="01" label="ESTRUCTURA" title="AVL VS BST">
      <div className="avl-summary">
        <span>{avlMetrics.balanced === false ? "AVL en modo estrés" : "AVL balanceado"}</span>
        <small>{avlMetrics.size ?? 0} nodos · {avlMetrics.leaves ?? 0} hojas</small>
      </div>
      <div className="avl-tree" aria-label="Estructura del árbol AVL">
        <div className="tree-compare">
          <div className="tree-panel">
            <div className="tree-panel-title">AVL balanceado</div>
            {state?.avl ? (
              <TreeView root={state.avl} tone="avl" onSelect={(node) => openNode(node)} />
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
      </div>
      {selectedNode && (
        <NodePanel
          node={selectedNode}
          onClose={closeNode}
          onReview={() => reviewEvent(selectedId)}
          onArchive={() => archiveEvent(selectedId)}
          onDelete={() => deleteEvent(selectedId)}
          busy={Boolean(action)}
        />
      )}
      <EventList
        title="Eventos activos"
        events={activeEvents}
        kind="active"
        emptyMessage="Sin eventos activos"
        onOpen={(eventId) => openNode(activeEvents.find((event) => event.id === eventId), { edit: true })}
        busy={Boolean(action)}
      />
    </WorkspaceCard>
  );
}

function MapPanel({ mapPoints, associations }) {
  return (
    <WorkspaceCard className="map-card" index="02" label="TERRITORIO" title="MAPA">
      <div className="map-grid" aria-label="Mapa de eventos">
        {mapPoints.map((point) => (
          <MapPoint key={point.id} id={point.id} left={point.left} top={point.top} />
        ))}
      </div>
      <div className="association-list" aria-live="polite">
        {associations.length === 0 ? (
          <span className="empty-association">Sin asociaciones activas</span>
        ) : (
          associations.slice(0, 4).map((item) => (
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

function QueuePanel({ form, handleInputChange, submitReport, processNextReport, queueItems, action }) {
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
        <button className="submit-report" type="submit">Encolar reporte</button>
      </form>

      <button className="process-report" type="button" onClick={processNextReport} disabled={Boolean(action)}>
        Crear nodo desde siguiente reporte
      </button>
      <p className="form-help">
        La recepción primero encola el reporte. El nodo se crea al procesar el siguiente elemento de la cola FIFO.
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
            />
          ))
        )}
      </div>
    </article>
  );
}

function ArchivePanel({ archivedEvents, recoverEvent, action }) {
  return (
    <section className="archive-panel">
      <article className="workspace-card archive-card">
        <SectionHeader index="06" label="HISTORIAL" title="ARCHIVADOS" />

        <EventList
          title="Eventos archivados"
          events={archivedEvents}
          kind="archive"
          emptyMessage="Sin eventos archivados"
          onRecover={(eventId) => recoverEvent(eventId)}
          busy={Boolean(action)}
        />
      </article>
    </section>
  );
}

export default function App() {
  const {
    state,
    error,
    loading,
    action,
    form,
    selectedId,
    editMode,
    editForm,
    openNode,
    closeNode,
    handleEditChange,
    selectedNode,
    submitNodeEdit,
    updateMode,
    updateParameters,
    advanceClock,
    handleInputChange,
    submitReport,
    processNextReport,
    archiveEvent,
    recoverEvent,
    recoverBalance,
    undoLastAction,
    archiveBranch,
    reviewEvent,
    deleteEvent,
    saveState,
    loadSavedState,
    downloadState,
    loadJsonFile,
    queueItems,
    activeEvents,
    archivedEvents,
    associations,
    avlMetrics,
    bstMetrics,
    mapPoints,
    setEditMode,
    setEditForm,
  } = useScenarioState();

  return (
    <main className="shell">
      <TopBar loading={loading} error={error} />

      {error && <p className="error" role="alert">{error}. Ejecuta la API en el puerto 8000.</p>}

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
          saveState={saveState}
          downloadState={downloadState}
          loadSavedState={loadSavedState}
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
            selectedNode={selectedNode}
            editMode={editMode}
            editForm={editForm}
            openNode={openNode}
            handleEditChange={handleEditChange}
            submitNodeEdit={submitNodeEdit}
            reviewEvent={reviewEvent}
            archiveEvent={archiveEvent}
            deleteEvent={deleteEvent}
            closeNode={closeNode}
            selectedId={selectedId}
            action={action}
            setEditMode={setEditMode}
            setEditForm={setEditForm}
            activeEvents={activeEvents}
          />
        </div>

        <div className="operations-column">
          <MapPanel mapPoints={mapPoints} associations={associations} />
          <QueuePanel
            form={form}
            handleInputChange={handleInputChange}
            submitReport={submitReport}
            processNextReport={processNextReport}
            queueItems={queueItems}
            action={action}
          />
        </div>
      </section>

      <ArchivePanel
        archivedEvents={archivedEvents}
        recoverEvent={recoverEvent}
        action={action}
      />
    </main>
  );
}