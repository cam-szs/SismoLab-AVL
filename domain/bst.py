"""[STUB - team must implement] Binary search tree contract."""

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

Key = TypeVar("Key")
Value = TypeVar("Value")


@dataclass
class BSTNode(Generic[Key, Value]):
    """Store a BST key, value, and child links."""

    key: Key
    value: Value
    left: Optional["BSTNode[Key, Value]"] = None
    right: Optional["BSTNode[Key, Value]"] = None


class BSTTree(Generic[Key, Value]):
    """Define a binary search tree contract for comparison views."""

    def __init__(self) -> None:
        """Create an empty binary search tree."""
        self.root: Optional[BSTNode[Key, Value]] = None

    def insert(self, key: Key, value: Value) -> None:
        """Insert according to the BST ordering rule."""
        raise NotImplementedError("TODO: implement BST insertion")

    def remove(self, key: Key) -> Value:
        """Remove a key while preserving the BST ordering rule."""
        raise NotImplementedError("TODO: implement BST removal")

    def find(self, key: Key) -> Optional[Value]:
        """Find a value by key."""
        raise NotImplementedError("TODO: implement BST search")
