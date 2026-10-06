# bst.py
from __future__ import annotations

import sys
from typing import Any, List, Optional, Tuple

from .event_key import EventKey
from .node import Node


class DuplicateKeyError(Exception):
    """Raised when a full BST key already exists in the tree.

    This is an internal structural guard, not the project-level validation for
    "event-id already exists". The business rule is enforced at the service
    layer by checking an id -> Event index before calling tree.insert().
    """


# The operations are recursive and a BST fed in ascending order has depth n,
# so the default limit (1000) is raised to support the comparison scenarios.
if sys.getrecursionlimit() < 20_000:
    sys.setrecursionlimit(20_000)

_MISSING = object()  # sentinel: "key not found" (an event may legitimately be None)


class BSTree:
    """
    Plain binary search tree (no rotations), recursive implementation.
    Stored heights are kept up to date. AVLTree extends this class and
    overrides `_rebalance`.

    Note: a degenerate tree (e.g. ascending insertion order) has depth n;
    the recursion limit is raised when this module is imported.
    """

    def __init__(self) -> None:
        self.root: Optional[Node] = None
        self.size: int = 0

    # ---------- hook (AVL overrides this) ----------

    def _rebalance(self, node: Node) -> Node:
        """Called on the way back up after an insert/delete below `node`.
        Returns the root of the subtree. The BST only refreshes the height."""
        node.update_height()
        return node

    # ---------- insert ----------

    def insert(self, key: EventKey, event: Any) -> None:
        """Insert a real event under a valid tree key.

        The business rule "id already exists" is validated before this method is
        called by the service layer; this method only guards the tree invariant.
        """
        self.root = self._insert(self.root, key, event)  # raises before size changes
        self.size += 1

    def _insert(self, node: Optional[Node], key: EventKey, event: Any) -> Node:
        if node is None:
            return Node(key, event)
        if key == node.key:
            raise DuplicateKeyError(f"Key {key} already exists.")
        if key < node.key:
            node.left = self._insert(node.left, key, event)
        else:
            node.right = self._insert(node.right, key, event)
        return self._rebalance(node)

    # ---------- search ----------

    def search(self, key: EventKey) -> Tuple[Optional[Node], int]:
        """Return (node or None, number of nodes visited)."""
        return self._search(self.root, key, 0)

    def update_value(self, key: EventKey, value: Any) -> None:
        """Replace the value stored at an existing key without changing structure."""
        node, _ = self.search(key)
        if node is None:
            raise KeyError(f"Key {key} not found.")
        node.event = value

    def _search(self, node: Optional[Node], key: EventKey,
                visited: int) -> Tuple[Optional[Node], int]:
        if node is None:
            return None, visited
        visited += 1
        if key == node.key:
            return node, visited
        child = node.left if key < node.key else node.right
        return self._search(child, key, visited)

    # ---------- delete ----------

    def delete(self, key: EventKey) -> Optional[Any]:
        """Remove the node with `key`. Returns the removed event,
        or None if the key does not exist."""
        self.root, removed = self._delete(self.root, key)
        if removed is _MISSING:
            return None
        self.size -= 1
        return removed

    def _delete(self, node: Optional[Node], key: EventKey) -> Tuple[Optional[Node], Any]:
        if node is None:
            return None, _MISSING

        if key < node.key:
            node.left, removed = self._delete(node.left, key)
        elif key > node.key:
            node.right, removed = self._delete(node.right, key)
        else:
            removed = node.event
            if node.left is None:
                return node.right, removed
            if node.right is None:
                return node.left, removed
            # Two children: the in-order predecessor (largest key of the left
            # subtree) takes this node's place. The predecessor node itself is
            # relinked, not copied, so every node keeps its own event.
            new_left, predecessor = self._detach_max(node.left)
            predecessor.left = new_left
            predecessor.right = node.right
            return self._rebalance(predecessor), removed

        if removed is _MISSING:
            return node, removed          # nothing changed, no rebalance needed
        return self._rebalance(node), removed

    def _detach_max(self, node: Node) -> Tuple[Optional[Node], Node]:
        """Unlink the largest node of a subtree.

        Returns (subtree without it, the detached node). The path back up is
        rebalanced, so in the AVL every subtree on that path stays valid.
        """
        if node.right is None:
            return node.left, node
        node.right, maximum = self._detach_max(node.right)
        return self._rebalance(node), maximum

    # ---------- traversals (recursive, return lists of nodes) ----------

    def inorder(self) -> List[Node]:
        out: List[Node] = []
        self._inorder(self.root, out)
        return out

    def _inorder(self, node: Optional[Node], out: List[Node]) -> None:
        if node is None:
            return
        self._inorder(node.left, out)
        out.append(node)
        self._inorder(node.right, out)

    def reverse_inorder(self) -> List[Node]:
        """Descending keys (useful for 'top k by K')."""
        out: List[Node] = []
        self._reverse_inorder(self.root, out)
        return out

    def _reverse_inorder(self, node: Optional[Node], out: List[Node]) -> None:
        if node is None:
            return
        self._reverse_inorder(node.right, out)
        out.append(node)
        self._reverse_inorder(node.left, out)

    def preorder(self) -> List[Node]:
        out: List[Node] = []
        self._preorder(self.root, out)
        return out

    def _preorder(self, node: Optional[Node], out: List[Node]) -> None:
        if node is None:
            return
        out.append(node)
        self._preorder(node.left, out)
        self._preorder(node.right, out)

    def postorder(self) -> List[Node]:
        out: List[Node] = []
        self._postorder(self.root, out)
        return out

    def _postorder(self, node: Optional[Node], out: List[Node]) -> None:
        if node is None:
            return
        self._postorder(node.left, out)
        self._postorder(node.right, out)
        out.append(node)

    def level_order(self) -> List[Node]:
        """Breadth-first traversal (naturally iterative, uses a queue)."""
        from collections import deque
        out: List[Node] = []
        queue = deque([self.root] if self.root else [])
        while queue:
            node = queue.popleft()
            out.append(node)
            if node.left:
                queue.append(node.left)
            if node.right:
                queue.append(node.right)
        return out

    def breadth_first_search(self) -> List[Node]:
        """Return nodes in breadth-first order.

        This is the canonical breadth-first alias; the typoed variant is not
        kept because it duplicates the same behavior and adds ambiguity.
        """
        return self.level_order()

    # ---------- metrics ----------

    def get_height(self) -> int:
        """Stored height of the root (empty = -1, leaf = 0). O(1)."""
        return Node.height_of(self.root)

    def count_leaves(self) -> int:
        return self._count_leaves(self.root)

    def _count_leaves(self, node: Optional[Node]) -> int:
        if node is None:
            return 0
        if node.is_leaf():
            return 1
        return self._count_leaves(node.left) + self._count_leaves(node.right)

    # ---------- export ----------

    def export_to_dict(self) -> Optional[dict[str, Any]]:
        """Export structure, height and balance factor for visualization."""
        return self._export_node_to_dict(self.root)

    def _export_node_to_dict(self, node: Optional[Node]) -> Optional[dict[str, Any]]:
        if node is None:
            return None
        event = (
            node.event.to_dict() if hasattr(node.event, "to_dict") else node.event
        )
        return {
            "key": {
                "priority": node.key.priority,
                "magnitude_tenths": node.key.magnitude_tenths,
                "event_id": node.key.event_id,
            },
            "event": event,
            "height": node.height,
            "factor_balanceo": node.balance_factor(),
            "izquierdo": self._export_node_to_dict(node.left),
            "derecho": self._export_node_to_dict(node.right),
        }

    def __len__(self) -> int:
        return self.size