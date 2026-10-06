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


# ---------- deletion with the in-order predecessor ----------

import random

from domain.bst import BSTree


def build(tree, ids):
    for event_id in ids:
        tree.insert(EventKey(1, 30, event_id), event_id)
    return tree


def test_deleting_the_root_promotes_its_in_order_predecessor() -> None:
    #        50                 40
    #       /  \               /  \
    #     30    70     ->    30    70
    #    /  \   /           /     /
    #   20  40 60          20    60
    tree = build(AVLTree(), [50, 30, 70, 20, 40, 60])
    predecessor_node = tree.root.left.right                    # node holding 40

    tree.remove(EventKey(1, 30, 50))

    assert tree.root is predecessor_node                       # relinked, not copied
    assert tree.root.event == 40
    assert tree.root.left.key.event_id == 30
    assert tree.root.right.key.event_id == 70
    assert tree.is_balanced()


def test_predecessor_deep_in_the_left_subtree_rebalances_the_path() -> None:
    tree = build(AVLTree(), [50, 30, 70, 20, 40, 60, 80, 10, 35, 45, 90, 47])
    tree.remove(EventKey(1, 30, 50))
    assert tree.root.key.event_id == 47
    assert tree.is_balanced()
    assert [node.key.event_id for node in tree.inorder()] == [10, 20, 30, 35, 40, 45, 47, 60, 70, 80, 90]


def test_deletion_that_unbalances_the_tree_rotates() -> None:
    tree = build(AVLTree(), [20, 10, 30, 40])
    rotations_before = tree.rotations_count["RR"]
    tree.remove(EventKey(1, 30, 10))                           # left side becomes too short
    assert tree.rotations_count["RR"] == rotations_before + 1
    assert tree.root.key.event_id == 30
    assert tree.is_balanced()


def test_plain_bst_also_uses_the_predecessor() -> None:
    tree = build(BSTree(), [50, 30, 70, 20, 40])
    tree.delete(EventKey(1, 30, 50))
    assert tree.root.key.event_id == 40
    assert [node.key.event_id for node in tree.inorder()] == [20, 30, 40, 70]


def test_nodes_keep_their_own_events_while_balancing(seed_count: int = 30) -> None:
    for seed in range(seed_count):
        rng = random.Random(seed)
        ids = rng.sample(range(1, 2000), 60)
        tree = build(AVLTree(), ids)
        node_of = {node.key.event_id: node for node in tree.inorder()}
        for event_id in rng.sample(ids, 40):
            tree.remove(EventKey(1, 30, event_id))
            assert tree.is_balanced()
            for node in tree.inorder():
                assert node is node_of[node.key.event_id]
                assert node.event == node.key.event_id
