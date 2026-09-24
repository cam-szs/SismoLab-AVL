"""[STUB - team must implement] AVL tree contract."""

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

Key = TypeVar("Key")
Value = TypeVar("Value")


@dataclass
class AVLNode(Generic[Key, Value]):
    """Store an AVL key, value, child links, and height."""

    key: Key
    value: Value
    left: Optional["AVLNode[Key, Value]"] = None
    right: Optional["AVLNode[Key, Value]"] = None
    height: int = 1


class AVLTree(Generic[Key, Value]):
    """Define an AVL tree whose balancing rules remain to be implemented."""

    def __init__(self) -> None:
        """Create an empty AVL tree."""
        self.root: Optional[AVLNode[Key, Value]] = None

    def insert(self, key: Key, value: Value) -> None:
        """Insert and rebalance using AVL rotations."""
        raise NotImplementedError("TODO: implement AVL insertion and rebalancing")

    def remove(self, key: Key) -> Value:
        """Remove a key and restore AVL balance after deletion."""
        raise NotImplementedError("TODO: implement AVL removal and rebalancing")

    def find(self, key: Key) -> Optional[Value]:
        """Find a value by key using the ordered tree invariant."""
        raise NotImplementedError("TODO: implement AVL search")

    def traverse_in_order(self) -> list[tuple[Key, Value]]:
        """Return entries in sorted-key order."""
        raise NotImplementedError("TODO: implement AVL in-order traversal")
