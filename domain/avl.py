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
    """Balance a BST by rebalancing after each recursive insert/delete."""

    def _rotate_left(self, node: Node) -> Node:
        """Rotate the subtree rooted at `node` to the left."""
        pivot = node.right
        if pivot is None:
            return node

        node.right = pivot.left
        pivot.left = node
        node.update_height()
        pivot.update_height()
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
        return pivot

    def _rebalance(self, node: Node) -> Node:
        """Apply AVL rotations when the subtree becomes unbalanced."""
        node.update_height()

        balance = node.balance_factor()
        if balance > 1:
            if node.left is not None and node.left.balance_factor() < 0:
                node.left = self._rotate_left(node.left)
            return self._rotate_right(node)

        if balance < -1:
            if node.right is not None and node.right.balance_factor() > 0:
                node.right = self._rotate_right(node.right)
            return self._rotate_left(node)

        return node

    def insert(self, key: Key, value: Value) -> None:
        """Insert a node and rebalance the AVL tree."""
        self.root = self._insert(self.root, key, value)
        self.size += 1

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
