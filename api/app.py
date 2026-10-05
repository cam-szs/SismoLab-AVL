"""HTTP boundary for the React client and persisted scenario state."""

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from copy import deepcopy
import re

from fastapi import FastAPI, Request
from fastapi import HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from domain.event import Event, _to_tenths
from domain.queue_fifo import ReportQueue
from domain.report import Report
from domain.scenario import Scenario
from services.association_service import AssociationService
from services.comparison_service import compare_orders
from services.persistence_service import PersistenceService
from services.report_processor import ReportProcessor
from domain.undo_stack import Snapshot, UndoStack
from domain.node import Node


PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCENARIO = Scenario()
REPORT_QUEUE: ReportQueue[Report] = ReportQueue()
REPORT_PROCESSOR = ReportProcessor(
    populated_zone=lambda report: SCENARIO.is_populated(report.x_km, report.y_km)
)
ASSOCIATION_SERVICE = AssociationService()
UNDO_STACK: UndoStack[Snapshot] = UndoStack()
# Append-only log of user actions (sections 6 and 14). It records history, so
# it is not part of the restorable state: undoing adds an entry instead of
# erasing the action it reverts.
ACTION_LOG: list[dict[str, Any]] = []
ACTION_LOG_LIMIT = 300
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
    active = REPORT_PROCESSOR.active_events.values()
    return {
        "active": len(REPORT_PROCESSOR.active_events),
        "archived": len(REPORT_PROCESSOR.archived_events),
        "deleted": len(REPORT_PROCESSOR.deleted_ids),
        "pending": queue_count,
        "pending_attention": sum(1 for event in active if event.status.value == "pending"),
        "by_priority": {
            str(priority): sum(1 for event in active if event.priority == priority)
            for priority in (1, 2, 3)
        },
        "expensive_access": len(
            REPORT_PROCESSOR.query_expensive_access(SCENARIO.access_depth_limit)
        ),
        "avl": tree_metrics,
        "bst": REPORT_PROCESSOR.bst_metrics(),
        "processing": REPORT_PROCESSOR.stats.copy(),
        "indicators": REPORT_PROCESSOR.indicators(),
    }


def _traversals_payload() -> dict[str, list[int]]:
    """AVL traversals as event-id sequences (section 14 indicators)."""
    tree = REPORT_PROCESSOR.tree
    return {
        "inorder": [node.event_id for node in tree.inorder()],
        "preorder": [node.event_id for node in tree.preorder()],
        "postorder": [node.event_id for node in tree.postorder()],
        "level_order": [node.event_id for node in tree.level_order()],
    }


def _event_from_dict(data: dict[str, Any]) -> Event:
    payload = dict(data)
    if "event_id" not in payload and "id" in payload:
        payload["event_id"] = payload["id"]
    if "id" not in payload and "event_id" in payload:
        payload["id"] = payload["event_id"]
    return Event.from_dict(payload)


def _parse_utc(raw: Any, name: str = "occurred_at") -> datetime:
    """Parse an ISO 8601 timestamp; naive values are interpreted as UTC."""
    try:
        parsed = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError(f"{name} must be an ISO 8601 date-time") from error
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _number(payload: dict[str, Any], name: str) -> float:
    """Read a required finite number from a request body."""
    if name not in payload or payload[name] in (None, ""):
        raise ValueError(f"{name} is required")
    value = payload[name]
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a number") from error


def _report_from_dict(data: dict[str, Any]) -> Report:
    payload = dict(data)
    occurred = payload.get("occurred_at")
    if occurred is None:
        occurred = SCENARIO.simulation_time
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
        "simulation_time": SCENARIO.simulation_time.isoformat().replace("+00:00", "Z"),
        "events": events_payload,
        "queue": queue_items,
        "history": history_payload,
        "metrics": {
            **_metrics_payload(),
            "pending": len(queue_items),
        },
        "avl": REPORT_PROCESSOR.tree.export_to_dict(),
        "bst": REPORT_PROCESSOR.bst_export(),
        "counters": REPORT_PROCESSOR.counters(),
        "traversals": _traversals_payload(),
        "scenario": _scenario_payload(),
        "associations": _association_payload()["associations"],
        "association_count": _association_payload()["count"],
    }


def _insertion_event(data: dict[str, Any], scenario: Scenario) -> Event:
    """Parse one event of an insertion-mode file.

    Only physical data is required; revision defaults to 1, the populated
    flag is derived from the zones and an optional stored priority must
    match the computed one.
    """
    occurred_raw = data.get("occurred_at")
    if occurred_raw in (None, ""):
        raise ValueError(f"event {data.get('id', data.get('event_id'))}: occurred_at is required")
    epicenter = data.get("epicenter", {})
    x_km = epicenter.get("x", data.get("x_km")) if isinstance(epicenter, dict) else None
    y_km = epicenter.get("y", data.get("y_km")) if isinstance(epicenter, dict) else None
    event_id = data.get("id", data.get("event_id"))
    if isinstance(event_id, bool) or not isinstance(event_id, int):
        raise ValueError("event id must be an integer")
    stations = data.get("stations") or ([data["station"]] if data.get("station") else [])
    if not stations:
        raise ValueError(f"event {data.get('id', data.get('event_id'))}: station is required")
    report = Report.create(
        event_id=event_id,
        magnitude=_number(data, "magnitude"),
        depth_km=_number(data, "depth_km"),
        x_km=_number({"x": x_km}, "x"),
        y_km=_number({"y": y_km}, "y"),
        occurred_at=_parse_utc(occurred_raw),
        station=str(stations[0]),
        revision=int(data.get("revision", 1)),
    )
    event = report.to_event(populated_zone=scenario.is_populated(report.x_km, report.y_km))
    event = replace(event, stations=frozenset(str(item) for item in stations))
    if "priority" in data and data["priority"] != event.priority:
        raise ValueError(
            f"event {event.event_id}: stored priority {data['priority']} "
            f"does not match computed {event.priority}"
        )
    return event


def _build_topology(payload: Any, events: dict[int, Event], label: str) -> tuple[Node | None, int]:
    """Rebuild a stored tree exactly as saved (no reinsertion).

    Every node must reference a known active event, appear once, carry the
    event's current key and a correct stored height. Order and balance
    factors were already checked by PersistenceService.validate_topology.
    """
    seen: set[int] = set()

    def build(node_payload: Any) -> Node | None:
        if node_payload is None:
            return None
        if not isinstance(node_payload, dict) or not isinstance(node_payload.get("key"), dict):
            raise ValueError(f"{label}: invalid node")
        key_payload = node_payload["key"]
        event_id = int(key_payload["event_id"])
        if event_id in seen:
            raise ValueError(f"{label}: event {event_id} appears more than once")
        seen.add(event_id)
        if event_id not in events:
            raise ValueError(f"{label}: references unknown active event {event_id}")
        event = events[event_id]
        stored_key = (int(key_payload["priority"]), int(key_payload["magnitude_tenths"]), event_id)
        if stored_key != (event.key.priority, event.key.magnitude_tenths, event_id):
            raise ValueError(f"{label}: stored key does not match event {event_id}")
        node = Node(event.key, event)
        node.left = build(node_payload.get("izquierdo"))
        node.right = build(node_payload.get("derecho"))
        node.update_height()
        if node.height != int(node_payload.get("height", node.height)):
            raise ValueError(f"{label}: invalid stored height for event {event_id}")
        return node

    root = build(payload)
    if seen != set(events):
        missing = sorted(set(events) - seen)
        raise ValueError(f"{label}: must contain every active event exactly once (missing {missing})")
    return root, len(seen)


def _hydrate_from_snapshot(payload: dict[str, Any], *, load_mode: str = "topology") -> None:
    """Validate a whole scenario and replace the live one only if all checks pass."""
    try:
        _hydrate(payload, load_mode=load_mode)
    except (KeyError, TypeError, AttributeError) as error:
        raise ValueError(f"malformed scenario file: {error!r}") from error


def _hydrate(payload: dict[str, Any], *, load_mode: str) -> None:
    if not isinstance(payload, dict):
        raise ValueError("state must be a JSON object")
    if load_mode not in {"topology", "insertions"}:
        raise ValueError("load mode must be 'topology' or 'insertions'")
    if load_mode == "topology":
        PersistenceService.validate_topology(payload.get("avl"))
        if payload.get("bst") is not None:
            PersistenceService.validate_topology(payload.get("bst"))

    global REPORT_QUEUE, REPORT_PROCESSOR

    candidate_mode = payload.get("mode", SCENARIO.mode)
    if not isinstance(candidate_mode, str):
        raise ValueError("mode must be a string")
    candidate_mode = candidate_mode.strip().lower()
    if candidate_mode not in {"normal", "stress", "w", "t"}:
        raise ValueError("mode must be one of normal or stress")
    candidate_clock = payload.get("clock", SCENARIO.clock)
    if not isinstance(candidate_clock, int) or isinstance(candidate_clock, bool) or candidate_clock < 0:
        raise ValueError("clock must be a non-negative integer")
    simulation_time_raw = payload.get(
        "simulation_time",
        payload.get("scenario", {}).get("simulation_time"),
    )
    if simulation_time_raw is None:
        candidate_time = SCENARIO.simulation_time
    else:
        candidate_time = datetime.fromisoformat(
            str(simulation_time_raw).replace("Z", "+00:00")
        ).astimezone(timezone.utc).replace(microsecond=0)
    parameters = payload.get("parameters", payload.get("scenario", {}).get("parameters", {}))
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    candidate_scenario = Scenario()
    zones_payload = payload.get("zones", payload.get("scenario", {}).get("zones"))
    if zones_payload is not None:
        candidate_scenario.zones = Scenario.zones_from_payload(zones_payload)
    stations_payload = payload.get("stations", payload.get("scenario", {}).get("stations"))
    if stations_payload is not None:
        candidate_scenario.stations = Scenario.stations_from_payload(stations_payload)
    candidate_scenario.set_mode(candidate_mode)
    candidate_scenario.set_parameters(
        W=parameters.get("W"),
        R=parameters.get("R"),
        L=parameters.get("L"),
        T=parameters.get("T"),
    )
    candidate_scenario.clock = candidate_clock
    candidate_scenario.simulation_time = candidate_time

    candidate_queue = ReportQueue()
    queue_payload = payload.get("queue", [])
    if not isinstance(queue_payload, list):
        raise ValueError("queue must be an array")
    for item in queue_payload:
        if not isinstance(item, dict):
            raise ValueError("queue entries must be objects")
        report = _report_from_dict(item)
        if report.occurred_at > candidate_time:
            raise ValueError("report occurrence cannot be after simulation time")
        _require_station(report.station, candidate_scenario.stations)
        candidate_queue.enqueue(report)

    active_events: dict[int, Event] = {}
    events_payload = payload.get("events", [])
    if not isinstance(events_payload, list):
        raise ValueError("events must be an array")
    for item in events_payload:
        if not isinstance(item, dict):
            raise ValueError("event entries must be objects")
        event = (
            _insertion_event(item, candidate_scenario)
            if load_mode == "insertions"
            else _event_from_dict(item)
        )
        if event.occurred_at > candidate_time:
            raise ValueError(f"event {event.event_id}: occurrence cannot be after simulation time")
        if event.event_id in active_events:
            raise ValueError(f"duplicate event {event.event_id} in the file")
        active_events[event.event_id] = event

    archived_events: dict[int, Event] = {}
    history_payload = payload.get("history", {})
    if not isinstance(history_payload, dict):
        raise ValueError("history must be an object")
    archived_payload = history_payload.get("archived", [])
    if not isinstance(archived_payload, list):
        raise ValueError("archived history must be an array")
    for item in archived_payload:
        if not isinstance(item, dict):
            raise ValueError("archived entries must be objects")
        event = _event_from_dict(item)
        if event.occurred_at > candidate_time:
            raise ValueError("archived occurrence cannot be after simulation time")
        if event.event_id in active_events or event.event_id in archived_events:
            raise ValueError(f"duplicate historical event {event.event_id}")
        archived_events[event.event_id] = event

    deleted_ids: set[int] = set()
    deleted_payload = history_payload.get("deleted", [])
    if not isinstance(deleted_payload, list):
        raise ValueError("deleted history must be an array")
    for item in deleted_payload:
        if isinstance(item, dict):
            deleted_ids.add(int(item.get("event_id", item.get("id", 0))))
        else:
            deleted_ids.add(int(item))
    overlap = deleted_ids & (set(active_events) | set(archived_events))
    if overlap:
        raise ValueError(f"identities cannot be active and deleted: {sorted(overlap)}")
    # The stored populated flag is derived data: it must match the zones.
    for event in [*active_events.values(), *archived_events.values()]:
        for station in event.stations:
            _require_station(station, candidate_scenario.stations)
        expected = candidate_scenario.is_populated(event.x_km, event.y_km)
        if event.populated_zone != expected:
            raise ValueError(
                f"event {event.event_id}: stored populated_zone {event.populated_zone} "
                f"does not match the zones ({expected})"
            )

    # Insertion loads always balance (section 12); the scenario mode applies
    # to the operations performed after the load.
    candidate_processor = ReportProcessor(
        active_events=active_events,
        archived_events=archived_events,
        deleted_ids=deleted_ids,
        populated_zone=lambda item: candidate_scenario.is_populated(item.x_km, item.y_km),
        stress_mode=candidate_scenario.stress_mode if load_mode == "topology" else False,
    )
    candidate_processor.tree.stress_mode = candidate_scenario.stress_mode
    if load_mode == "topology":
        if payload.get("avl") is not None or active_events:
            root, size = _build_topology(payload.get("avl"), active_events, "AVL topology")
            candidate_processor.tree.root, candidate_processor.tree.size = root, size
        if payload.get("bst") is not None:
            root, size = _build_topology(payload.get("bst"), active_events, "BST topology")
            candidate_processor.bst.root, candidate_processor.bst.size = root, size
        if "counters" in payload:
            candidate_processor.restore_counters(payload["counters"])
    audit = candidate_processor.audit_report()
    if audit["metadata_errors"]:
        raise ValueError("; ".join(audit["metadata_errors"]))
    if not candidate_scenario.stress_mode and audit["unbalanced_events"]:
        raise ValueError(
            "an unbalanced topology can only be loaded in stress mode; unbalanced events: "
            f"{audit['unbalanced_events']}"
        )

    candidate_scenario.values["clock"] = candidate_clock
    candidate_scenario.values["simulation_time"] = candidate_time.isoformat().replace("+00:00", "Z")
    SCENARIO.zones = candidate_scenario.zones
    SCENARIO.stations = candidate_scenario.stations
    SCENARIO.mode = candidate_scenario.mode
    SCENARIO.clock = candidate_scenario.clock
    SCENARIO.simulation_time = candidate_scenario.simulation_time
    SCENARIO.values = candidate_scenario.values
    SCENARIO.association_window_hours = candidate_scenario.association_window_hours
    SCENARIO.association_distance_km = candidate_scenario.association_distance_km
    SCENARIO.access_depth_limit = candidate_scenario.access_depth_limit
    SCENARIO.archive_age_hours = candidate_scenario.archive_age_hours
    REPORT_QUEUE = candidate_queue
    REPORT_PROCESSOR = candidate_processor


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
        "simulation_time": SCENARIO.simulation_time.isoformat().replace("+00:00", "Z"),
        "parameters": SCENARIO.parameters,
        "values": SCENARIO.values.copy(),
        "zones": SCENARIO.zones_payload(),
        "stations": SCENARIO.stations_payload(),
    }


def _record_undo(label: str) -> None:
    """Capture a complete immutable state before a user action."""
    UNDO_STACK.push(_capture_undo(label))


def _capture_undo(label: str) -> Snapshot:
    """Capture the state before an action that may still be rejected.

    The snapshot is pushed with UNDO_STACK.push only after the action
    succeeds, so a rejected action never leaves an empty undo step.
    """
    return Snapshot(label=label, state=deepcopy(_snapshot_state()))


def _require_path(payload: dict[str, Any]) -> str:
    """Server-side files are only read or written at a path the user chose."""
    path = payload.get("path")
    if not isinstance(path, str) or not path.strip():
        raise ValueError("path is required: the file must be chosen by the user")
    return path


def _require_station(code: str, stations: dict[str, Any] | None = None) -> None:
    """Stations are scenario parameters and fixed during a run (section 1)."""
    known = SCENARIO.stations if stations is None else stations
    if code not in known:
        raise ValueError(f"unknown station {code!r}; scenario stations: {', '.join(sorted(known))}")


def _counter_totals() -> dict[str, int]:
    counters = REPORT_PROCESSOR.counters()
    return {
        **counters["stats"],
        **counters["rotations"],
        "active": len(REPORT_PROCESSOR.active_events),
        "archived": len(REPORT_PROCESSOR.archived_events),
        "queue": len(REPORT_QUEUE),
    }


def _log_action(label: str, before: dict[str, int], detail: str = "") -> None:
    """Record an action with the counters it changed, so its metrics can be explained."""
    after = _counter_totals()
    delta = {
        name: after[name] - before.get(name, 0)
        for name in after
        if after[name] != before.get(name, 0)
    }
    sequence = ACTION_LOG[-1]["sequence"] + 1 if ACTION_LOG else 1
    ACTION_LOG.append({
        "sequence": sequence,
        "label": label,
        "detail": detail,
        "simulation_time": SCENARIO.simulation_time.isoformat().replace("+00:00", "Z"),
        "mode": SCENARIO.mode,
        "delta": delta,
    })
    del ACTION_LOG[:-ACTION_LOG_LIMIT]


def _public_state() -> dict[str, Any]:
    """Live state for the UI: the restorable snapshot plus the action log."""
    return {**_snapshot_state(), "actions": list(reversed(ACTION_LOG))}


def _event_location(event_id: int) -> dict[str, Any]:
    """Structural data of an active event: depth, height, balance, access cost."""
    node, visited = REPORT_PROCESSOR.locate(event_id)
    if node is None:
        return {}
    depth = visited - 1
    return {
        "node_depth": depth,
        "nodes_visited": visited,
        "height": node.height,
        "balance_factor": node.balance_factor(),
        "expensive_access": node.event.priority == 3 and depth > SCENARIO.access_depth_limit,
        "left_id": node.left.event_id if node.left else None,
        "right_id": node.right.event_id if node.right else None,
    }


def _event_associations(event: Event) -> dict[str, Any]:
    """Candidates, chosen reference and referencing events for one event.

    Active and archived events are considered, deleted ones are not. Cost:
    O(n) for the candidates and O(n^2) for "referenced by", because every
    other event has to evaluate its own candidates.
    """
    pool = [*REPORT_PROCESSOR.active_events.values(), *REPORT_PROCESSOR.archived_events.values()]
    limits = {
        "max_hours": SCENARIO.association_window_hours,
        "max_distance_km": SCENARIO.association_distance_km,
    }

    def describe(association: Any, other_id: int) -> dict[str, Any]:
        return {
            "event_id": other_id,
            "status": REPORT_PROCESSOR.status_of(other_id),
            "time_hours": round(association.time_hours, 2),
            "distance_km": round(association.distance_km, 2),
            "is_reference": association.is_reference,
        }

    candidates = [
        describe(item, item.reference_id)
        for item in ASSOCIATION_SERVICE.associate(event, pool, **limits)
    ]
    referenced_by = []
    for other in pool:
        if other.event_id == event.event_id:
            continue
        for item in ASSOCIATION_SERVICE.associate(other, pool, **limits):
            if item.is_reference and item.reference_id == event.event_id:
                referenced_by.append(describe(item, other.event_id))
    reference = next((item["event_id"] for item in candidates if item["is_reference"]), None)
    return {"candidates": candidates, "reference_id": reference, "referenced_by": referenced_by}


@app.get("/api/health")
def health() -> dict[str, str]:
    """Return a cheap endpoint used to verify the local connection."""
    return {"status": "ok"}


@app.get("/api/state")
def state() -> dict[str, Any]:
    """Return the current live state from memory, with the action log."""
    return _public_state()


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
    snapshot = _capture_undo("change execution mode")
    before = _counter_totals()
    was_stress = SCENARIO.stress_mode
    SCENARIO.set_mode(str(mode))
    UNDO_STACK.push(snapshot)
    detail = f"mode {SCENARIO.mode}"
    if was_stress and not SCENARIO.stress_mode:
        # Leaving stress mode runs the global recovery; report its cost.
        recovery = REPORT_PROCESSOR.recover_balance()
        REPORT_PROCESSOR.set_stress_mode(False, recover=False)
        detail += (
            f"; global recovery applied {len(recovery['applied_cases'])} case(s) to "
            f"{len(recovery['unbalanced_before'])} unbalanced node(s)"
        )
    else:
        REPORT_PROCESSOR.set_stress_mode(SCENARIO.stress_mode, recover=False)
    _log_action("change execution mode", before, detail)
    return _public_state()


@app.post("/api/scenario/parameters")
def set_scenario_parameters(payload: dict[str, Any]) -> dict[str, Any]:
    """Update W/R/L/T and return the recalculated live state."""
    snapshot = _capture_undo("change scenario parameters")
    before = _counter_totals()
    previous = SCENARIO.parameters
    SCENARIO.set_parameters(
        W=payload.get("W"),
        R=payload.get("R"),
        L=payload.get("L"),
        T=payload.get("T"),
    )
    UNDO_STACK.push(snapshot)
    changed = [
        f"{name} {previous[name]:g} -> {value:g}"
        for name, value in SCENARIO.parameters.items()
        if value != previous[name]
    ]
    _log_action("change scenario parameters", before, ", ".join(changed) or "no change")
    return _public_state()


@app.post("/api/scenario/recover")
def recover_scenario_balance() -> dict[str, Any]:
    """Recover the global AVL balance after a stress burst."""
    _record_undo("recover AVL balance")
    before = _counter_totals()
    metrics = REPORT_PROCESSOR.recover_balance()
    audit = REPORT_PROCESSOR.audit_report()
    if not audit["balanced"]:
        # Never reached in practice; normal mode is only entered after a clean audit.
        raise ValueError(f"recovery did not pass the audit: {audit}")
    if SCENARIO.stress_mode:
        SCENARIO.set_mode("normal")
    REPORT_PROCESSOR.set_stress_mode(False, recover=False)
    _log_action(
        "global AVL recovery",
        before,
        f"{len(metrics['unbalanced_before'])} unbalanced node(s), "
        f"{len(metrics['applied_cases'])} case(s) applied; audit passed",
    )
    return {
        "recovered": True,
        "mode": SCENARIO.mode,
        "metrics": metrics,
        "audit": audit,
        "state": _public_state(),
    }


@app.post("/api/scenario/clock")
def advance_scenario_clock(payload: dict[str, Any]) -> dict[str, Any]:
    """Advance the simulation clock by a non-negative integer amount."""
    amount = payload.get("amount", 1)
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError("amount must be a non-negative integer")
    snapshot = _capture_undo("advance simulation clock")
    before = _counter_totals()
    SCENARIO.advance_clock(amount)
    UNDO_STACK.push(snapshot)
    _log_action("advance simulation clock", before, f"+{amount} h -> {_scenario_payload()['simulation_time']}")
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
    before = _counter_totals()
    result = REPORT_PROCESSOR.process_next(REPORT_QUEUE)
    rotations = ", ".join(f"{item['case']} at {item['node_id']}" for item in result.rotations)
    _log_action(
        "process queued report",
        before,
        f"{result.report.station} -> event {result.report.event_id} rev {result.report.revision}: "
        f"{result.decision}" + (f"; rotations {rotations}" if rotations else ""),
    )
    serialized = {
        "decision": result.decision,
        "message": result.message,
        "report": result.report.to_dict(),
        "event": result.event.to_dict() if result.event is not None else None,
        "previous_event": result.previous_event.to_dict() if result.previous_event is not None else None,
        "rotations": list(result.rotations),
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
        occurred_at = SCENARIO.simulation_time
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
    if report.occurred_at > SCENARIO.simulation_time:
        raise ValueError("report occurrence cannot be after simulation time")
    _require_station(report.station)
    _record_undo("enqueue report")
    before = _counter_totals()
    REPORT_QUEUE.enqueue(report)
    _log_action(
        "enqueue report", before,
        f"{report.station} -> event {report.event_id} rev {report.revision} (position {len(REPORT_QUEUE)})",
    )
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
    before = _counter_totals()
    event = REPORT_PROCESSOR.archive(event_id)
    _log_action("archive single event", before, f"event {event_id}")
    return {
        "archived": True,
        "event_id": event_id,
        "event": event.to_dict(),
        "history": _serialize_history(),
    }


def _archive_plan_payload(plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "root_id": plan["root_id"],
        "event_ids": [event.event_id for event in plan["events"]],
        "count": len(plan["events"]),
        "eligible_branches": plan["eligible_branches"],
        "alternatives": plan["alternatives"],
        "reason": plan["reason"],
        "age_limit_hours": SCENARIO.archive_age_hours,
    }


@app.get("/api/archive/branch/preview")
def archive_branch_preview() -> dict[str, Any]:
    """Show which branch would be archived, and why, without changing anything."""
    plan = REPORT_PROCESSOR.select_archive_branch(
        clock=SCENARIO.simulation_time,
        age_hours=SCENARIO.archive_age_hours,
    )
    return _archive_plan_payload(plan)


@app.post("/api/archive/branch")
def archive_branch() -> dict[str, Any]:
    """Archive the largest eligible low-priority old subtree as one undoable action."""
    snapshot = _capture_undo("archive eligible branch")
    before = _counter_totals()
    result = REPORT_PROCESSOR.archive_branch(
        clock=SCENARIO.simulation_time,
        age_hours=SCENARIO.archive_age_hours,
    )
    if result["archived"]:
        UNDO_STACK.push(snapshot)
        _log_action(
            "archive eligible branch", before,
            f"root {result['root_id']}: {', '.join(str(event.event_id) for event in result['archived'])}",
        )
    return {
        **_archive_plan_payload(result),
        "archived": bool(result["archived"]),
        "rotations": result["rotations"],
        "state": _public_state(),
    }


@app.post("/api/events")
def create_event(payload: dict[str, Any]) -> dict[str, Any]:
    """Manually create an event (section 6) as one undoable action.

    Ranges, one-decimal precision, the occurrence time against the simulation
    clock and the uniqueness of the id (active, archived or deleted) are all
    validated before any structure is modified.
    """
    if "event_id" not in payload:
        raise ValueError("event_id is required")
    event_id = payload["event_id"]
    if isinstance(event_id, bool) or not isinstance(event_id, int):
        raise ValueError("event_id must be an integer")
    occurred_at = (
        _parse_utc(payload["occurred_at"])
        if payload.get("occurred_at") not in (None, "")
        else SCENARIO.simulation_time
    )
    if occurred_at > SCENARIO.simulation_time:
        raise ValueError("occurrence time cannot be after the simulation clock")
    report = Report.create(
        event_id=event_id,
        magnitude=_number(payload, "magnitude"),
        depth_km=_number(payload, "depth_km"),
        x_km=_number(payload, "x_km"),
        y_km=_number(payload, "y_km"),
        occurred_at=occurred_at,
        station=str(payload.get("station", "")),
        revision=1,
    )
    _require_station(report.station)
    snapshot = _capture_undo("create event")
    before = _counter_totals()
    event = REPORT_PROCESSOR.create(report)
    UNDO_STACK.push(snapshot)
    _log_action("create event", before, f"event {event.event_id} key {event.key}")
    return {"created": True, "event": event.to_dict(), "state": _public_state()}


@app.get("/api/events/{event_id}")
def lookup_event(event_id: int) -> dict[str, Any]:
    """Locate an event by identifier even if its priority or magnitude changed."""
    status = REPORT_PROCESSOR.status_of(event_id)
    result: dict[str, Any] = {"event_id": event_id, "status": status}
    if status == "unknown":
        raise KeyError(f"event {event_id} does not exist")
    if status == "deleted":
        return result
    event = (
        REPORT_PROCESSOR.active_events.get(event_id)
        or REPORT_PROCESSOR.archived_events[event_id]
    )
    result["event"] = event.to_dict()
    result["key"] = str(event.key)
    result["associations"] = _event_associations(event)
    if status == "active":
        result["location"] = _event_location(event_id)
        result["depth_limit"] = SCENARIO.access_depth_limit
    return result


@app.post("/api/events/{event_id}/correct")
def correct_event(event_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    """Apply a correction to an active event and return the new snapshot."""
    if "populated_zone" in payload:
        raise ValueError("populated zone is derived from the epicenter and cannot be set")
    changes: dict[str, object] = {}
    field_map = {
        "magnitude": "magnitude_tenths",
        "depth_km": "depth_tenths",
        "x_km": "x_tenths",
        "y_km": "y_tenths",
    }
    for source, target in field_map.items():
        if source in payload:
            changes[target] = _to_tenths(_number(payload, source), source)
    if payload.get("occurred_at") not in (None, ""):
        occurred_at = _parse_utc(payload["occurred_at"])
        if occurred_at > SCENARIO.simulation_time:
            raise ValueError("occurrence time cannot be after the simulation clock")
        changes["occurred_at"] = occurred_at

    snapshot = _capture_undo("correct event")
    before = _counter_totals()
    previous = REPORT_PROCESSOR.active_events.get(event_id)
    try:
        event = REPORT_PROCESSOR.correct(event_id, changes)
    except (KeyError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    UNDO_STACK.push(snapshot)
    _log_action(
        "correct event", before,
        f"event {event_id} rev {event.revision}: key {previous.key} -> {event.key}",
    )
    return {"corrected": True, "event": event.to_dict(), "state": _public_state()}


@app.post("/api/events/{event_id}/delete")
def delete_event(event_id: int) -> dict[str, Any]:
    """Delete an active event and expose the updated live state."""
    snapshot = _capture_undo("delete event")
    before = _counter_totals()
    try:
        event = REPORT_PROCESSOR.delete(event_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    UNDO_STACK.push(snapshot)
    _log_action("delete event", before, f"event {event_id} retired")
    return {"deleted": True, "event_id": event.event_id, "state": _public_state()}


@app.post("/api/events/{event_id}/review")
def review_event(event_id: int) -> dict[str, Any]:
    snapshot = _capture_undo("mark event reviewed")
    before = _counter_totals()
    try:
        event = REPORT_PROCESSOR.mark_reviewed(event_id)
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    UNDO_STACK.push(snapshot)
    _log_action("mark event reviewed", before, f"event {event_id}; key unchanged")
    return {"reviewed": True, "event": event.to_dict(), "state": _public_state()}


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
    before = _counter_totals()
    event = REPORT_PROCESSOR.recover(event_id)
    _log_action("recover archived event", before, f"event {event_id}")
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
    before = _counter_totals()
    snapshot = UNDO_STACK.pop()
    _hydrate_from_snapshot(snapshot.state)
    _log_action("undo", before, f"reverted: {snapshot.label}")
    return {"undone": True, "label": snapshot.label, "state": _public_state()}


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
    _log_action("save version", _counter_totals(), f"version {normalized}")
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
    snapshot = _capture_undo("restore version")
    before = _counter_totals()
    _hydrate_from_snapshot(deepcopy(VERSIONS[name]))
    UNDO_STACK.push(snapshot)
    _log_action("restore version", before, f"version {name}")
    return {"restored": True, "name": name, "state": _public_state()}


@app.get("/api/compare")
def compare_avl_bst() -> dict[str, Any]:
    """Compare AVL and BST for the active events under several insertion orders.

    The live trees are not touched: fresh trees are built for each order.
    "given" uses the order in which the events entered the catalog.
    """
    events = list(REPORT_PROCESSOR.active_events.values())
    return {"size": len(events), "orders": compare_orders(events)}


@app.get("/api/queries/expensive")
def expensive_events() -> dict[str, Any]:
    """High-priority events deeper than L. The depth of every node is
    computed with one breadth-first pass, so all n nodes are examined."""
    entries = REPORT_PROCESSOR.query_expensive_access(SCENARIO.access_depth_limit)
    return {
        "limit": SCENARIO.access_depth_limit,
        "nodes_examined": REPORT_PROCESSOR.tree.size,
        "events": [
            {
                **entry["event"].to_dict(),
                "node_depth": entry["depth"],
                "nodes_visited": entry["visited"],
            }
            for entry in sorted(entries, key=lambda item: item["event"].key, reverse=True)
        ],
    }


@app.get("/api/queries/top-pending")
def top_pending(limit: int = 5) -> dict[str, Any]:
    result = REPORT_PROCESSOR.query_top_pending(limit)
    return {
        "limit": limit,
        "nodes_examined": result["nodes_examined"],
        "events": [event.to_dict() for event in result["events"]],
    }


@app.get("/api/queries/magnitude")
def magnitude_range(min: float, max: float) -> dict[str, Any]:
    result = REPORT_PROCESSOR.query_magnitude_range(
        _to_tenths(min, "min"), _to_tenths(max, "max")
    )
    return {
        "min": min,
        "max": max,
        "nodes_examined": result["nodes_examined"],
        "events": [event.to_dict() for event in result["events"]],
    }


@app.get("/api/queries/depth-dates")
def depth_and_dates(max_depth: float, start: str, end: str) -> dict[str, Any]:
    result = REPORT_PROCESSOR.query_depth_and_dates(
        _to_tenths(max_depth, "max_depth"),
        _parse_utc(start, "start"),
        _parse_utc(end, "end"),
    )
    return {
        "max_depth": max_depth,
        "start": start,
        "end": end,
        "nodes_examined": result["nodes_examined"],
        "events": [event.to_dict() for event in result["events"]],
    }


@app.post("/api/persist")
def persist(payload: dict[str, Any]) -> dict[str, Any]:
    """Export the live scenario to a path chosen by the user.

    The browser normally downloads the export instead (no server path at all).
    """
    path = _require_path(payload)
    state = payload.get("state", {})
    if not isinstance(state, dict):
        raise ValueError("state must be a JSON object")
    # Operational data always comes from the live state; extra client fields
    # (such as a status note) are kept.
    live = _snapshot_state()
    state = {**state, **{key: value for key, value in live.items() if key not in ("status", "message")}}
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
    load_mode = str(payload.get("mode", "topology"))
    snapshot = _capture_undo("load JSON document")
    before = _counter_totals()
    _hydrate_from_snapshot(document, load_mode=load_mode)
    UNDO_STACK.push(snapshot)
    _log_action("load JSON", before, f"{load_mode} load, {len(REPORT_PROCESSOR.active_events)} active events")
    return {"loaded": True, "state": _public_state()}


@app.post("/api/load")
def load_state(payload: dict[str, Any]) -> dict[str, Any]:
    """Load a scenario from a path chosen by the user."""
    path = _require_path(payload)
    persistence = PersistenceService()
    state = persistence.load(path)
    snapshot = _capture_undo("load saved JSON")
    before = _counter_totals()
    _hydrate_from_snapshot(state, load_mode=str(payload.get("mode", "topology")))
    UNDO_STACK.push(snapshot)
    _log_action("load JSON from path", before, str(path))
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