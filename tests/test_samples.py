"""The JSON files in samples/ must keep loading as documented."""

import json
from copy import deepcopy
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.app as app_module
from api.app import app
from domain.scenario import default_stations, default_zones
from services.report_processor import ReportProcessor

SAMPLES = Path(__file__).resolve().parent.parent / "samples"


def sample(name: str) -> dict:
    return json.loads((SAMPLES / name).read_text(encoding="utf-8"))


@pytest.fixture
def client():
    saved = (
        {**app_module.SCENARIO.__dict__, "values": dict(app_module.SCENARIO.values)},
        app_module.REPORT_QUEUE, app_module.REPORT_PROCESSOR, app_module.UNDO_STACK,
    )
    app_module.SCENARIO.zones = default_zones()
    app_module.SCENARIO.stations = default_stations()
    app_module.SCENARIO.mode = "normal"
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.UNDO_STACK = app_module.UndoStack()
    app_module.REPORT_PROCESSOR = ReportProcessor(
        populated_zone=lambda item: app_module.SCENARIO.is_populated(item.x_km, item.y_km)
    )
    yield TestClient(app)
    app_module.SCENARIO.__dict__.update(saved[0])
    app_module.REPORT_QUEUE, app_module.REPORT_PROCESSOR, app_module.UNDO_STACK = saved[1:]


def load(client, name, mode, document=None):
    return client.post("/api/load-json", json={"document": document or sample(name), "mode": mode})


def test_random_insertion_sample(client) -> None:
    state = load(client, "insercion_aleatoria.json", "insertions").json()["state"]
    priorities = {event["id"]: event["priority"] for event in state["events"]}
    assert priorities[115] == 3 and priorities[130] == 2      # zone border vs outside
    assert priorities[125] == 2 and priorities[160] == 3      # H > 30 vs H <= 30 in a zone
    assert state["metrics"]["avl"]["balanced"] is True
    assert state["metrics"]["avl"]["height"] < state["metrics"]["bst"]["height"]


def test_ascending_insertion_sample_degenerates_the_bst(client) -> None:
    state = load(client, "insercion_ascendente.json", "insertions").json()["state"]
    assert state["metrics"]["bst"]["height"] == 11
    assert state["metrics"]["avl"]["height"] == 3
    assert state["counters"]["rotations"]["RR"] > 0


def test_normal_topology_sample_restores_the_exact_tree(client) -> None:
    document = sample("topologia_normal.json")
    state = load(client, None, "topology", document).json()["state"]
    assert state["avl"] == document["avl"]
    assert state["bst"] == document["bst"]
    assert [item["id"] for item in state["queue"]] == [180]
    assert state["counters"] == document["counters"]


def test_stress_topology_sample_needs_stress_mode(client) -> None:
    document = sample("topologia_estres.json")
    state = load(client, None, "topology", document).json()["state"]
    assert state["mode"] == "stress"
    assert state["metrics"]["avl"]["balanced"] is False
    assert state["avl"] == document["avl"]

    as_normal = deepcopy(document)
    as_normal["mode"] = "normal"
    assert load(client, None, "topology", as_normal).status_code == 400


def test_invalid_topology_sample_is_rejected_without_changes(client) -> None:
    before = load(client, "topologia_normal.json", "topology").json()["state"]["avl"]
    response = load(client, "topologia_invalida.json", "topology")
    assert response.status_code == 400
    assert "height" in response.json()["error"]
    assert client.get("/api/state").json()["avl"] == before


def test_burst_sample_queues_every_report(client) -> None:
    app_module.SCENARIO.simulation_time = app_module._parse_utc("2026-10-05T12:00:00Z")
    response = client.post("/api/queue/load", json={"document": sample("rafaga_reportes.json")})
    assert response.json()["queued"] == 8
