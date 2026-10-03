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
