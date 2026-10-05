"""AVL vs BST comparison for one set of events under several insertion orders."""

from __future__ import annotations

import random
from typing import Any, Iterable

from domain.avl import AVLTree, elementary_rotations
from domain.bst import BSTree
from domain.event import Event

# A fixed seed keeps the "random" order reproducible between runs.
RANDOM_SEED = 2026


def _search_cost(tree: BSTree, events: list[Event]) -> dict[str, Any]:
    """Search every key once; the cost of a search is the nodes visited.

    One visited node equals one key comparison, so this is the comparison
    count the assignment asks for.
    """
    costs = [tree.search(event.key)[1] for event in events]
    total = sum(costs)
    return {
        "total_comparisons": total,
        "average_comparisons": round(total / len(costs), 2) if costs else 0,
        "max_comparisons": max(costs, default=0),
    }


def _measure(tree: BSTree, events: list[Event]) -> dict[str, Any]:
    root = tree.root
    return {
        "root_id": root.event_id if root is not None else None,
        "height": tree.get_height(),
        "max_depth": tree.get_height(),   # the deepest node is at depth = height
        "leaves": tree.count_leaves(),
        **_search_cost(tree, events),
    }


def insertion_orders(events: Iterable[Event]) -> dict[str, list[Event]]:
    """The orders compared: given (as received), ascending K, descending K, random."""
    given = list(events)
    shuffled = list(given)
    random.Random(RANDOM_SEED).shuffle(shuffled)
    return {
        "given": given,
        "ascending": sorted(given, key=lambda event: event.key),
        "descending": sorted(given, key=lambda event: event.key, reverse=True),
        "random": shuffled,
    }


def compare_orders(events: Iterable[Event]) -> list[dict[str, Any]]:
    """Insert the same events, with the same comparator, into a balanced AVL
    and a plain BST for each order, then measure both trees.

    Cost: O(n log n) per order for the AVL and O(n^2) worst case for the BST
    (ascending or descending order makes it a linked list of height n - 1).
    """
    results = []
    for name, ordered in insertion_orders(events).items():
        avl = AVLTree()
        bst = BSTree()
        for event in ordered:
            avl.insert(event.key, event)
            bst.insert(event.key, event)
        results.append({
            "order": name,
            "size": len(ordered),
            "avl": {**_measure(avl, ordered), "rotations": elementary_rotations(avl.rotations_count)},
            "bst": _measure(bst, ordered),
        })
    return results
