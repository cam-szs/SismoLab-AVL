"""AVL tree implementation on top of the BST contract."""

from __future__ import annotations

from typing import Generic, Optional, TypeVar

from .bst import BSTree, DuplicateKeyError
from .node import Node

Key = TypeVar("Key")
Value = TypeVar("Value")

# Backwards-compatible alias used by the project skeleton.
AVLNode = Node


class AVLTree(BSTree, Generic[Key, Value]):
    """Balance a BST, with an optional deferred-balancing stress mode.

    Stress mode is intended for a burst of inserts/deletes: structural
    operations keep the BST ordering and stored heights correct, but defer
    rotations until :meth:`recover_balance` is called.
    """

    def __init__(self, *, stress_mode: bool = False) -> None:
        super().__init__()
        self.stress_mode = stress_mode
        self.rotations_count = {
            "single_left": 0,
            "single_right": 0,
            "double_left": 0,
            "double_right": 0,
        }

    def _rotate_left(self, node: Node) -> Node:
        """Rotate the subtree rooted at `node` to the left."""
        pivot = node.right
        if pivot is None:
            return node

        node.right = pivot.left
        pivot.left = node
        node.update_height()
        pivot.update_height()
        self.rotations_count["single_left"] += 1
        return pivot

    def _rotate_right(self, node: Node) -> Node:
        """Rotate the subtree rooted at `node` to the right."""
        pivot = node.left
        if pivot is None:
            return node

        node.left = pivot.right
        pivot.right = node
        node.update_height()
        pivot.update_height()
        self.rotations_count["single_right"] += 1
        return pivot

    def _rebalance(self, node: Node) -> Node:
        """Apply AVL rotations when the subtree becomes unbalanced."""
        node.update_height()
        if self.stress_mode:
            return node

        balance = node.balance_factor()
        if balance > 1:
            if node.left is not None and node.left.balance_factor() < 0:
                node.left = self._rotate_left(node.left)
                self.rotations_count["double_right"] += 1
            return self._rotate_right(node)

        if balance < -1:
            if node.right is not None and node.right.balance_factor() > 0:
                node.right = self._rotate_right(node.right)
                self.rotations_count["double_left"] += 1
            return self._rotate_left(node)

        return node

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

    def recover_balance(self) -> dict[str, int]:
        """Recover balance using rotations on the existing tree.

        The academic specification forbids replacing the tree with a new
        balanced tree built from an ordered list. Repeated post-order
        rotations preserve every existing node and its identity.
        """
        self.stress_mode = False
        while self.root is not None and not self.is_balanced():
            self.root = self._recover_subtree(self.root)
        return self.audit()

    def _recover_subtree(self, node: Node) -> Node:
        """Rotate an unbalanced subtree after recovering both children."""
        if node.left is not None:
            node.left = self._recover_subtree(node.left)
        if node.right is not None:
            node.right = self._recover_subtree(node.right)
        node.update_height()
        balance = node.balance_factor()
        if balance > 1:
            if node.left is not None and node.left.balance_factor() < 0:
                node.left = self._rotate_left(node.left)
                self.rotations_count["double_right"] += 1
            return self._rotate_right(node)
        if balance < -1:
            if node.right is not None and node.right.balance_factor() > 0:
                node.right = self._rotate_right(node.right)
                self.rotations_count["double_left"] += 1
            return self._rotate_left(node)
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
            "rotations": sum(self.rotations_count.values()),
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
