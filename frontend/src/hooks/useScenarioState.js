import { useEffect, useMemo, useState } from "react";
import { API_URL, fetchJson } from "../api";
import { findTreeNode } from "../components/TreeView";

export const emptyForm = {
  event_id: "",
  magnitude: "",
  depth_km: "",
  x_km: "",
  y_km: "",
  station: "ST-",
};

export function useScenarioState() {
  const [state, setState] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [action, setAction] = useState("");
  const [form, setForm] = useState(emptyForm);
  const [selectedId, setSelectedId] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editForm, setEditForm] = useState(null);

  const openNode = (node, { edit = false } = {}) => {
    if (!node) return;
    setSelectedId(node.key.event_id);
    setEditMode(edit);
    setEditForm({
      magnitude: String(node.event?.magnitude ?? node.key.magnitude_tenths / 10),
      depth_km: String(node.event?.depth_km ?? 0),
      x_km: String(node.event?.epicenter?.x ?? 0),
      y_km: String(node.event?.epicenter?.y ?? 0),
    });
  };

  const closeNode = () => {
    setSelectedId(null);
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
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          magnitude: Number(editForm.magnitude),
          depth_km: Number(editForm.depth_km),
          x_km: Number(editForm.x_km),
          y_km: Number(editForm.y_km),
        }),
      });
      setState(payload.state);
      setEditMode(false);
      setEditForm(null);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo guardar la corrección");
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
          station: form.station,
          revision: 1,
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
      await fetchJson(`${API_URL}/api/queue/process`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });
      await refreshState();
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo procesar la cola");
    } finally {
      setAction("");
    }
  };

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
    setAction("recover-balance");
    try {
      const payload = await fetchJson(`${API_URL}/api/scenario/recover`, { method: "POST" });
      setState(payload.state);
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
      const payload = await fetchJson(`${API_URL}/api/archive/branch`, { method: "POST" });
      setState(payload.state);
      setError(payload.reason === "no eligible branch" ? "No hay ramas elegibles para archivar" : "");
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
    if (!window.confirm(`¿Eliminar el evento #${eventId}?`)) return;
    setAction(`delete-${eventId}`);
    try {
      const payload = await fetchJson(`${API_URL}/api/events/${eventId}/delete`, { method: "POST" });
      setState(payload.state);
      setError("");
    } catch (reason) {
      setError(reason.message || "No se pudo eliminar el evento");
    } finally {
      setAction("");
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

  const downloadState = () => {
    const payload = JSON.stringify(state ?? {}, null, 2);
    const blob = new Blob([payload], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "sismolab-scenario.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  const loadJsonFile = async (event) => {
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
        body: JSON.stringify({ document, mode: "topology" }),
      });
      setState(payload.state);
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
  const mapPoints = activeEvents.map((event) => ({
    id: event.id,
    left: Math.min(90, Math.max(8, (event.epicenter?.x ?? 0) / 10)),
    top: Math.min(90, Math.max(8, (event.epicenter?.y ?? 0) / 10)),
  }));

  return {
    state,
    error,
    loading,
    action,
    form,
    setForm,
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
    saveState,
    loadSavedState,
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
