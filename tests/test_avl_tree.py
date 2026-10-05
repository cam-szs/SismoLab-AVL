from domain.avl import AVLTree
from domain.event_key import EventKey


def test_avl_insert_and_search() -> None:
    tree = AVLTree[EventKey, str]()
    keys = [
        EventKey(2, 50, 20),
        EventKey(1, 40, 10),
        EventKey(3, 60, 30),
        EventKey(2, 45, 15),
    ]

    for key in keys:
        tree.insert(key, f"event-{key.event_id}")

    assert tree.find(EventKey(2, 45, 15)) == "event-15"
    assert tree.find(EventKey(9, 99, 999)) is None
    assert tree.size == 4


def test_avl_inorder_is_sorted() -> None:
    tree = AVLTree[EventKey, str]()
    insertion = [
        EventKey(3, 70, 7),
        EventKey(1, 40, 1),
        EventKey(2, 50, 2),
        EventKey(3, 60, 3),
        EventKey(1, 30, 4),
    ]

    for key in insertion:
        tree.insert(key, str(key.event_id))

    ordered = tree.traverse_in_order()
    keys = [key for key, _ in ordered]
    assert keys == sorted(keys)
    assert ordered[0][1] == "4"


def test_stress_mode_defers_rotations_and_recovers() -> None:
    tree = AVLTree[EventKey, str]()
    tree.enable_stress_mode()

    for event_id in range(1, 16):
        key = EventKey(1, event_id, event_id)
        tree.insert(key, str(event_id))

    assert tree.stress_mode is True
    assert tree.is_balanced() is False
    assert tree.rotations_count == {
        "LL": 0, "RR": 0, "LR": 0, "RL": 0, "rotate_left": 0, "rotate_right": 0,
    }

    metrics = tree.recover_balance()

    assert tree.is_balanced() is True
    assert metrics["size"] == 15
    assert [key.event_id for key, _ in tree.traverse_in_order()] == list(range(1, 16))


def test_disabling_stress_mode_recovers_by_default() -> None:
    tree = AVLTree[EventKey, str](stress_mode=True)
    for event_id in range(1, 8):
        tree.insert(EventKey(1, event_id, event_id), str(event_id))

    tree.disable_stress_mode()

    assert tree.stress_mode is False
    assert tree.is_balanced() is True
