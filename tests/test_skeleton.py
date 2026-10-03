"""[BOILERPLATE - implemented] Minimal smoke tests for mechanical utilities."""

from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

import api.app as app_module
from api.app import app
from domain.report import Report
from domain.historial import Historial
from domain.queue_fifo import ReportQueue
from domain.scenario import Scenario
from domain.undo_stack import UndoStack
from services.report_processor import ReportProcessor


REPORT_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


def test_report_queue_is_fifo() -> None:
    """Verify the linked queue's mechanical FIFO behavior."""
    queue = ReportQueue[int]()
    queue.enqueue(1)
    queue.enqueue(2)
    assert queue.dequeue() == 1


def test_undo_stack_is_lifo() -> None:
    """Verify the linked stack's mechanical LIFO behavior."""
    stack = UndoStack[int]()
    stack.push(1)
    stack.push(2)
    assert stack.pop() == 2


def test_report_converts_to_pending_event() -> None:
    report = Report.create(7, 5.2, 10.0, 3.0, 4.0, REPORT_TIME, "  ST-01  ", revision=3)

    event = report.to_event()

    assert report.station == "ST-01"
    assert event.event_id == 7
    assert event.magnitude == 5.2
    assert event.revision == 3
    assert event.stations == frozenset({"ST-01"})


def test_report_rejects_precision_and_empty_station() -> None:
    with pytest.raises(ValueError, match="at most one decimal"):
        Report.create(7, 5.25, 10.0, 3.0, 4.0, REPORT_TIME, "ST-01")

    with pytest.raises(ValueError, match="non-empty"):
        Report.create(7, 5.2, 10.0, 3.0, 4.0, REPORT_TIME, "   ")


def make_report(event_id: int, revision: int, magnitude: float, station: str) -> Report:
    return Report.create(
        event_id, magnitude, 5.0, 10.0, 20.0, REPORT_TIME, station, revision=revision
    )


def test_report_processor_resolves_revision_states() -> None:
    queue = ReportQueue[Report]()
    processor = ReportProcessor()

    queue.enqueue(make_report(10, 1, 4.8, "A"))
    assert processor.process_next(queue).decision == "created"

    queue.enqueue(make_report(10, 1, 4.8, "B"))
    confirmation = processor.process_next(queue)
    assert confirmation.decision == "confirmed"
    assert processor.active_events[10].stations == frozenset({"A", "B"})

    queue.enqueue(make_report(10, 1, 5.0, "C"))
    assert processor.process_next(queue).decision == "conflict"
    assert processor.active_events[10].magnitude == 4.8

    queue.enqueue(make_report(10, 2, 6.2, "C"))
    correction = processor.process_next(queue)
    assert correction.decision == "corrected"
    assert processor.active_events[10].revision == 2
    assert processor.active_events[10].magnitude == 6.2

    queue.enqueue(make_report(10, 1, 4.8, "D"))
    assert processor.process_next(queue).decision == "stale"


def test_report_processor_rejects_deleted_ids_and_reactivates_archive() -> None:
    queue = ReportQueue[Report]()
    processor = ReportProcessor()

    queue.enqueue(make_report(20, 1, 4.0, "A"))
    processor.process_next(queue)
    archived = processor.archive(20)

    queue.enqueue(make_report(20, 1, 4.0, "B"))
    assert processor.process_next(queue).decision == "archived_confirmation"
    assert 20 not in processor.active_events
    assert processor.archived_events[20].stations == frozenset({"A", "B"})

    queue.enqueue(make_report(20, 2, 6.1, "C"))
    assert processor.process_next(queue).decision == "reactivated"
    assert processor.active_events[20].revision == 2
    assert processor.active_events[20].stations == frozenset({"A", "B", "C"})
    assert archived.event_id == 20

    processor.delete(20)
    queue.enqueue(make_report(20, 3, 7.0, "D"))
    assert processor.process_next(queue).decision == "rejected_deleted"


def test_report_processor_uses_inclusive_populated_zone_priority() -> None:
    report = Report.create(30, 4.5, 30.0, 10.0, 20.0, REPORT_TIME, "A")
    processor = ReportProcessor(populated_zone=lambda candidate: candidate.event_id == 30)

    assert processor.calculate_priority(report) == 3


def test_report_processor_stress_mode_recovers_global_avl_balance() -> None:
    queue = ReportQueue[Report]()
    processor = ReportProcessor()
    processor.set_stress_mode(True)

    for event_id in range(1, 16):
        queue.enqueue(make_report(event_id, 1, 4.0, f"S-{event_id}"))
        processor.process_next(queue)

    stressed = processor.tree_metrics()
    assert stressed["stress_mode"] is True
    assert stressed["balanced"] is False
    assert stressed["rotations"] == 0

    recovered = processor.recover_balance()

    assert recovered["balanced"] is True
    assert recovered["size"] == 15
    assert processor.tree.find(processor.active_events[8].key) == processor.active_events[8]


def test_report_processor_keeps_avl_value_in_sync_after_confirmation() -> None:
    queue = ReportQueue[Report]()
    processor = ReportProcessor()
    queue.enqueue(make_report(50, 1, 4.8, "A"))
    processor.process_next(queue)

    queue.enqueue(make_report(50, 1, 4.8, "B"))
    result = processor.process_next(queue)

    assert result.event is not None
    assert processor.tree.find(result.event.key) == result.event
    assert processor.tree.find(result.event.key).stations == frozenset({"A", "B"})


def test_persistence_service_round_trips_and_merges_state(tmp_path) -> None:
    from services.persistence_service import PersistenceService

    payload = {
        "status": "normal",
        "metrics": {"active": 1, "archived": 0},
        "events": [{"id": 7, "magnitude": 5.1}],
    }
    destination = tmp_path / "scenario.json"

    service = PersistenceService()
    service.export(destination, payload)
    loaded = service.load(destination)

    assert loaded == payload

    merged = service.load(destination, mode="merge")
    assert merged["status"] == "normal"
    assert merged["metrics"]["active"] == 1

    patched = {"metrics": {"archived": 1}, "status": "paused"}
    merged = service.load(destination, mode="merge")
    assert merged["status"] == "normal"
    assert merged["metrics"]["active"] == 1

    merge_result = service.merge_state(loaded, patched)
    assert merge_result["status"] == "paused"
    assert merge_result["metrics"]["active"] == 1
    assert merge_result["metrics"]["archived"] == 1

    merged_from_file = service.load(destination, mode="merge", current=patched)
    assert merged_from_file["status"] == "normal"
    assert merged_from_file["metrics"]["active"] == 1


def test_history_tracks_archived_and_deleted_reports() -> None:
    from domain.historial import Historial

    historial = Historial()
    report = make_report(70, 2, 6.5, "A")

    historial.archive(report)
    assert historial.archived[-1].event_id == 70

    recovered = historial.restore(70)
    assert recovered.event_id == 70
    assert historial.archived == []

    historial.delete(report)
    assert historial.restore(70).event_id == 70


def test_archive_endpoints_update_history_and_active_catalog() -> None:
    client = TestClient(app)

    report_payload = {
        "event_id": 201,
        "magnitude": 5.4,
        "depth_km": 18.0,
        "x_km": 10.0,
        "y_km": 20.0,
        "station": "ST-10",
        "revision": 1,
    }

    posted = client.post("/api/reports", json=report_payload)
    assert posted.status_code == 200
    assert client.post("/api/queue/process").status_code == 200

    archived = client.post("/api/archive", json={"event_id": 201})
    assert archived.status_code == 200
    assert archived.json()["archived"] is True
    assert archived.json()["event_id"] == 201

    state = client.get("/api/state")
    assert state.status_code == 200
    assert state.json()["metrics"]["archived"] >= 1

    recovered = client.post("/api/recover", json={"event_id": 201})
    assert recovered.status_code == 200
    assert recovered.json()["recovered"] is True


def test_api_state_and_persistence_round_trip() -> None:
    client = TestClient(app)

    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    state = client.get("/api/state")
    assert state.status_code == 200
    assert state.json()["status"] in {"scaffold", "ready"}

    payload = {
        "status": "paused",
        "metrics": {"active": 1, "archived": 0},
        "events": [{"id": 7, "magnitude": 5.1}],
    }
    saved = client.post("/api/persist", json={"state": payload, "path": "tmp_api_state.json"})
    assert saved.status_code == 200
    assert saved.json()["saved"] is True

    loaded = client.post("/api/load", json={"path": "tmp_api_state.json"})
    assert loaded.status_code == 200
    assert loaded.json()["state"]["status"] == "paused"


def test_api_load_rehydrates_queue_and_history() -> None:
    client = TestClient(app)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = app_module.ReportProcessor()

    payload = {
        "event_id": 300,
        "magnitude": 6.1,
        "depth_km": 18.0,
        "x_km": 8.0,
        "y_km": 12.0,
        "station": "ST-30",
        "revision": 1,
    }
    enqueue = client.post("/api/reports", json=payload)
    assert enqueue.status_code == 200

    process = client.post("/api/queue/process")
    assert process.status_code == 200

    archiving = client.post("/api/archive", json={"event_id": 300})
    assert archiving.status_code == 200

    snapshot = client.get("/api/state").json()
    persisted = client.post("/api/persist", json={"state": snapshot, "path": "tmp_rehydrate_state.json"})
    assert persisted.status_code == 200

    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = app_module.ReportProcessor()

    loaded = client.post("/api/load", json={"path": "tmp_rehydrate_state.json"})
    assert loaded.status_code == 200
    assert loaded.json()["state"]["history"]["archived"][0]["id"] == 300
    assert client.get("/api/events").json()["count"] == 0


def test_scenario_clock_and_mode_are_validated() -> None:
    scenario = Scenario()

    scenario.advance_clock(3)
    assert scenario.clock == 3
    assert scenario.values.get("clock") == 3

    scenario.set_mode("stress")
    assert scenario.mode == "stress"
    assert scenario.values.get("previous_mode") == "normal"

    scenario.set_parameters(W=24, R=20, L=4, T=96)
    assert scenario.parameters == {"W": 24.0, "R": 20.0, "L": 4, "T": 96.0}

    with pytest.raises(ValueError, match="normal or stress"):
        scenario.set_mode("X")

    with pytest.raises(ValueError, match="non-negative integer"):
        scenario.advance_clock(-1)

    with pytest.raises(ValueError, match="non-negative integer"):
        scenario.advance_clock(1.5)


def test_scenario_api_exposes_clock_and_mode() -> None:
    client = TestClient(app)

    response = client.get("/api/scenario")
    assert response.status_code == 200
    assert response.json()["mode"] in {"normal", "stress"}
    assert response.json()["clock"] == 0

    mode_response = client.post("/api/scenario/mode", json={"mode": "normal"})
    assert mode_response.status_code == 200
    assert mode_response.json()["mode"] == "normal"

    clock_response = client.post("/api/scenario/clock", json={"amount": 2})
    assert clock_response.status_code == 200
    assert clock_response.json()["clock"] == 2

    state_response = client.get("/api/state")
    assert state_response.status_code == 200
    assert state_response.json()["mode"] == "normal"
    assert state_response.json()["clock"] == 2


def test_api_exposes_avl_metrics_and_event_mutation_controls() -> None:
    client = TestClient(app)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = app_module.ReportProcessor()
    app_module.SCENARIO.set_mode("W")

    payload = {
        "event_id": 510,
        "magnitude": 4.5,
        "depth_km": 20.0,
        "x_km": 10.0,
        "y_km": 20.0,
        "station": "ST-51",
        "revision": 1,
    }
    assert client.post("/api/reports", json=payload).status_code == 200
    assert client.post("/api/queue/process").status_code == 200

    state = client.get("/api/state").json()
    assert state["metrics"]["avl"]["size"] == 1
    assert state["avl"]["key"]["event_id"] == 510

    corrected = client.post("/api/events/510/correct", json={"magnitude": 6.0})
    assert corrected.status_code == 200
    assert corrected.json()["event"]["magnitude"] == 6.0

    deleted = client.post("/api/events/510/delete")
    assert deleted.status_code == 200
    assert deleted.json()["state"]["metrics"]["avl"]["size"] == 0


def test_api_stress_mode_and_global_recovery_controls() -> None:
    client = TestClient(app)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = app_module.ReportProcessor()

    assert client.post("/api/scenario/mode", json={"mode": "T"}).status_code == 200
    for event_id in range(601, 606):
        payload = {
            "event_id": event_id,
            "magnitude": 4.0,
            "depth_km": 20.0,
            "x_km": 10.0,
            "y_km": 20.0,
            "station": f"ST-{event_id}",
            "revision": 1,
        }
        client.post("/api/reports", json=payload)
        client.post("/api/queue/process")

    stressed = client.get("/api/state").json()
    assert stressed["mode"] == "stress"
    assert stressed["metrics"]["avl"]["stress_mode"] is True

    recovered = client.post("/api/scenario/recover")
    assert recovered.status_code == 200
    assert recovered.json()["metrics"]["balanced"] is True
    assert recovered.json()["mode"] == "normal"


def test_report_queue_api_accepts_new_reports() -> None:
    client = TestClient(app)

    payload = {
        "event_id": 101,
        "magnitude": 5.8,
        "depth_km": 12.4,
        "x_km": 10.0,
        "y_km": 20.0,
        "station": "ST-05",
        "revision": 1,
    }

    posted = client.post("/api/reports", json=payload)
    assert posted.status_code == 200
    assert posted.json()["queued"] is True
    assert posted.json()["report"]["event_id"] == 101

    queued = client.get("/api/queue")
    assert queued.status_code == 200
    assert queued.json()["queue"][0]["event_id"] == 101
    assert queued.json()["count"] == 1


def test_association_api_returns_reference_links() -> None:
    client = TestClient(app)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = app_module.ReportProcessor()

    base_time = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    for payload in (
        {
            "event_id": 400,
            "magnitude": 5.0,
            "depth_km": 20.0,
            "x_km": 0.0,
            "y_km": 0.0,
            "station": "ST-40",
            "revision": 1,
            "occurred_at": (base_time).isoformat(),
        },
        {
            "event_id": 401,
            "magnitude": 6.1,
            "depth_km": 18.0,
            "x_km": 8.0,
            "y_km": 0.0,
            "station": "ST-41",
            "revision": 1,
            "occurred_at": (base_time.replace(hour=9)).isoformat(),
        },
    ):
        posted = client.post("/api/reports", json=payload)
        assert posted.status_code == 200

    assert client.post("/api/queue/process").status_code == 200
    assert client.post("/api/queue/process").status_code == 200

    response = client.get("/api/associations")
    assert response.status_code == 200
    assert response.json()["count"] >= 1
    assert any(item["reference_id"] == 401 for item in response.json()["associations"])
def test_history_archives_restores_and_preserves_deleted_reports() -> None:
    report = make_report(40, 1, 4.0, "A")
    history = Historial()

    history.archive(report)
    assert history.archived_count == 1
    assert history.find_archived("SIS-000040") == report
    assert history.restore("SIS-000040") == report
    assert history.archived_count == 0

    history.delete(report)
    assert history.deleted_count == 1
    assert history.find_deleted(40) == report
    assert history.restore(40) == report


def test_history_rejects_missing_report_and_duplicate_archive_is_idempotent() -> None:
    report = make_report(41, 1, 4.0, "A")
    history = Historial()
    history.archive(report)
    history.archive(report)

    assert history.archived == [report]
    with pytest.raises(LookupError, match="not archived or deleted"):
        history.restore(999)
