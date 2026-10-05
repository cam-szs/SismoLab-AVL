"""Zones, manual creation, lookup by id, corrections and section 11 queries."""

import random
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import api.app as app_module
from api.app import app
from domain.event import Event
from domain.scenario import Scenario, default_zones
from services.report_processor import ReportProcessor

CLOCK = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)


@pytest.fixture
def client():
    """Fresh API state whose processor classifies epicenters with the live zones.

    The module-level API globals are restored afterwards so other test files
    keep seeing the state they expect.
    """
    saved = (
        {**app_module.SCENARIO.__dict__, "values": dict(app_module.SCENARIO.values)},
        app_module.REPORT_QUEUE,
        app_module.REPORT_PROCESSOR,
        app_module.UNDO_STACK,
    )
    app_module.SCENARIO.zones = default_zones()
    app_module.SCENARIO.simulation_time = CLOCK
    app_module.SCENARIO.clock = 0
    app_module.SCENARIO.mode = "normal"
    app_module.SCENARIO.set_parameters(W=48, R=40, L=3, T=72)
    app_module.REPORT_QUEUE = app_module.ReportQueue()
    app_module.UNDO_STACK = app_module.UndoStack()
    app_module.REPORT_PROCESSOR = ReportProcessor(
        populated_zone=lambda item: app_module.SCENARIO.is_populated(item.x_km, item.y_km)
    )
    yield TestClient(app)
    app_module.SCENARIO.__dict__.update(saved[0])
    app_module.REPORT_QUEUE, app_module.REPORT_PROCESSOR, app_module.UNDO_STACK = saved[1:]


def create(client: TestClient, event_id: int, magnitude: float, depth: float,
           x: float = 50.0, y: float = 900.0, occurred_at: str = "2026-09-10T10:00:00Z"):
    return client.post("/api/events", json={
        "event_id": event_id,
        "magnitude": magnitude,
        "depth_km": depth,
        "x_km": x,
        "y_km": y,
        "occurred_at": occurred_at,
        "station": "ST-1",
    })


# ---------- zones and priority limits ----------

def test_zone_border_shared_with_unpopulated_zone_counts_as_populated() -> None:
    scenario = Scenario()
    # x = 500 is the border between Valle Central (populated) and Sierra Alta.
    assert scenario.is_populated(500.0, 400.0)
    assert scenario.is_populated(300.0, 300.0)       # corner of Valle Central
    assert not scenario.is_populated(600.0, 400.0)   # inside Sierra Alta only
    assert not scenario.is_populated(50.0, 900.0)    # outside every zone


def test_priority_limits_with_zones(client: TestClient) -> None:
    # M = 4.5 and H = 30.0 on the populated border -> priority 3.
    assert create(client, 1, 4.5, 30.0, x=500.0, y=400.0).json()["event"]["priority"] == 3
    # Same data outside a populated zone -> priority 2.
    assert create(client, 2, 4.5, 30.0, x=600.0, y=400.0).json()["event"]["priority"] == 2
    # H = 30.1 breaks the populated rule -> priority 2.
    assert create(client, 3, 4.5, 30.1, x=400.0, y=400.0).json()["event"]["priority"] == 2
    # M = 6.0 is high anywhere.
    assert create(client, 4, 6.0, 300.0).json()["event"]["priority"] == 3
    assert create(client, 5, 4.4, 10.0, x=400.0, y=400.0).json()["event"]["priority"] == 1


def test_zones_are_saved_and_rejected_when_flags_do_not_match(client: TestClient) -> None:
    # M = 3.0 is low priority anywhere, so only the stored zone flag is wrong.
    create(client, 1, 3.0, 30.0, x=400.0, y=400.0)
    state = client.get("/api/state").json()
    assert {zone["name"] for zone in state["scenario"]["zones"]} == set(default_zones())

    tampered = dict(state)
    tampered["events"] = [{**state["events"][0], "populated_zone": False}]
    response = client.post("/api/load-json", json={"document": tampered, "mode": "topology"})
    assert response.status_code == 400
    assert "populated_zone" in response.json()["error"]


# ---------- manual creation ----------

def test_manual_creation_is_one_undoable_action(client: TestClient) -> None:
    response = create(client, 10, 5.2, 12.0)
    assert response.status_code == 200
    event = response.json()["event"]
    assert event["revision"] == 1
    assert event["status"] == "pending"
    assert len(app_module.UNDO_STACK) == 1

    undone = client.post("/api/undo").json()
    assert undone["state"]["metrics"]["active"] == 0


@pytest.mark.parametrize("prepare", ["active", "archived", "deleted"])
def test_creation_rejects_any_registered_id_without_changes(client: TestClient, prepare: str) -> None:
    create(client, 10, 5.2, 12.0)
    if prepare == "archived":
        client.post("/api/archive", json={"event_id": 10})
    if prepare == "deleted":
        client.post("/api/events/10/delete")
    before = client.get("/api/state").json()
    undo_depth = len(app_module.UNDO_STACK)

    response = create(client, 10, 3.0, 5.0)

    assert response.status_code == 400
    assert prepare in response.json()["error"]
    assert len(app_module.UNDO_STACK) == undo_depth
    after = client.get("/api/state").json()
    assert after["avl"] == before["avl"]
    assert after["history"] == before["history"]


@pytest.mark.parametrize("override", [
    {"magnitude": 10.1}, {"magnitude": 4.25}, {"depth_km": -0.1},
    {"x_km": 1000.1}, {"occurred_at": "2026-09-10T12:00:01Z"}, {"station": " "},
])
def test_creation_rejects_invalid_data(client: TestClient, override: dict) -> None:
    payload = {
        "event_id": 20, "magnitude": 5.0, "depth_km": 10.0, "x_km": 1.0,
        "y_km": 1.0, "occurred_at": "2026-09-10T10:00:00Z", "station": "ST-1",
        **override,
    }
    response = client.post("/api/events", json=payload)
    assert response.status_code == 400
    assert client.get("/api/state").json()["metrics"]["active"] == 0


# ---------- correction ----------

def test_correction_case_from_section_16(client: TestClient) -> None:
    create(client, 30, 4.8, 70.0, x=400.0, y=400.0)
    assert client.get("/api/events/30").json()["event"]["priority"] == 2

    corrected = client.post("/api/events/30/correct", json={"magnitude": 6.2, "depth_km": 15.0})
    assert corrected.status_code == 200
    event = corrected.json()["event"]
    assert (event["priority"], event["revision"], event["status"]) == (3, 2, "pending")

    # An older revision received later does not create a node or revert the data.
    client.post("/api/reports", json={
        "event_id": 30, "magnitude": 4.8, "depth_km": 70.0, "x_km": 400.0,
        "y_km": 400.0, "station": "ST-2", "revision": 1,
        "occurred_at": "2026-09-10T10:00:00Z",
    })
    result = client.post("/api/queue/process").json()["result"]
    assert result["decision"] == "stale"
    state = client.get("/api/state").json()
    assert state["metrics"]["avl"]["size"] == 1
    assert state["events"][0]["magnitude"] == 6.2


def test_correction_recomputes_populated_zone_from_new_epicenter(client: TestClient) -> None:
    create(client, 31, 4.6, 20.0, x=600.0, y=400.0)
    assert client.get("/api/events/31").json()["event"]["priority"] == 2

    moved = client.post("/api/events/31/correct", json={"x_km": 450.0}).json()["event"]
    assert moved["populated_zone"] is True
    assert moved["priority"] == 3


def test_correction_with_same_key_still_increments_revision(client: TestClient) -> None:
    create(client, 32, 3.0, 20.0)
    event = client.post("/api/events/32/correct", json={"depth_km": 25.0}).json()["event"]
    assert event["revision"] == 2


def test_invalid_correction_changes_nothing_and_adds_no_undo_step(client: TestClient) -> None:
    create(client, 33, 3.0, 20.0)
    before = client.get("/api/state").json()["avl"]
    undo_depth = len(app_module.UNDO_STACK)

    for body in ({"magnitude": 11.0}, {"populated_zone": True}, {"occurred_at": "2027-01-01T00:00:00Z"}):
        assert client.post("/api/events/33/correct", json=body).status_code == 400

    assert client.get("/api/state").json()["avl"] == before
    assert len(app_module.UNDO_STACK) == undo_depth


# ---------- lookup by id ----------

def test_lookup_reports_status_and_structure(client: TestClient) -> None:
    for event_id in (1, 2, 3):
        create(client, event_id, 3.0 + event_id / 10, 10.0)

    root = client.get("/api/events/2").json()
    assert root["status"] == "active"
    assert root["location"]["node_depth"] == 0
    assert root["location"]["nodes_visited"] == 1
    assert root["location"]["height"] == 1
    assert root["location"]["balance_factor"] == 0
    assert root["key"] == "(1, 3.2, 2)"

    leaf = client.get("/api/events/3").json()["location"]
    assert leaf["node_depth"] == 1 and leaf["nodes_visited"] == 2

    client.post("/api/archive", json={"event_id": 1})
    client.post("/api/events/3/delete")
    assert client.get("/api/events/1").json()["status"] == "archived"
    assert client.get("/api/events/3").json() == {"event_id": 3, "status": "deleted"}
    assert client.get("/api/events/99").status_code == 404


def test_lookup_lists_candidates_reference_and_referencing_events(client: TestClient) -> None:
    # Late report case: 5.6 at 10:00, 4.2 at 10:20, then 6.1 at 09:55, all nearby.
    create(client, 41, 5.6, 10.0, x=50.0, y=900.0, occurred_at="2026-09-10T10:00:00Z")
    create(client, 42, 4.2, 10.0, x=55.0, y=900.0, occurred_at="2026-09-10T10:20:00Z")
    create(client, 43, 6.1, 10.0, x=60.0, y=900.0, occurred_at="2026-09-10T09:55:00Z")
    client.post("/api/archive", json={"event_id": 41})

    small = client.get("/api/events/42").json()["associations"]
    assert {item["event_id"] for item in small["candidates"]} == {41, 43}
    assert small["reference_id"] == 43
    assert {item["event_id"]: item["status"] for item in small["candidates"]} == {
        41: "archived", 43: "active",
    }

    big = client.get("/api/events/43").json()["associations"]
    assert big["candidates"] == []
    assert {item["event_id"] for item in big["referenced_by"]} == {41, 42}


# ---------- section 11 queries ----------

def _build_processor(events: list[Event]) -> ReportProcessor:
    processor = ReportProcessor()
    for event in events:
        processor._insert_active(event)
    return processor


def _random_events(seed: int, count: int) -> list[Event]:
    rng = random.Random(seed)
    events = []
    for event_id in rng.sample(range(1, 5000), count):
        events.append(Event.create(
            event_id, rng.randint(-20, 100) / 10, rng.randint(0, 7000) / 10,
            rng.randint(0, 10000) / 10, rng.randint(0, 10000) / 10,
            CLOCK - timedelta(hours=rng.randint(0, 500)), "ST-1",
            populated_zone=rng.random() < 0.5,
        ))
    return events


@pytest.mark.parametrize("seed", range(5))
def test_magnitude_range_matches_brute_force(seed: int) -> None:
    events = _random_events(seed, 120)
    processor = _build_processor(events)
    for low, high in ((-20, 100), (45, 59), (10, 30), (60, 100), (44, 45), (70, 70)):
        result = processor.query_magnitude_range(low, high)
        expected = sorted(
            (event for event in events if low <= event.magnitude_tenths <= high),
            key=lambda event: event.key,
        )
        assert result["events"] == expected
        assert result["nodes_examined"] <= len(events)


def test_magnitude_range_discards_branches_using_the_key() -> None:
    # Only low-priority magnitudes 1.0..3.9 plus a few high ones.
    events = [Event.create(i, 1.0 + (i % 30) / 10, 10.0, 1.0, 1.0, CLOCK, "ST", False)
              for i in range(1, 64)]
    events += [Event.create(100 + i, 7.0, 10.0, 1.0, 1.0, CLOCK, "ST", False) for i in range(3)]
    processor = _build_processor(events)

    result = processor.query_magnitude_range(65, 80)

    assert [event.event_id for event in result["events"]] == [100, 101, 102]
    assert result["nodes_examined"] < processor.tree.size // 2


def test_top_pending_stops_early_and_skips_reviewed() -> None:
    events = [Event.create(i, i / 10, 10.0, 1.0, 1.0, CLOCK, "ST", False) for i in range(1, 32)]
    processor = _build_processor(events)
    processor.mark_reviewed(31)

    result = processor.query_top_pending(3)

    assert [event.event_id for event in result["events"]] == [30, 29, 28]
    assert result["nodes_examined"] == 4
    assert len(processor.query_top_pending(100)["events"]) == 30


def test_query_endpoints_report_examined_nodes(client: TestClient) -> None:
    create(client, 1, 3.0, 5.0, occurred_at="2026-09-09T10:00:00Z")
    create(client, 2, 4.0, 50.0, occurred_at="2026-09-10T10:00:00Z")
    create(client, 3, 5.0, 8.0, occurred_at="2026-09-10T11:00:00Z")

    top = client.get("/api/queries/top-pending", params={"limit": 2}).json()
    assert [event["id"] for event in top["events"]] == [3, 2]
    assert top["nodes_examined"] >= 2

    magnitude = client.get("/api/queries/magnitude", params={"min": 3.5, "max": 5.0}).json()
    assert [event["id"] for event in magnitude["events"]] == [2, 3]

    dates = client.get("/api/queries/depth-dates", params={
        "max_depth": 10.0, "start": "2026-09-10T00:00:00Z", "end": "2026-09-10T23:59:59Z",
    }).json()
    assert [event["id"] for event in dates["events"]] == [3]
    assert dates["nodes_examined"] == 3

    assert client.get("/api/queries/top-pending", params={"limit": 0}).status_code == 400
    assert client.get("/api/queries/magnitude", params={"min": 5, "max": 4}).status_code == 400
