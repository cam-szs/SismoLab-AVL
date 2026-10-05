"""Rotation cases, restorable counters, archive preview, audit, comparison and loads."""

import random
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

import api.app as app_module
from api.app import app
from domain.avl import AVLTree
from domain.event import Event
from domain.event_key import EventKey
from domain.scenario import default_zones
from services.report_processor import ReportProcessor

CLOCK = datetime(2026, 9, 10, 12, tzinfo=timezone.utc)


@pytest.fixture
def client():
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


def create(client: TestClient, event_id: int, magnitude: float, *, hours_ago: int = 1,
           depth: float = 10.0, x: float = 50.0, y: float = 900.0):
    response = client.post("/api/events", json={
        "event_id": event_id, "magnitude": magnitude, "depth_km": depth,
        "x_km": x, "y_km": y, "station": "ST-1",
        "occurred_at": (CLOCK - timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    assert response.status_code == 200, response.json()
    return response.json()


# ---------- the four AVL cases ----------

@pytest.mark.parametrize("ids, case, elementary", [
    ((3, 2, 1), "LL", {"rotate_right": 1}),
    ((1, 2, 3), "RR", {"rotate_left": 1}),
    ((3, 1, 2), "LR", {"rotate_left": 1, "rotate_right": 1}),
    ((1, 3, 2), "RL", {"rotate_left": 1, "rotate_right": 1}),
])
def test_each_case_counts_one_case_and_its_elementary_rotations(ids, case, elementary) -> None:
    tree = AVLTree()
    for event_id in ids:
        tree.insert(EventKey(1, 30, event_id), event_id)

    expected = {"LL": 0, "RR": 0, "LR": 0, "RL": 0, "rotate_left": 0, "rotate_right": 0}
    expected.update({case: 1, **elementary})
    assert tree.rotations_count == expected
    assert tree.root.key.event_id == 2
    assert tree.rotation_log == [{"case": case, "node_id": ids[0], "balance": 2 if case[0] == "L" else -2,
                                  "new_root_id": 2}]


# ---------- recovery ----------

def test_recovery_handles_differences_greater_than_two_and_keeps_identity() -> None:
    tree = AVLTree(stress_mode=True)
    for event_id in range(1, 41):           # ascending: a chain with balance -39 at the root
        tree.insert(EventKey(1, 30, event_id), event_id)
    nodes_before = {node.key: id(node) for node in tree.inorder()}
    assert min(node.balance_factor() for node in tree.inorder()) < -2

    report = tree.recover_balance()

    assert tree.is_balanced()
    assert {node.key: id(node) for node in tree.inorder()} == nodes_before
    assert report["applied_cases"]
    assert sum(report["rotation_delta"].values()) > 0


@pytest.mark.parametrize("seed", range(40))
def test_recovery_on_random_degraded_trees(seed: int) -> None:
    rng = random.Random(seed)
    keys = [EventKey(rng.randint(1, 3), rng.randint(-20, 100), event_id)
            for event_id in rng.sample(range(1, 10_000), rng.randint(5, 80))]
    keys.sort(reverse=rng.random() < 0.5)
    tree = AVLTree(stress_mode=True)
    for key in keys:
        tree.insert(key, key.event_id)
    for key in rng.sample(keys, len(keys) // 3):
        tree.remove(key)
    order_before = [node.key for node in tree.inorder()]

    tree.recover_balance()

    assert tree.is_balanced()
    assert [node.key for node in tree.inorder()] == order_before


def test_recovery_endpoint_reports_cost_and_returns_to_normal(client: TestClient) -> None:
    client.post("/api/scenario/mode", json={"mode": "stress"})
    for event_id in range(1, 9):
        create(client, event_id, 3.0)
    assert client.get("/api/audit").json()["expected_unbalance"] is True

    response = client.post("/api/scenario/recover").json()

    assert response["mode"] == "normal"
    assert response["audit"]["balanced"] is True
    assert response["metrics"]["unbalanced_before"]
    assert response["metrics"]["applied_cases"]


# ---------- restorable counters ----------

def test_undo_and_versions_restore_counters_and_bst_topology(client: TestClient, tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(app_module, "VERSION_DIR", tmp_path)
    for event_id in (1, 2, 3):                      # RR case in the AVL, a chain in the BST
        create(client, event_id, 3.0)
    before = client.get("/api/state").json()
    assert before["counters"]["rotations"]["RR"] == 1
    assert before["counters"]["stats"]["created"] == 3
    assert client.post("/api/versions/v1").status_code == 200

    client.post("/api/events/2/correct", json={"magnitude": 3.5})
    client.post("/api/events/3/delete")
    assert client.get("/api/state").json()["counters"]["stats"]["deletions"] == 1

    client.post("/api/undo")
    client.post("/api/undo")
    after = client.get("/api/state").json()
    assert after["counters"] == before["counters"]
    assert after["bst"] == before["bst"]
    assert after["avl"] == before["avl"]

    create(client, 4, 3.0)
    restored = client.post("/api/versions/v1/restore").json()["state"]
    assert restored["counters"] == before["counters"]
    assert restored["bst"] == before["bst"]


def test_queue_step_shows_rotations_and_undo_restores_queue_position(client: TestClient) -> None:
    for event_id in (1, 2, 3):
        client.post("/api/reports", json={
            "event_id": event_id, "magnitude": 3.0, "depth_km": 10.0, "x_km": 50.0,
            "y_km": 900.0, "station": "ST-1", "occurred_at": "2026-09-10T10:00:00Z",
        })
    client.post("/api/queue/process")
    client.post("/api/queue/process")
    third = client.post("/api/queue/process").json()["result"]
    assert [item["case"] for item in third["rotations"]] == ["RR"]

    state = client.post("/api/undo").json()["state"]
    assert [item["id"] for item in state["queue"]] == [3]
    assert state["counters"]["rotations"]["RR"] == 0


# ---------- archive preview ----------

def test_archive_preview_explains_choice_and_changes_nothing(client: TestClient) -> None:
    for event_id in (10, 20, 30, 40, 50, 60, 70):
        create(client, event_id, 3.0, hours_ago=100)
    create(client, 80, 6.5, hours_ago=100)           # high priority: blocks the branches above it
    before = client.get("/api/state").json()

    preview = client.get("/api/archive/branch/preview").json()

    assert preview["count"] == len(preview["event_ids"]) > 0
    assert 80 not in preview["event_ids"]
    assert preview["eligible_branches"] >= 1
    assert "eligible" in preview["reason"]
    assert client.get("/api/state").json()["avl"] == before["avl"]

    executed = client.post("/api/archive/branch").json()
    assert executed["event_ids"] == preview["event_ids"]
    counters = executed["state"]["counters"]["stats"]
    assert counters["archive_operations"] == 1
    assert counters["archived_events"] == preview["count"]


def test_archive_without_eligible_branch_keeps_state_and_undo_stack(client: TestClient) -> None:
    create(client, 1, 3.0, hours_ago=1)               # too recent
    depth = len(app_module.UNDO_STACK)

    response = client.post("/api/archive/branch").json()

    assert response["archived"] is False
    assert "no eligible branch" in response["reason"]
    assert len(app_module.UNDO_STACK) == depth


# ---------- audit ----------

def test_audit_reports_each_inconsistent_event(client: TestClient) -> None:
    for event_id in (1, 2, 3):
        create(client, event_id, 3.0)
    tree = app_module.REPORT_PROCESSOR.tree
    tree.root.height = 7                               # stale metadata at the root
    tree.root.left.key = EventKey(1, 30, 99)           # breaks order and the key reference

    audit = client.get("/api/audit").json()

    kinds = {(item["event_id"], item["kind"]) for item in audit["issues"]}
    assert (2, "height") in kinds
    assert (99, "order") in kinds
    assert (99, "reference") in kinds
    assert audit["valid_order"] is False
    assert audit["balanced"] is False


def test_audit_distinguishes_expected_stress_imbalance(client: TestClient) -> None:
    client.post("/api/scenario/mode", json={"mode": "stress"})
    for event_id in range(1, 6):
        create(client, event_id, 3.0)

    audit = client.get("/api/audit").json()

    assert audit["metadata_errors"] == []
    assert audit["valid_order"] is True
    assert {item["kind"] for item in audit["issues"]} == {"balance_expected"}


# ---------- loads ----------

def insertion_file(ids):
    return {
        "simulation_time": "2026-09-10T12:00:00Z",
        "events": [
            {"id": event_id, "magnitude": 3.0, "depth_km": 10.0,
             "epicenter": {"x": 50.0, "y": 900.0},
             "occurred_at": "2026-09-10T10:00:00Z", "station": "ST-1"}
            for event_id in ids
        ],
    }


def test_insertion_load_builds_balanced_avl_and_plain_bst(client: TestClient) -> None:
    response = client.post("/api/load-json", json={"document": insertion_file(range(1, 16)),
                                                    "mode": "insertions"})
    assert response.status_code == 200
    metrics = response.json()["state"]["metrics"]
    assert metrics["avl"]["height"] == 3
    assert metrics["bst"]["height"] == 14
    assert response.json()["state"]["counters"]["rotations"]["RR"] > 0


def test_insertion_load_rejects_duplicate_ids_and_keeps_state(client: TestClient) -> None:
    create(client, 500, 3.0)
    response = client.post("/api/load-json", json={"document": insertion_file([1, 2, 1]),
                                                    "mode": "insertions"})
    assert response.status_code == 400
    assert "duplicate" in response.json()["error"]
    assert [event["id"] for event in client.get("/api/state").json()["events"]] == [500]


def test_unbalanced_topology_needs_stress_mode(client: TestClient) -> None:
    client.post("/api/scenario/mode", json={"mode": "stress"})
    for event_id in range(1, 5):
        create(client, event_id, 3.0)
    stressed = client.get("/api/state").json()

    as_normal = deepcopy(stressed)
    as_normal["mode"] = "normal"
    rejected = client.post("/api/load-json", json={"document": as_normal})
    assert rejected.status_code == 400
    assert "stress mode" in rejected.json()["error"]

    accepted = client.post("/api/load-json", json={"document": stressed})
    assert accepted.status_code == 200
    assert accepted.json()["state"]["avl"] == stressed["avl"]


def test_malformed_topology_is_rejected_with_400(client: TestClient) -> None:
    create(client, 1, 3.0)
    state = client.get("/api/state").json()
    broken = deepcopy(state)
    del broken["avl"]["key"]["priority"]
    response = client.post("/api/load-json", json={"document": broken})
    assert response.status_code == 400


# ---------- comparison ----------

def test_compare_endpoint_shows_degenerate_bst_for_sorted_orders(client: TestClient) -> None:
    for event_id in range(1, 32):
        create(client, event_id, 3.0)

    orders = {item["order"]: item for item in client.get("/api/compare").json()["orders"]}

    assert set(orders) == {"given", "ascending", "descending", "random"}
    assert orders["ascending"]["bst"]["height"] == 30
    assert orders["ascending"]["avl"]["height"] == 4
    assert orders["ascending"]["bst"]["total_comparisons"] == sum(range(1, 32))
    assert orders["ascending"]["avl"]["total_comparisons"] < orders["ascending"]["bst"]["total_comparisons"]
    assert client.get("/api/state").json()["metrics"]["avl"]["size"] == 31


def test_traversals_and_indicators_are_exposed(client: TestClient) -> None:
    for event_id in (1, 2, 3):
        create(client, event_id, 3.0)
    state = client.get("/api/state").json()
    assert state["traversals"] == {
        "inorder": [1, 2, 3], "preorder": [2, 1, 3],
        "postorder": [1, 3, 2], "level_order": [2, 1, 3],
    }
    assert state["metrics"]["by_priority"] == {"1": 3, "2": 0, "3": 0}
    assert state["metrics"]["pending_attention"] == 3
    assert state["metrics"]["indicators"]["discarded_reports"] == 0
