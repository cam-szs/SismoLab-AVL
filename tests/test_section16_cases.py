"""Section 16 minimum cases, run on the reproducible files in samples/.

docs/CASOS_SECCION_16.md lists, for each case, the initial state, the steps,
the expected result and the obtained result; these tests keep both in sync.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.app as app_module
from api.app import app
from domain.scenario import Scenario
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
    fresh = Scenario()
    app_module.SCENARIO.__dict__.update(fresh.__dict__)
    app_module.SCENARIO.simulation_time = datetime(2026, 10, 5, 12, tzinfo=timezone.utc)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.UNDO_STACK = app_module.UndoStack()
    app_module.REPORT_PROCESSOR = ReportProcessor(
        populated_zone=lambda item: app_module.SCENARIO.is_populated(item.x_km, item.y_km)
    )
    yield TestClient(app)
    app_module.SCENARIO.__dict__.update(saved[0])
    app_module.REPORT_QUEUE, app_module.REPORT_PROCESSOR, app_module.UNDO_STACK = saved[1:]


def insertions(client, document):
    return client.post("/api/load-json", json={"document": document, "mode": "insertions"}).json()["state"]


def test_case1_limits_and_ties(client) -> None:
    state = insertions(client, sample("caso1_limites_empates.json"))
    priority = {event["id"]: event["priority"] for event in state["events"]}
    assert priority == {401: 3, 402: 2, 403: 2, 404: 3, 405: 2, 406: 1, 410: 2}
    assert state["traversals"]["inorder"] == [406, 402, 403, 405, 410, 401, 404]


def test_case2_correction_and_stale_report(client) -> None:
    client.post("/api/queue/load", json={"document": sample("caso2_correccion_reporte_antiguo.json")})
    results = [client.post("/api/queue/process").json()["result"] for _ in range(3)]
    assert [item["decision"] for item in results] == ["created", "corrected", "stale"]
    assert (results[0]["event"]["priority"], results[1]["event"]["priority"]) == (2, 3)
    final = client.get("/api/events/220").json()["event"]
    assert (final["magnitude"], final["depth_km"], final["revision"]) == (6.2, 15.0, 2)
    assert client.get("/api/state").json()["metrics"]["avl"]["size"] == 1


def test_case3_late_report(client) -> None:
    client.post("/api/queue/load", json={"document": sample("caso3_reporte_tardio.json")})
    client.post("/api/queue/process")
    client.post("/api/queue/process")
    assert client.get("/api/events/302").json()["associations"]["reference_id"] == 301
    client.post("/api/queue/process")
    late = client.get("/api/events/302").json()["associations"]
    assert [item["event_id"] for item in late["candidates"]] == [303, 301]
    assert late["reference_id"] == 303
    assert client.get("/api/events/301").json()["associations"]["reference_id"] == 303
    referenced = client.get("/api/events/303").json()["associations"]["referenced_by"]
    assert {item["event_id"] for item in referenced} == {301, 302}


def test_case4_four_rotation_cases_and_recovery(client) -> None:
    document = sample("caso4_rotaciones.json")
    cases = []
    for count in range(1, len(document["events"]) + 1):
        state = insertions(client, {**document, "events": document["events"][:count]})
        cases.append(dict(state["counters"]["rotations"]))
    assert [cases[index][name] for index, name in ((2, "LL"), (4, "RL"), (5, "LR"), (6, "RR"))] == [1, 1, 1, 1]
    assert cases[-1]["rotate_left"] == cases[-1]["rotate_right"] == 3

    stressed = client.post("/api/load-json", json={"document": sample("topologia_estres.json")}).json()["state"]
    assert stressed["avl"]["factor_balanceo"] == -6
    recovered = client.post("/api/scenario/recover").json()
    assert recovered["audit"]["balanced"] is True
    assert recovered["mode"] == "normal"
    assert recovered["state"]["traversals"]["inorder"] == stressed["traversals"]["inorder"]


def test_case5_mass_archival(client) -> None:
    client.post("/api/load-json", json={"document": sample("caso5_archivo_masivo.json")})
    preview = client.get("/api/archive/branch/preview").json()
    assert (preview["root_id"], preview["event_ids"]) == (506, [505, 506, 507])
    assert preview["alternatives"][:2] == [
        {"root_id": 506, "size": 3, "depth": 2},
        {"root_id": 502, "size": 3, "depth": 1},
    ]
    eligible_roots = {item["root_id"] for item in preview["alternatives"]}
    assert not eligible_roots & {504, 508, 509, 510}

    archived = client.post("/api/archive/branch").json()["state"]
    assert (archived["metrics"]["active"], archived["metrics"]["archived"]) == (7, 3)
    undone = client.post("/api/undo").json()["state"]
    assert (undone["metrics"]["active"], undone["metrics"]["archived"]) == (10, 0)

    client.post("/api/scenario/parameters", json={"T": 200})
    assert client.get("/api/archive/branch/preview").json()["root_id"] is None


def test_case6_persistence_and_consistency(client, tmp_path, monkeypatch) -> None:
    for name in ("topologia_normal.json", "topologia_estres.json"):
        document = sample(name)
        state = client.post("/api/load-json", json={"document": document}).json()["state"]
        assert state["avl"] == document["avl"] and state["counters"] == document["counters"]
    before = client.get("/api/state").json()["avl"]
    rejected = client.post("/api/load-json", json={"document": sample("topologia_invalida.json")})
    assert rejected.status_code == 400
    assert client.get("/api/state").json()["avl"] == before

    # A version survives a restart (memory cleared, read back from disk) and its restore is undoable.
    monkeypatch.setattr(app_module, "VERSION_DIR", tmp_path)
    client.post("/api/versions/demo-estres")
    client.post("/api/load-json", json={"document": sample("topologia_normal.json")})
    app_module.VERSIONS.clear()
    restored = client.post("/api/versions/demo-estres/restore").json()["state"]
    assert restored["avl"] == before
    assert client.post("/api/undo").json()["state"]["avl"] == sample("topologia_normal.json")["avl"]
