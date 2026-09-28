from __future__ import annotations

from typing import Any, Optional

from event import EventKey  # adjust to the module where EventKey lives


class Node:
    """
    Tree node shared by the AVL and the plain BST.

    It only stores structure (links and height) plus a reference to the
    event it represents. Depth and balance factor are derived, never stored.
    """

    __slots__ = ("key", "event", "left", "right", "height")

    def __init__(self, key: EventKey, event: Any = None) -> None:
        self.key: EventKey = key          # immutable: a key change = remove + reinsert
        self.event: Any = event           # domain data (Event) or None
        self.left: Optional[Node] = None
        self.right: Optional[Node] = None
        self.height: int = 0              # leaf = 0, empty tree = -1

    # ---------- height helpers ----------

    @staticmethod
    def height_of(node: Optional[Node]) -> int:
        """Height of a possibly-empty subtree (None -> -1)."""
        return -1 if node is None else node.height

    def update_height(self) -> None:
        """Recompute this node's height from its children.
        Call it bottom-up (child first, then parent) after any link change."""
        self.height = 1 + max(Node.height_of(self.left), Node.height_of(self.right))

    def compute_height(self) -> int:
        """Recursively recompute the real height, ignoring the stored value.
        Used by the audit. O(n) for the subtree."""
        lh = self.left.compute_height() if self.left else -1
        rh = self.right.compute_height() if self.right else -1
        return 1 + max(lh, rh)

    # ---------- balance ----------

    def balance_factor(self) -> int:
        """Left height minus right height, from the stored heights."""
        return Node.height_of(self.left) - Node.height_of(self.right)

    # ---------- structure ----------

    def is_leaf(self) -> bool:
        return self.left is None and self.right is None

    def child_count(self) -> int:
        return (self.left is not None) + (self.right is not None)

    # ---------- misc ----------

    @property
    def event_id(self) -> int:
        return self.key.event_id

    def __repr__(self) -> str:
        return f"Node(key={self.key}, h={self.height})"