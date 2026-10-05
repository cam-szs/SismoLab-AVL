"""AVL tree implementation on top of the BST contract."""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from .bst import BSTree, DuplicateKeyError
from .node import Node

Key = TypeVar("Key")
Value = TypeVar("Value")

# Backwards-compatible alias used by the project skeleton.
AVLNode = Node

# LL/RR/LR/RL count balancing cases; rotate_left/rotate_right count the
# elementary rotations (a double case adds one case and two rotations).
ROTATION_COUNTER_KEYS = ("LL", "RR", "LR", "RL", "rotate_left", "rotate_right")


def new_rotation_counters() -> dict[str, int]:
    return dict.fromkeys(ROTATION_COUNTER_KEYS, 0)


def elementary_rotations(counts: dict[str, int]) -> int:
    return counts["rotate_left"] + counts["rotate_right"]


class AVLTree(BSTree, Generic[Key, Value]):
    """Balance a BST, with an optional deferred-balancing stress mode.

    Stress mode is intended for a burst of inserts/deletes: structural
    operations keep the BST ordering and stored heights correct, but defer
    rotations until :meth:`recover_balance` is called.
    """

    def __init__(self, *, stress_mode: bool = False) -> None:
        super().__init__()
        self.stress_mode = stress_mode
        self.rotations_count = new_rotation_counters()
        # One entry per balancing case handled, so callers can show which
        # rotations an operation produced (compare the length before/after).
        self.rotation_log: list[dict[str, object]] = []

    def _rotate_left(self, node: Node) -> Node:
        """Elementary left rotation of the subtree rooted at `node`.

        Only links and heights change; keys and events stay in their nodes,
        so the in-order sequence (the BST order) is preserved.
        """
        pivot = node.right
        if pivot is None:
            return node

        node.right = pivot.left
        pivot.left = node
        node.update_height()
        pivot.update_height()
        self.rotations_count["rotate_left"] += 1
        return pivot

    def _rotate_right(self, node: Node) -> Node:
        """Elementary right rotation of the subtree rooted at `node`."""
        pivot = node.left
        if pivot is None:
            return node

        node.left = pivot.right
        pivot.right = node
        node.update_height()
        pivot.update_height()
        self.rotations_count["rotate_right"] += 1
        return pivot

    def _fix_balance(self, node: Node) -> Node:
        """Apply the AVL case for an unbalanced node and return the new root.

        LL and RR use one elementary rotation; LR and RL count as one case
        and two elementary rotations, as the assignment requires.
        """
        balance = node.balance_factor()
        if balance > 1:
            if node.left is not None and node.left.balance_factor() < 0:
                case = "LR"
                node.left = self._rotate_left(node.left)
            else:
                case = "LL"
            new_root = self._rotate_right(node)
        elif balance < -1:
            if node.right is not None and node.right.balance_factor() > 0:
                case = "RL"
                node.right = self._rotate_right(node.right)
            else:
                case = "RR"
            new_root = self._rotate_left(node)
        else:
            return node
        self.rotations_count[case] += 1
        self.rotation_log.append({
            "case": case,
            "node_id": node.key.event_id,
            "balance": balance,
            "new_root_id": new_root.key.event_id,
        })
        return new_root

    def _rebalance(self, node: Node) -> Node:
        """Apply AVL rotations when the subtree becomes unbalanced."""
        node.update_height()
        if self.stress_mode:
            return node
        return self._fix_balance(node)

    def insert(self, key: Key, value: Value) -> None:
        """Insert a node and rebalance the AVL tree."""
        self.root = self._insert(self.root, key, value)
        self.size += 1

    def set_stress_mode(self, enabled: bool) -> None:
        """Enable or disable deferred balancing for subsequent mutations."""
        if not isinstance(enabled, bool):
            raise TypeError("stress mode must be a boolean")
        self.stress_mode = enabled

    def enable_stress_mode(self) -> None:
        """Start a burst without rotations."""
        self.set_stress_mode(True)

    def disable_stress_mode(self, *, recover: bool = True) -> None:
        """End a burst and optionally restore the AVL invariant."""
        self.set_stress_mode(False)
        if recover:
            self.recover_balance()

    def recover_balance(self) -> dict[str, object]:
        """Recover the AVL property with rotations on the existing nodes.

        The specification forbids replacing the tree with one rebuilt from an
        ordered list. `_recover_subtree` works bottom-up: both children are
        made AVL first, then the root is rotated while it is unbalanced, and
        the subtrees touched by the rotation are recovered again. Rotations
        preserve the in-order sequence, so the BST order and every node
        identity are kept. Each rotation at the root strictly reduces the
        height difference between its children, and the recursion only
        descends into smaller subtrees, so the procedure terminates even
        with differences greater than 2. Returns the audit metrics plus the
        cases and rotations it applied (its cost).
        """
        self.stress_mode = False
        log_start = len(self.rotation_log)
        counts_before = dict(self.rotations_count)
        self.root = self._recover_subtree(self.root)
        metrics = self.audit()
        metrics["applied_cases"] = self.rotation_log[log_start:]
        metrics["rotation_delta"] = {
            name: self.rotations_count[name] - counts_before[name]
            for name in self.rotations_count
        }
        return metrics

    def _recover_subtree(self, node: Optional[Node]) -> Optional[Node]:
        """Return an AVL subtree with the same nodes and in-order sequence."""
        if node is None:
            return None
        node.left = self._recover_subtree(node.left)
        node.right = self._recover_subtree(node.right)
        node.update_height()
        while abs(node.balance_factor()) > 1:
            node = self._fix_balance(node)
            # The rotation may leave the demoted root unbalanced: repair the
            # two children of the new root, then re-check the root itself.
            node.left = self._recover_subtree(node.left)
            node.right = self._recover_subtree(node.right)
            node.update_height()
        return node

    def recover(self) -> dict[str, int]:
        """Compatibility alias for recovering a stressed tree."""
        return self.recover_balance()

    def rebalance_all(self) -> dict[str, int]:
        """Explicit name for the global recovery operation."""
        return self.recover_balance()

    def audit(self) -> dict[str, int]:
        """Validate ordering, stored heights and AVL balance.

        Raises ``AssertionError`` with a useful message when an invariant is
        broken.  The returned metrics are useful to the UI and tests.
        """
        nodes = self.inorder()
        keys = [node.key for node in nodes]
        assert keys == sorted(keys), "in-order keys are not sorted"
        assert len(nodes) == self.size, "tree size does not match node count"
        for node in nodes:
            expected = node.compute_height()
            assert node.height == expected, f"stale height for {node.key}"
            assert abs(node.balance_factor()) <= 1, f"unbalanced node {node.key}"
        return {
            "size": self.size,
            "height": self.get_height(),
            "leaves": self.count_leaves(),
            "rotations": elementary_rotations(self.rotations_count),
        }

    def is_balanced(self) -> bool:
        """Return whether all nodes currently satisfy the AVL invariant."""
        try:
            self.audit()
        except AssertionError:
            return False
        return True

    def get_height_node(self, node: Optional[Node]) -> int:
        return Node.height_of(node)

    def get_balance_factor(self, node: Optional[Node]) -> int:
        return 0 if node is None else node.balance_factor()

    def _insert(self, node: Optional[Node], key: Key, event: Value) -> Node:
        if node is None:
            return Node(key, event)

        if key == node.key:
            raise DuplicateKeyError(f"Key {key} already exists.")

        if key < node.key:
            node.left = self._insert(node.left, key, event)
        else:
            node.right = self._insert(node.right, key, event)

        return self._rebalance(node)

    def remove(self, key: Key) -> Optional[Value]:
        """Remove a key and keep the tree balanced."""
        return super().delete(key)

    def find(self, key: Key) -> Optional[Value]:
        """Return the stored value by key, or None when it is absent."""
        node, _ = self.search(key)
        return None if node is None else node.event

    def traverse_in_order(self) -> list[tuple[Key, Value]]:
        """Return entries in sorted key order."""
        return [(node.key, node.event) for node in self.inorder()]

    def breadthFirstSearch(self) -> list[Node]:
        """Compatibility alias used by the original student implementation."""
        return self.level_order()

    def calculateHeight(self, node: Optional[Node]) -> int:
        return -1 if node is None else node.compute_height()
