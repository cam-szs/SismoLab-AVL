"""HTTP boundary for the React client and persisted scenario state."""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from domain.event import Event
from domain.queue_fifo import ReportQueue
from domain.report import Report
from domain.scenario import Scenario
from services.archive_service import ArchiveService
from services.association_service import AssociationService
from services.persistence_service import PersistenceService
from services.report_processor import ReportProcessor


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_STATE_PATH = PROJECT_ROOT / "data" / "scenario_state.json"
SCENARIO = Scenario()
REPORT_QUEUE: ReportQueue[Report] = ReportQueue()
REPORT_PROCESSOR = ReportProcessor()
ARCHIVE_SERVICE = ArchiveService()
ASSOCIATION_SERVICE = AssociationService()


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
    return {
        "active": len(REPORT_PROCESSOR.active_events),
        "archived": len(REPORT_PROCESSOR.archived_events),
        "pending": queue_count,
        "expensive_access": len(REPORT_PROCESSOR.deleted_ids),
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
        "clock": SCENARIO.clock,
        "events": events_payload,
        "queue": queue_items,
        "history": history_payload,
        "metrics": {
            **_metrics_payload(),
            "pending": len(queue_items),
        },
        "scenario": _scenario_payload(),
        "associations": _association_payload()["associations"],
        "association_count": _association_payload()["count"],
    }


def _hydrate_from_snapshot(payload: dict[str, Any]) -> None:
    if not isinstance(payload, dict):
        raise ValueError("state must be a JSON object")

    global REPORT_QUEUE, REPORT_PROCESSOR

    if isinstance(payload.get("mode"), str):
        SCENARIO.set_mode(payload["mode"])
    if isinstance(payload.get("clock"), int):
        SCENARIO.clock = payload["clock"]
        SCENARIO.values["clock"] = payload["clock"]

    REPORT_QUEUE = ReportQueue()
    for item in payload.get("queue", []):
        REPORT_QUEUE.enqueue(_report_from_dict(item))

    active_events: dict[int, Event] = {}
    for item in payload.get("events", []):
        event = _event_from_dict(item)
        active_events[event.event_id] = event

    archived_events: dict[int, Event] = {}
    for item in payload.get("history", {}).get("archived", []):
        event = _event_from_dict(item)
        archived_events[event.event_id] = event

    deleted_ids: set[int] = set()
    for item in payload.get("history", {}).get("deleted", []):
        if isinstance(item, dict):
            deleted_ids.add(int(item.get("event_id", item.get("id", 0))))
        else:
            deleted_ids.add(int(item))

    REPORT_PROCESSOR = ReportProcessor(
        active_events=active_events,
        archived_events=archived_events,
        deleted_ids=deleted_ids,
    )


def _association_payload() -> dict[str, Any]:
    events = sorted(REPORT_PROCESSOR.active_events.values(), key=lambda event: event.event_id)
    links: list[dict[str, Any]] = []
    for source in events:
        for association in ASSOCIATION_SERVICE.associate(source, events):
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
        "values": SCENARIO.values.copy(),
    }


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
    SCENARIO.set_mode(str(mode))
    return _scenario_payload()


@app.post("/api/scenario/clock")
def advance_scenario_clock(payload: dict[str, Any]) -> dict[str, Any]:
    """Advance the simulation clock by a non-negative integer amount."""
    amount = payload.get("amount", 1)
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
    event = REPORT_PROCESSOR.archive(event_id)
    ARCHIVE_SERVICE.archive(event)
    return {
        "archived": True,
        "event_id": event_id,
        "event": event.to_dict(),
        "history": _serialize_history(),
    }


@app.post("/api/recover")
def recover_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Recover an archived event back into the active catalog."""
    event_id = int(payload.get("event_id"))
    if event_id not in REPORT_PROCESSOR.archived_events:
        raise KeyError(f"event {event_id} is not archived")
    event = REPORT_PROCESSOR.recover(event_id)
    ARCHIVE_SERVICE.recover(event_id)
    return {
        "recovered": True,
        "event_id": event_id,
        "event": event.to_dict(),
        "history": _serialize_history(),
    }


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
    state["associations"] = _association_payload()["associations"]
    state["association_count"] = _association_payload()["count"]
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    persistence = PersistenceService()
    persistence.export(path, state)
    return {"saved": True, "path": str(path), "state": state}


@app.post("/api/load")
def load_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Load a previously persisted scenario state from disk."""
    path = payload.get("path", str(DEFAULT_STATE_PATH))
    persistence = PersistenceService()
    state = persistence.load(path)
    _hydrate_from_snapshot(state)
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
    state["associations"] = _association_payload()["associations"]
    state["association_count"] = _association_payload()["count"]
    return {"loaded": True, "path": str(path), "state": state}