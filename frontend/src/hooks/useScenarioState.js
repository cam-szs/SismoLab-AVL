import { useEffect, useMemo, useRef, useState } from "react";
import { API_URL, fetchJson } from "../api";
import { findTreeNode } from "../components/TreeView";

export const emptyForm = {
  event_id: "",
  magnitude: "",
  depth_km: "",
  x_km: "",
  y_km: "",
  occurred_at: "",
  station: "ST-1",
  revision: "1",
};

export const emptyCreateForm = {
  event_id: "",
  magnitude: "",
  depth_km: "",
  x_km: "",
  y_km: "",
  occurred_at: "",
  station: "ST-1",
};

// <input type="datetime-local"> has no zone; the observatory works in UTC,
// so the typed value is sent as UTC. Empty means "use the simulation clock".
export function toUtcIso(value) {
  if (!value) return undefined;
  const withSeconds = value.length === 16 ? `${value}:00` : value;
  return `${withSeconds}Z`;
}

export function fromUtcIso(value) {
  return value ? value.replace("Z", "").slice(0, 19) : "";
}

const JSON_HEADERS = { "Content-Type": "application/json" };

export function useScenarioState() {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [createForm, setCreateForm] = useState(emptyCreateForm);
  const [selectedId, setSelectedId] = useState(null);
  const [details, setDetails] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState(null);
  const [queryResult, setQueryResult] = useState(null);
  const [comparison, setComparison] = useState(null);
  const [autoProcess, setAutoProcess] = useState(false);
  const [stepDelay, setStepDelay] = useState(1500);
  const autoTimer = useRef(null);

  const loadDetails = async (eventId) => {
    const payload = await fetchJson(`${API_URL}/api/events/${eventId}`);
    setDetails(payload);
    return payload;
  };

  // Open the detail dialog of any event (active, archived or deleted) by id.
  const openEvent = async (eventId, { edit = false } = {}) => {
    if (eventId == null || eventId === "") return;
    setAction(`lookup-${eventId}`);
    try {
      const payload = await loadDetails(Number(eventId));
      const event = payload.event ?? {};
      setSelectedId(Number(eventId));
      setEditMode(edit && payload.status === "active");
      setEditForm({
        magnitude: String(event.magnitude ?? ""),
        depth_km: String(event.depth_km ?? ""),
        x_km: String(event.epicenter?.x ?? ""),
        y_km: String(event.epicenter?.y ?? ""),
        occurred_at: fromUtcIso(event.occurred_at),
      });
      setError("");
    } catch (reason) {
      setError(reason.message || `No existe el evento #${eventId}`);
    } finally {
      setAction("");
    }
  };

  const openNode = (node, options) => openEvent(node?.key?.event_id ?? node?.id, options);

  const closeNode = () => {
    setSelectedId(null);
    setDetails(null);
    setEditMode(false);
    setEditForm(null);
  };

  const handleEditChange = (event) => {
    const { name, value } = event.target;
    setEditForm((previous) => ({ ...(previous ?? {}), [name]: value }));
  };

  const selectedNode = useMemo(() => {
    if (selectedId == null || !state) return null;
    for (const root of [state?.avl, state?.bst]) {
      const found = findTreeNode(root, selectedId);
      if (found) return found;
    }
    return null;
  }, [selectedId, state]);

  const submitNodeEdit = async (event) => {
    event.preventDefault();
    if (!selectedId || !editForm) return;
    setAction(`edit-${selectedId}`);
    try {
      const payload = await fetchJson(`${API_URL}/api/events/${selectedId}/correct`, {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          magnitude: Number(editForm.magnitude),
          depth_km: Number(editForm.depth_km),
          x_km: Number(editForm.x_km),
          y_km: Number(editForm.y_km),
          occurred_at: toUtcIso(editForm.occurred_at),
        }),
      });
      setState(payload.state);
      await loadDetails(selectedId);
      setEditMode(false);
      const corrected = payload.event;
      setNotice(
        `Corrección aceptada: #${corrected.id} pasa a revisión ${corrected.revision}, ` +
        `prioridad ${corrected.priority} y queda pendiente.`
      );
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo guardar la corrección");
    } finally {
      setAction("");
    }
  };

  const handleCreateChange = (event) => {
    const { name, value } = event.target;
    setCreateForm((previous) => ({ ...previous, [name]: value }));
  };

  const submitCreate = async (event) => {
    event.preventDefault();
    setAction("create");
    try {
      const payload = await fetchJson(`${API_URL}/api/events`, {
        method: "POST",
        headers: JSON_HEADERS,
        body: JSON.stringify({
          event_id: Number(createForm.event_id),
          magnitude: Number(createForm.magnitude),
          depth_km: Number(createForm.depth_km),
          x_km: Number(createForm.x_km),
          y_km: Number(createForm.y_km),
          occurred_at: toUtcIso(createForm.occurred_at),
          station: createForm.station,
        }),
      });
      setState(payload.state);
      setCreateForm(emptyCreateForm);
      const created = payload.event;
      setNotice(
        `Evento #${created.id} creado con revisión 1: ` +
        `${created.populated_zone ? "zona poblada" : "zona no poblada"}, prioridad ${created.priority}, ` +
        `clave (${created.priority}, ${created.magnitude.toFixed(1)}, ${created.id}).`
      );
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo crear el evento");
    } finally {
      setAction("");
    }
  };

  const formatTime = (iso) => (iso ? iso.replace("T", " ").replace("Z", "") : "");

  // Section 11 queries. Each response reports how many AVL nodes were examined.
  const runQuery = async (kind, params = {}) => {
    setAction(`query-${kind}`);
    try {
      let url;
      let title;
      if (kind === "top") {
        url = `/api/queries/top-pending?limit=${encodeURIComponent(params.k)}`;
        title = `Primeros ${params.k} pendientes (K descendente)`;
      } else if (kind === "magnitude") {
        url = `/api/queries/magnitude?min=${encodeURIComponent(params.min)}&max=${encodeURIComponent(params.max)}`;
        title = `Magnitud entre ${params.min} y ${params.max}`;
      } else if (kind === "depth-dates") {
        const start = toUtcIso(params.start);
        const end = toUtcIso(params.end);
        url = `/api/queries/depth-dates?max_depth=${encodeURIComponent(params.maxDepth)}` +
          `&start=${encodeURIComponent(start ?? "")}&end=${encodeURIComponent(end ?? "")}`;
        title = `H ≤ ${params.maxDepth} km entre ${formatTime(start)} y ${formatTime(end)}`;
      } else {
        url = "/api/queries/expensive";
        title = "Prioridad alta con acceso costoso";
      }
      const payload = await fetchJson(`${API_URL}${url}`);
      setQueryResult({
        kind,
        title: kind === "expensive" ? `${title} (L = ${payload.limit})` : title,
        events: payload.events ?? [],
        nodesExamined: payload.nodes_examined,
        treeSize: state?.metrics?.avl?.size ?? 0,
      });
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo ejecutar la consulta");
    } finally {
      setAction("");
    }
  };

  const refreshState = async () => {
    setLoading(true);
    try {
      const nextState = await fetchJson(`${API_URL}/api/state`);
      setState(nextState);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo consultar el backend");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshState();
    const timer = window.setInterval(refreshState, 3000);
    return () => window.clearInterval(timer);
  }, []);

  const updateMode = async (mode) => {
    setAction(`mode-${mode}`);
    try {
      const nextState = await fetchJson(`${API_URL}/api/scenario/mode`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      setState(nextState);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo cambiar el modo");
    } finally {
      setAction("");
    }
  };

  const updateParameters = async (name, value) => {
    setAction(`parameter-${name}`);
    try {
      const parameters = { ...(state?.parameters ?? {}), [name]: Number(value) };
      const nextState = await fetchJson(`${API_URL}/api/scenario/parameters`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(parameters),
      });
      setState(nextState);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudieron actualizar los parámetros");
    } finally {
      setAction("");
    }
  };

  const advanceClock = async (amount = 1) => {
    setAction("clock");
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
    } finally {
      setAction("");
    }
  };

  const handleInputChange = (event) => {
    const { name, value } = event.target;
    setForm((previous) => ({ ...previous, [name]: value }));
  };

  const submitReport = async (event) => {
    event.preventDefault();
    setAction("submit");
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
          occurred_at: toUtcIso(form.occurred_at),
          station: form.station,
          revision: Number(form.revision || 1),
        }),
      });
      setForm(emptyForm);
      await refreshState();
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo enviar el reporte");
    } finally {
      setAction("");
    }
  };

  const processNextReport = async () => {
    setAction("process");
    try {
      const payload = await fetchJson(`${API_URL}/api/queue/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      const result = payload.result;
      if (result) {
        const rotations = result.rotations?.length
          ? ` Rotaciones: ${result.rotations.map((item) => `${item.case} en #${item.node_id}`).join(", ")}.`
          : " Sin rotaciones.";
        setNotice(
          `Reporte de ${result.report.station} para #${result.report.id} (rev ${result.report.revision}): ` +
          `${result.decision} — ${result.message}.${rotations}`
        );
      }
      await refreshState();
      return payload.processed;
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo procesar la cola");
    } finally {
      setAction("");
    }
  };

  // Continuous processing: one report per step with a pause between steps.
  // Each step is resolved completely (and is its own undoable action)
  // before the next one starts.
  useEffect(() => {
    if (!autoProcess) return undefined;
    let cancelled = false;
    const step = async () => {
      const processed = await processNextReport();
      if (cancelled) return;
      if (!processed) {
        setAutoProcess(false);
        return;
      }
      autoTimer.current = window.setTimeout(step, stepDelay);
    };
    step();
    return () => {
      cancelled = true;
      window.clearTimeout(autoTimer.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoProcess]);

  const archiveEvent = async (eventId) => {
    setAction(`archive-${eventId}`);
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
    } finally {
      setAction("");
    }
  };

  const recoverEvent = async (eventId) => {
    setAction(`recover-${eventId}`);
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
    } finally {
      setAction("");
    }
  };

  const recoverBalance = async () => {
    // Global recovery pauses report processing (section 8).
    setAutoProcess(false);
    setAction("recover-balance");
    try {
      const payload = await fetchJson(`${API_URL}/api/scenario/recover`, { method: "POST" });
      setState(payload.state);
      const metrics = payload.metrics;
      const delta = metrics.rotation_delta ?? {};
      const cases = (metrics.applied_cases ?? []).map((item) => `${item.case}@#${item.node_id}(${item.balance})`);
      setNotice(
        `Recuperación global: ${metrics.unbalanced_before?.length ?? 0} nodos desbalanceados antes, ` +
        `${cases.length} casos (LL ${delta.LL ?? 0}, RR ${delta.RR ?? 0}, LR ${delta.LR ?? 0}, RL ${delta.RL ?? 0}) y ` +
        `${(delta.rotate_left ?? 0) + (delta.rotate_right ?? 0)} giros elementales. ` +
        `Auditoría: ${payload.audit.balanced ? "AVL válido" : "con errores"}; modo ${payload.mode}.` +
        (cases.length ? ` Detalle: ${cases.join(", ")}.` : "")
      );
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo recuperar el AVL");
    } finally {
      setAction("");
    }
  };

  const undoLastAction = async () => {
    setAction("undo");
    try {
      const payload = await fetchJson(`${API_URL}/api/undo`, { method: "POST" });
      setState(payload.state);
      setError("");
    } catch (reason) {
      setError(reason.message || "No hay acciones para deshacer");
    } finally {
      setAction("");
    }
  };

  const archiveBranch = async () => {
    setAction("archive-branch");
    try {
      const preview = await fetchJson(`${API_URL}/api/archive/branch/preview`);
      if (!preview.root_id) {
        setNotice(`No hay ramas elegibles (T = ${preview.age_limit_hours} h): ${preview.reason}. El estado no cambia.`);
        return;
      }
      const alternatives = preview.alternatives
        .map((item) => `#${item.root_id}: ${item.size} nodos, profundidad ${item.depth}`)
        .join("\n");
      const confirmed = window.confirm(
        `Archivar la rama con raíz #${preview.root_id} (${preview.count} eventos):\n` +
        `${preview.event_ids.map((id) => `#${id}`).join(", ")}\n\n` +
        `Justificación: ${preview.reason}.\n\nRamas elegibles mejor ubicadas:\n${alternatives}`
      );
      if (!confirmed) return;
      const payload = await fetchJson(`${API_URL}/api/archive/branch`, { method: "POST" });
      setState(payload.state);
      setNotice(
        `Rama #${payload.root_id} archivada: ${payload.count} eventos pasan al histórico ` +
        `(${payload.rotations.length} casos de rotación al retirarlos). Se deshace con una sola acción.`
      );
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo archivar la rama");
    } finally {
      setAction("");
    }
  };

  const reviewEvent = async (eventId) => {
    setAction(`review-${eventId}`);
    try {
      const payload = await fetchJson(`${API_URL}/api/events/${eventId}/review`, { method: "POST" });
      setState(payload.state);
      if (selectedId === eventId) await loadDetails(eventId);
      setNotice(`Evento #${eventId} marcado como revisado. Su clave no cambia, así que el árbol no se modifica.`);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo marcar el evento");
    } finally {
      setAction("");
    }
  };

  const correctEvent = async (eventId) => {
    const magnitude = window.prompt("Nueva magnitud (ejemplo: 5.4):");
    if (magnitude === null || magnitude.trim() === "") return;
    setAction(`correct-${eventId}`);
    try {
      const payload = await fetchJson(`${API_URL}/api/events/${eventId}/correct`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ magnitude: Number(magnitude) }),
      });
      setState(payload.state);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo corregir el evento");
    } finally {
      setAction("");
    }
  };

  const deleteEvent = async (eventId) => {
    const event = (state?.events ?? []).find((item) => item.id === eventId);
    const summary = event
      ? `\nClave (${event.priority}, ${Number(event.magnitude).toFixed(1)}, ${event.id}) · ` +
        `M ${event.magnitude} · H ${event.depth_km} km · ${event.occurred_at}`
      : "";
    if (!window.confirm(
      `¿Eliminar el evento #${eventId}?${summary}\n\nSolo se retira este evento; sus descendientes siguen activos ` +
      "y el identificador no podrá reutilizarse."
    )) return;
    setAction(`delete-${eventId}`);
    try {
      const payload = await fetchJson(`${API_URL}/api/events/${eventId}/delete`, { method: "POST" });
      setState(payload.state);
      if (selectedId === eventId) await loadDetails(eventId);
      setNotice(`Evento #${eventId} eliminado. El identificador queda retirado.`);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo eliminar el evento");
    } finally {
      setAction("");
    }
  };

  // Export the live scenario as a file the user saves wherever they choose
  // (section 12: no fixed paths). The action log is history, not state.
  const downloadState = async () => {
    try {
      const { actions, ...live } = await fetchJson(`${API_URL}/api/state`);
      const blob = new Blob([JSON.stringify(live, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `sismolab-${live.mode}-${live.simulation_time.replace(/[:]/g, "")}.json`;
      link.click();
      URL.revokeObjectURL(url);
      setNotice(`Escenario exportado (${live.metrics.active} activos, modo ${live.mode}).`);
    } catch (reason) {
      setError(reason.message || "No se pudo exportar el escenario");
    }
  };

  const loadJsonFile = async (event, mode = "topology") => {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    setAction("load-file");
    try {
      const text = await file.text();
      const document = JSON.parse(text);
      const payload = await fetchJson(`${API_URL}/api/load-json`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ document, mode }),
      });
      setState(payload.state);
      const metrics = payload.state.metrics;
      setNotice(
        mode === "insertions"
          ? `Carga por inserciones: ${metrics.avl.size} eventos. AVL raíz #${payload.state.avl?.key.event_id ?? "—"}, ` +
            `altura ${metrics.avl.height}, ${metrics.avl.leaves} hojas · BST raíz #${payload.state.bst?.key.event_id ?? "—"}, ` +
            `altura ${metrics.bst.height}, ${metrics.bst.leaves} hojas.`
          : `Carga por topología: ${metrics.avl.size} eventos en modo ${payload.state.mode}` +
            `${metrics.avl.balanced ? "" : " (topología desbalanceada, cargada en estrés)"}.`
      );
      setError("");
    } catch (reason) {
      setError(reason instanceof SyntaxError
        ? "El archivo no contiene JSON válido"
        : reason.message || "No se pudo cargar el archivo JSON");
    } finally {
      setAction("");
    }
  };

  const refreshAudit = async () => {
    try {
      const payload = await fetchJson(`${API_URL}/api/audit`);
      setState((previous) => ({ ...(previous ?? {}), audit: payload }));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo consultar la auditoría");
    }
  };

  const loadComparison = async () => {
    setAction("compare");
    try {
      setComparison(await fetchJson(`${API_URL}/api/compare`));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo comparar AVL y BST");
    } finally {
      setAction("");
    }
  };

  const listVersions = async () => {
    try {
      const payload = await fetchJson(`${API_URL}/api/versions`);
      setState((previous) => ({ ...(previous ?? {}), versions: payload.versions ?? [] }));
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudieron consultar las versiones");
    }
  };

  const saveVersion = async (name) => {
    const normalized = name.trim();
    if (!normalized) return;
    setAction("version-save");
    try {
      await fetchJson(`${API_URL}/api/versions/${encodeURIComponent(normalized)}`, { method: "POST" });
      await listVersions();
    } catch (reason) {
      setError(reason.message || "No se pudo guardar la versión");
    } finally {
      setAction("");
    }
  };

  const restoreVersion = async (name) => {
    setAction(`version-restore-${name}`);
    try {
      const payload = await fetchJson(`${API_URL}/api/versions/${encodeURIComponent(name)}/restore`, { method: "POST" });
      setState(payload.state);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo restaurar la versión");
    } finally {
      setAction("");
    }
  };

  const queueItems = state?.queue ?? [];
  const activeEvents = state?.events ?? [];
  const archivedEvents = state?.history?.archived ?? [];
  const associations = state?.associations ?? [];
  const avlMetrics = state?.metrics?.avl ?? {};
  const bstMetrics = state?.metrics?.bst ?? {};
  const depthLimit = state?.parameters?.L ?? 3;
  const depths = avlMetrics.depths ?? {};
  const mapPoints = [
    ...activeEvents.map((event) => ({ event, archived: false })),
    ...archivedEvents.map((event) => ({ event, archived: true })),
  ].map(({ event, archived }) => ({
    id: event.id,
    x: event.epicenter?.x ?? 0,
    y: event.epicenter?.y ?? 0,
    magnitude: event.magnitude,
    priority: event.priority,
    archived,
    expensive: !archived && event.priority === 3 && (depths[event.id] ?? 0) > depthLimit,
  }));
  const zones = state?.scenario?.zones ?? [];
  const stations = state?.scenario?.stations ?? [];
  const actions = state?.actions ?? [];

  return {
    state,
    error,
    notice,
    setNotice,
    loading,
    action,
    form,
    setForm,
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
    autoProcess,
    setAutoProcess,
    stepDelay,
    setStepDelay,
    selectedId,
    setSelectedId,
    editMode,
    setEditMode,
    editForm,
    setEditForm,
    openNode,
    closeNode,
    handleEditChange,
    selectedNode,
    submitNodeEdit,
    refreshState,
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
    correctEvent,
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
    audit: state?.audit ?? null,
    versions: state?.versions ?? [],
  };
}
