"""End-to-end regression cases used during the project defense."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

import api.app as app_module
from api.app import app
from domain.event import Event
from domain.event_key import EventKey
from domain.scenario import Scenario
from services.report_processor import ReportProcessor


def test_simulated_clock_controls_event_age() -> None:
    scenario = Scenario(
        simulation_time=datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    )
    event_time = scenario.simulation_time - timedelta(hours=73)
    event = Event.create(1, 4.0, 10.0, 1.0, 1.0, event_time, "ST-1", False)
    processor = ReportProcessor(active_events={1: event})

    result = processor.archive_branch(
        clock=scenario.simulation_time,
        age_hours=72,
    )

    assert result["root_id"] == 1
    assert result["archived"][0].event_id == 1


def test_archive_branch_is_one_undoable_api_action() -> None:
    client = TestClient(app)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = ReportProcessor()
    app_module.UNDO_STACK = app_module.UndoStack()
    app_module.SCENARIO.simulation_time = datetime(2026, 1, 10, tzinfo=timezone.utc)
    app_module.SCENARIO.clock = 0

    for event_id in (1, 2, 3):
        payload = {
            "event_id": event_id,
            "magnitude": 4.0,
            "depth_km": 10.0,
            "x_km": float(event_id),
            "y_km": 1.0,
            "station": f"ST-{event_id}",
            "occurred_at": "2026-01-01T00:00:00Z",
        }
        assert client.post("/api/reports", json=payload).status_code == 200
        assert client.post("/api/queue/process").status_code == 200

    response = client.post("/api/archive/branch")
    assert response.status_code == 200
    assert response.json()["state"]["metrics"]["active"] == 0

    undone = client.post("/api/undo")
    assert undone.status_code == 200
    assert undone.json()["state"]["metrics"]["active"] == 3


def test_corrupt_json_does_not_replace_live_state() -> None:
    client = TestClient(app)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = ReportProcessor()
    app_module.SCENARIO.simulation_time = datetime.now(timezone.utc).replace(microsecond=0)

    payload = {
        "event_id": 90,
        "magnitude": 4.0,
        "depth_km": 10.0,
        "x_km": 1.0,
        "y_km": 1.0,
        "station": "ST-1",
    }
    assert client.post("/api/reports", json=payload).status_code == 200
    assert client.post("/api/queue/process").status_code == 200
    valid = client.get("/api/state").json()
    corrupt = deepcopy(valid)
    corrupt["avl"] = {
        **corrupt["avl"],
        "height": 99,
    }

    response = client.post("/api/load-json", json={"document": corrupt})
    assert response.status_code == 400
    assert client.get("/api/state").json()["metrics"]["avl"]["size"] == 1


def test_versions_restore_from_disk_after_memory_reset(tmp_path, monkeypatch) -> None:
    client = TestClient(app)
    monkeypatch.setattr(app_module, "VERSION_DIR", tmp_path)
    app_module.VERSIONS.clear()
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.REPORT_PROCESSOR = ReportProcessor()

    saved = client.post("/api/versions/defense-case")
    assert saved.status_code == 200
    app_module.VERSIONS.clear()

    listed = client.get("/api/versions")
    assert listed.json()["versions"] == ["defense-case"]

    restored = client.post("/api/versions/defense-case/restore")
    assert restored.status_code == 200
    assert restored.json()["restored"] is True


def test_priority_ties_order_by_identifier() -> None:
    first = EventKey(1, 40, 10)
    second = EventKey(1, 40, 11)
    assert first < second
