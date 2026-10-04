"""HTTP boundary for the React client and persisted scenario state."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from copy import deepcopy
import re

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from domain.event import Event
from domain.event_key import EventKey
from domain.queue_fifo import ReportQueue
from domain.report import Report
from domain.scenario import Scenario
from services.association_service import AssociationService
from services.persistence_service import PersistenceService
from services.report_processor import ReportProcessor
from domain.undo_stack import Snapshot, UndoStack
from domain.node import Node


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = PROJECT_ROOT / "data" / "scenario_state.json"
SCENARIO = Scenario()
REPORT_QUEUE: ReportQueue[Report] = ReportQueue()
REPORT_PROCESSOR = ReportProcessor(
    populated_zone=lambda report: SCENARIO.is_populated(report.x_km, report.y_km)
)
ASSOCIATION_SERVICE = AssociationService()
UNDO_STACK: UndoStack[Snapshot] = UndoStack()
VERSIONS: dict[str, dict[str, Any]] = {}
VERSION_DIR = PROJECT_ROOT / "data" / "versions"


app = FastAPI(title="SismoLab AVL API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, error: ValueError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": str(error)})


@app.exception_handler(KeyError)
async def key_error_handler(request: Request, error: KeyError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": str(error)})


def _serialize_queue() -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    queue = REPORT_QUEUE
    if queue is None:
        return items
    try:
        node = queue._front
        while node is not None:
            payload = node.value.to_dict()
            payload["event_id"] = payload["id"]
            items.append(payload)
            node = node.next
    except AttributeError:
        return items
    return items


def _serialize_events() -> list[dict[str, Any]]:
    events = sorted(REPORT_PROCESSOR.active_events.values(), key=lambda event: event.key)
    return [event.to_dict() for event in events]


def _serialize_history() -> dict[str, Any]:
    return {
        "archived": [event.to_dict() for event in REPORT_PROCESSOR.archived_events.values()],
        "deleted": [
            {"event_id": event_id}
            for event_id in sorted(REPORT_PROCESSOR.deleted_ids)
        ],
    }


def _metrics_payload() -> dict[str, Any]:
    queue_count = len(REPORT_QUEUE)
    tree_metrics = REPORT_PROCESSOR.tree_metrics()
    return {
        "active": len(REPORT_PROCESSOR.active_events),
        "archived": len(REPORT_PROCESSOR.archived_events),
        "pending": queue_count,
        "expensive_access": len(
            REPORT_PROCESSOR.query_expensive_access(SCENARIO.access_depth_limit)
        ),
        "avl": tree_metrics,
        "bst": REPORT_PROCESSOR.bst_metrics(),
        "processing": REPORT_PROCESSOR.stats.copy(),
    }


def _event_from_dict(data: dict[str, Any]) -> Event:
    payload = dict(data)
    if "event_id" not in payload and "id" in payload:
        payload["event_id"] = payload["id"]
    if "id" not in payload and "event_id" in payload:
        payload["id"] = payload["event_id"]
    return Event.from_dict(payload)


def _report_from_dict(data: dict[str, Any]) -> Report:
    payload = dict(data)
    occurred = payload.get("occurred_at")
    if occurred is None:
        occurred = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        occurred = datetime.fromisoformat(str(occurred).replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0)
    return Report.create(
        event_id=int(payload.get("event_id", payload.get("id", 0))),
        magnitude=float(payload.get("magnitude", 0.0)),
        depth_km=float(payload.get("depth_km", 0.0)),
        x_km=float(payload.get("epicenter", {}).get("x", payload.get("x_km", 0.0))),
        y_km=float(payload.get("epicenter", {}).get("y", payload.get("y_km", 0.0))),
        occurred_at=occurred,
        station=str(payload.get("station", "ST-0")),
        revision=int(payload.get("revision", 1)),
    )


def _snapshot_state() -> dict[str, Any]:
    queue_items = _serialize_queue()
    events_payload = _serialize_events()
    history_payload = _serialize_history()
    return {
        "status": "ready",
        "message": "Backend connected and ready for scenario state.",
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "mode": SCENARIO.mode,
        "parameters": SCENARIO.parameters,
        "clock": SCENARIO.clock,
        "events": events_payload,
        "queue": queue_items,
        "history": history_payload,
        "metrics": {
            **_metrics_payload(),
            "pending": len(queue_items),
        },
        "avl": REPORT_PROCESSOR.tree.export_to_dict(),
        "bst": REPORT_PROCESSOR.bst_export(),
        "scenario": _scenario_payload(),
        "associations": _association_payload()["associations"],
        "association_count": _association_payload()["count"],
    }


def _hydrate_from_snapshot(payload: dict[str, Any], *, load_mode: str = "topology") -> None:
    if not isinstance(payload, dict):
        raise ValueError("state must be a JSON object")
    if load_mode not in {"topology", "insertions"}:
        raise ValueError("load mode must be 'topology' or 'insertions'")
    if load_mode == "topology":
        PersistenceService.validate_topology(payload.get("avl"))

    global REPORT_QUEUE, REPORT_PROCESSOR

    if isinstance(payload.get("mode"), str):
        SCENARIO.set_mode(payload["mode"])
    if isinstance(payload.get("clock"), int):
        SCENARIO.clock = payload["clock"]
        SCENARIO.values["clock"] = payload["clock"]
    parameters = payload.get("parameters", payload.get("scenario", {}).get("parameters", {}))
    if isinstance(parameters, dict):
        SCENARIO.set_parameters(
            W=parameters.get("W"),
            R=parameters.get("R"),
            L=parameters.get("L"),
            T=parameters.get("T"),
        )

    REPORT_QUEUE = ReportQueue()
    for item in payload.get("queue", []):
        REPORT_QUEUE.enqueue(_report_from_dict(item))

    active_events: dict[int, Event] = {}
    for item in payload.get("events", []):
        event = _event_from_dict(item)
        if event.event_id in active_events:
            raise ValueError(f"duplicate active event {event.event_id}")
        active_events[event.event_id] = event

    archived_events: dict[int, Event] = {}
    for item in payload.get("history", {}).get("archived", []):
        event = _event_from_dict(item)
        if event.event_id in active_events or event.event_id in archived_events:
            raise ValueError(f"duplicate historical event {event.event_id}")
        archived_events[event.event_id] = event

    deleted_ids: set[int] = set()
    for item in payload.get("history", {}).get("deleted", []):
        if isinstance(item, dict):
            deleted_ids.add(int(item.get("event_id", item.get("id", 0))))
        else:
            deleted_ids.add(int(item))
    overlap = deleted_ids & (set(active_events) | set(archived_events))
    if overlap:
        raise ValueError(f"identities cannot be active and deleted: {sorted(overlap)}")

    REPORT_PROCESSOR = ReportProcessor(
        active_events=active_events,
        archived_events=archived_events,
        deleted_ids=deleted_ids,
        populated_zone=lambda report: SCENARIO.is_populated(report.x_km, report.y_km),
        stress_mode=SCENARIO.stress_mode,
    )
    topology = payload.get("avl") if load_mode == "topology" else None
    if topology is not None:
        def build(node_payload: dict[str, Any] | None) -> Node | None:
            if node_payload is None:
                return None
            key_payload = node_payload["key"]
            event_id = int(key_payload["event_id"])
            event = active_events[event_id]
            stored_key = (
                int(key_payload["priority"]),
                int(key_payload["magnitude_tenths"]),
                event_id,
            )
            if stored_key != (
                event.key.priority,
                event.key.magnitude_tenths,
                event.key.event_id,
            ):
                raise ValueError(f"stored key does not match event {event_id}")
            node = Node(event.key, event)
            node.left = build(node_payload.get("izquierdo"))
            node.right = build(node_payload.get("derecho"))
            node.update_height()
            if node.height != int(node_payload.get("height", node.height)):
                raise ValueError(f"invalid stored height for event {event_id}")
            return node

        REPORT_PROCESSOR.tree.root = build(topology)
        REPORT_PROCESSOR.tree.size = len(active_events)
    audit = REPORT_PROCESSOR.audit_report()
    if not SCENARIO.stress_mode and not audit["balanced"]:
        raise ValueError("normal snapshot must contain a balanced AVL")


def _association_payload() -> dict[str, Any]:
    events = sorted(
        [
            *REPORT_PROCESSOR.active_events.values(),
            *REPORT_PROCESSOR.archived_events.values(),
        ],
        key=lambda event: event.event_id,
    )
    links: list[dict[str, Any]] = []
    for source in events:
        for association in ASSOCIATION_SERVICE.associate(
            source,
            events,
            max_hours=SCENARIO.association_window_hours,
            max_distance_km=SCENARIO.association_distance_km,
        ):
            links.append(
                {
                    "source_id": association.source_id,
                    "reference_id": association.reference_id,
                    "time_hours": round(association.time_hours, 2),
                    "distance_km": round(association.distance_km, 2),
                    "is_reference": association.is_reference,
                }
            )
    return {"count": len(links), "associations": links}


def _default_state() -> dict[str, Any]:
    return _snapshot_state()


def _scenario_payload() -> dict[str, Any]:
    return {
        "mode": SCENARIO.mode,
        "clock": SCENARIO.clock,
        "parameters": SCENARIO.parameters,
        "values": SCENARIO.values.copy(),
    }


def _record_undo(label: str) -> None:
    """Capture a complete immutable state before a user action."""
    UNDO_STACK.push(Snapshot(label=label, state=deepcopy(_snapshot_state())))


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return a cheap endpoint used to verify the local connection."""
    return {"status": "ok"}


@app.get("/api/state")
def state() -> dict[str, Any]:
    """Return the current live state from memory. Explicit /api/load rehydrates from disk."""
    return _snapshot_state()


@app.get("/api/events")
def events_state() -> dict[str, Any]:
    """Expose the currently active events in the catalog."""
    events_payload = _serialize_events()
    return {"events": events_payload, "count": len(events_payload)}


@app.get("/api/scenario")
def scenario() -> dict[str, Any]:
    """Expose the live simulation mode and time."""
    return _scenario_payload()


@app.get("/api/associations")
def associations() -> dict[str, Any]:
    """Expose the active event associations selected by the deterministic matching policy."""
    return _association_payload()


@app.post("/api/scenario/mode")
def set_scenario_mode(payload: dict[str, Any]) -> dict[str, Any]:
    """Set the active scenario mode."""
    mode = payload.get("mode")
    if mode is None:
        raise ValueError("mode is required")
    _record_undo("change execution mode")
    SCENARIO.set_mode(str(mode))
    REPORT_PROCESSOR.set_stress_mode(SCENARIO.stress_mode)
    return _snapshot_state()


@app.post("/api/scenario/parameters")
def set_scenario_parameters(payload: dict[str, Any]) -> dict[str, Any]:
    """Update W/R/L/T and return the recalculated live state."""
    _record_undo("change scenario parameters")
    SCENARIO.set_parameters(
        W=payload.get("W"),
        R=payload.get("R"),
        L=payload.get("L"),
        T=payload.get("T"),
    )
    return _snapshot_state()


@app.post("/api/scenario/recover")
def recover_scenario_balance() -> dict[str, Any]:
    """Recover the global AVL balance after a stress burst."""
    _record_undo("recover AVL balance")
    metrics = REPORT_PROCESSOR.recover_balance()
    if SCENARIO.stress_mode:
        SCENARIO.set_mode("normal")
    REPORT_PROCESSOR.set_stress_mode(False, recover=False)
    return {"recovered": True, "mode": SCENARIO.mode, "metrics": metrics, "state": _snapshot_state()}


@app.post("/api/scenario/clock")
def advance_scenario_clock(payload: dict[str, Any]) -> dict[str, Any]:
    """Advance the simulation clock by a non-negative integer amount."""
    amount = payload.get("amount", 1)
    _record_undo("advance simulation clock")
    SCENARIO.advance_clock(int(amount))
    return _scenario_payload()


@app.get("/api/queue")
def queue_state() -> dict[str, Any]:
    """Expose the current FIFO queue contents."""
    entries = _serialize_queue()
    return {"queue": entries, "count": len(entries)}


@app.post("/api/queue/process")
def process_queue() -> dict[str, Any]:
    """Consume at most one queued report and update the active catalog."""
    if REPORT_QUEUE.is_empty():
        return {
            "processed": False,
            "result": None,
            "events": _serialize_events(),
            "queue": _serialize_queue(),
            "metrics": _metrics_payload(),
        }

    _record_undo("process one queued report")
    result = REPORT_PROCESSOR.process_next(REPORT_QUEUE)
    serialized = {
        "decision": result.decision,
        "message": result.message,
        "report": result.report.to_dict(),
        "event": result.event.to_dict() if result.event is not None else None,
        "previous_event": result.previous_event.to_dict() if result.previous_event is not None else None,
    }
    return {
        "processed": True,
        "result": serialized,
        "events": _serialize_events(),
        "queue": _serialize_queue(),
        "metrics": _metrics_payload(),
    }


@app.post("/api/reports")
def enqueue_report(payload: dict[str, Any]) -> dict[str, Any]:
    """Enqueue a report received from a station."""
    required = ["event_id", "magnitude", "depth_km", "x_km", "y_km", "station"]
    missing = [key for key in required if key not in payload]
    if missing:
        raise ValueError(f"missing required report fields: {', '.join(missing)}")

    occurred_at_raw = payload.get("occurred_at")
    if occurred_at_raw is None:
        occurred_at = datetime.now(timezone.utc).replace(microsecond=0)
    else:
        occurred_at = datetime.fromisoformat(str(occurred_at_raw).replace("Z", "+00:00")).astimezone(timezone.utc).replace(microsecond=0)

    report = Report.create(
        event_id=int(payload["event_id"]),
        magnitude=float(payload["magnitude"]),
        depth_km=float(payload["depth_km"]),
        x_km=float(payload["x_km"]),
        y_km=float(payload["y_km"]),
        occurred_at=occurred_at,
        station=str(payload["station"]),
        revision=int(payload.get("revision", 1)),
    )
    _record_undo("enqueue report")
    REPORT_QUEUE.enqueue(report)
    report_payload = report.to_dict()
    report_payload["event_id"] = report_payload["id"]
    return {"queued": True, "report": report_payload}


@app.post("/api/archive")
def archive_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Archive one active event and track it in history."""
    event_id = int(payload.get("event_id"))
    if event_id not in REPORT_PROCESSOR.active_events:
        raise KeyError(f"event {event_id} is not active")
    _record_undo("archive event")
    event = REPORT_PROCESSOR.archive(event_id)
    return {
        "archived": True,
        "event_id": event_id,
        "event": event.to_dict(),
        "history": _serialize_history(),
    }


@app.post("/api/archive/branch")
def archive_branch() -> dict[str, Any]:
    """Archive the largest eligible low-priority old subtree."""
    _record_undo("archive eligible branch")
    result = REPORT_PROCESSOR.archive_branch(
        clock=datetime.now(timezone.utc),
        age_hours=SCENARIO.archive_age_hours,
    )
    return {
        "archived": bool(result["archived"]),
        "root_id": result["root_id"],
        "event_ids": [event.event_id for event in result["archived"]],
        "reason": result["reason"],
        "state": _snapshot_state(),
    }


@app.post("/api/events/{event_id}/correct")
def correct_event(event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Apply a correction to an active event and return the new snapshot."""
    changes: dict[str, object] = {}
    field_map = {
        "magnitude": "magnitude_tenths",
        "depth_km": "depth_tenths",
        "x_km": "x_tenths",
        "y_km": "y_tenths",
    }
    for source, target in field_map.items():
        if source in payload:
            value = float(payload[source])
            changes[target] = EventKey.to_tenths(value)
    if "populated_zone" in payload:
        changes["populated_zone"] = bool(payload["populated_zone"])

    try:
        _record_undo("correct event")
        event = REPORT_PROCESSOR.correct(event_id, changes)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {"corrected": True, "event": event.to_dict(), "state": _snapshot_state()}


@app.post("/api/events/{event_id}/delete")
def delete_event(event_id: int) -> dict[str, Any]:
    """Delete an active event and expose the updated live state."""
    try:
        _record_undo("delete event")
        event = REPORT_PROCESSOR.delete(event_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"deleted": True, "event_id": event.event_id, "state": _snapshot_state()}


@app.post("/api/events/{event_id}/review")
def review_event(event_id: int) -> dict[str, Any]:
    _record_undo("mark event reviewed")
    try:
        event = REPORT_PROCESSOR.mark_reviewed(event_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return {"reviewed": True, "event": event.to_dict(), "state": _snapshot_state()}


@app.get("/api/audit")
def audit_state() -> dict[str, object]:
    return REPORT_PROCESSOR.audit_report()


@app.post("/api/recover")
def recover_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Recover an archived event back into the active catalog."""
    event_id = int(payload.get("event_id"))
    if event_id not in REPORT_PROCESSOR.archived_events:
        raise KeyError(f"event {event_id} is not archived")
    _record_undo("recover archived event")
    event = REPORT_PROCESSOR.recover(event_id)
    return {
        "recovered": True,
        "event_id": event_id,
        "event": event.to_dict(),
        "history": _serialize_history(),
    }


@app.post("/api/undo")
def undo() -> dict[str, Any]:
    """Restore the complete state captured before the latest action."""
    if len(UNDO_STACK) == 0:
        raise HTTPException(status_code=409, detail="no actions to undo")
    snapshot = UNDO_STACK.pop()
    _hydrate_from_snapshot(snapshot.state)
    return {"undone": True, "label": snapshot.label, "state": _snapshot_state()}


@app.post("/api/versions/{name}")
def save_version(name: str) -> dict[str, Any]:
    """Save a named operational version in memory and on disk when requested."""
    normalized = name.strip()
    if not normalized or not re.fullmatch(r"[A-Za-z0-9_-]+", normalized):
        raise HTTPException(status_code=400, detail="version name is required")
    state = deepcopy(_snapshot_state())
    VERSIONS[normalized] = state
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    PersistenceService().export(VERSION_DIR / f"{normalized}.json", state)
    return {"saved": True, "name": normalized}


@app.get("/api/versions")
def list_versions() -> dict[str, Any]:
    VERSION_DIR.mkdir(parents=True, exist_ok=True)
    disk_versions = {
        path.stem for path in VERSION_DIR.glob("*.json") if path.is_file()
    }
    return {"versions": sorted(set(VERSIONS) | disk_versions)}


@app.post("/api/versions/{name}/restore")
def restore_version(name: str) -> dict[str, Any]:
    """Restore a named version as one undoable action."""
    if not re.fullmatch(r"[A-Za-z0-9_-]+", name):
        raise HTTPException(status_code=400, detail="invalid version name")
    if name not in VERSIONS:
        version_path = VERSION_DIR / f"{name}.json"
        if not version_path.exists():
            raise HTTPException(status_code=404, detail="version not found")
        VERSIONS[name] = PersistenceService().load(version_path)
    _record_undo("restore version")
    _hydrate_from_snapshot(deepcopy(VERSIONS[name]))
    return {"restored": True, "name": name, "state": _snapshot_state()}


@app.get("/api/queries/expensive")
def expensive_events() -> dict[str, Any]:
    entries = REPORT_PROCESSOR.query_expensive_access(SCENARIO.access_depth_limit)
    return {
        "limit": SCENARIO.access_depth_limit,
        "events": [
            {
                **entry["event"].to_dict(),
                "node_depth": entry["depth"],
                "nodes_visited": entry["visited"],
            }
            for entry in entries
        ],
    }


@app.get("/api/queries/top-pending")
def top_pending(limit: int = 5) -> dict[str, Any]:
    if limit < 1:
        raise HTTPException(status_code=400, detail="limit must be positive")
    events = [
        node.event
        for node in REPORT_PROCESSOR.tree.reverse_inorder()
        if node.event.status.value == "pending"
    ][:limit]
    return {"limit": limit, "events": [event.to_dict() for event in events]}


@app.post("/api/persist")
def persist(payload: dict[str, Any]) -> dict[str, Any]:
    """Persist the supplied state to disk."""
    path = payload.get("path", str(DEFAULT_STATE_PATH))
    state = payload.get("state", _snapshot_state())
    if not isinstance(state, dict):
        raise ValueError("state must be a JSON object")
    state.setdefault("mode", SCENARIO.mode)
    state.setdefault("clock", SCENARIO.clock)
    state["events"] = _serialize_events()
    state["queue"] = _serialize_queue()
    state["history"] = _serialize_history()
    state["metrics"] = {
        **state.get("metrics", {}),
        **_metrics_payload(),
        "pending": len(_serialize_queue()),
    }
    state["scenario"] = _scenario_payload()
    state["avl"] = REPORT_PROCESSOR.tree.export_to_dict()
    state["bst"] = REPORT_PROCESSOR.bst_export()
    state["associations"] = _association_payload()["associations"]
    state["association_count"] = _association_payload()["count"]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    persistence = PersistenceService()
    persistence.export(path, state)
    return {"saved": True, "path": str(path), "state": state}


@app.post("/api/load-json")
def load_json_document(payload: dict[str, Any]) -> dict[str, Any]:
    """Load a JSON document supplied directly by the browser."""
    document = payload.get("document")
    if not isinstance(document, dict):
        raise ValueError("document must be a JSON object")
    _record_undo("load JSON document")
    _hydrate_from_snapshot(document, load_mode=str(payload.get("mode", "topology")))
    return {"loaded": True, "state": _snapshot_state()}


@app.post("/api/load")
def load_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Load a previously persisted scenario state from disk."""
    path = payload.get("path", str(DEFAULT_STATE_PATH))
    persistence = PersistenceService()
    state = persistence.load(path)
    _record_undo("load saved JSON")
    _hydrate_from_snapshot(state, load_mode=str(payload.get("mode", "topology")))
    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    state["mode"] = SCENARIO.mode
    state["clock"] = SCENARIO.clock
    state["events"] = _serialize_events()
    state["queue"] = _serialize_queue()
    state["history"] = _serialize_history()
    state["metrics"] = {
        **state.get("metrics", {}),
        **_metrics_payload(),
        "pending": len(_serialize_queue()),
    }
    state["scenario"] = _scenario_payload()
    state["avl"] = REPORT_PROCESSOR.tree.export_to_dict()
    state["bst"] = REPORT_PROCESSOR.bst_export()
    state["associations"] = _association_payload()["associations"]
    state["association_count"] = _association_payload()["count"]
    return {"loaded": True, "path": str(path), "state": state}