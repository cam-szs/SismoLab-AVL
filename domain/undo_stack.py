"""[BOILERPLATE - implemented] Linked undo stack and snapshots."""

from dataclasses import dataclass, field
from typing import Any, Generic, Optional, TypeVar

Item = TypeVar("Item")


@dataclass
class Snapshot:
    """Capture serializable state needed for one undo version."""

    label: str
    state: dict[str, Any] = field(default_factory=dict)


@dataclass
class _StackNode(Generic[Item]):
    """Hold one stack item and its predecessor."""

    value: Item
    next: Optional["_StackNode[Item]"] = None


class UndoStack(Generic[Item]):
    """Provide LIFO snapshot storage backed by linked nodes."""

    def __init__(self) -> None:
        """Create an empty undo stack."""
        self._top: Optional[_StackNode[Item]] = None
        self._size = 0

    def push(self, value: Item) -> None:
        """Place a snapshot on top of the stack."""
        self._top = _StackNode(value, self._top)
        self._size += 1

    def pop(self) -> Item:
        """Remove and return the latest snapshot."""
        if self._top is None:
            raise IndexError("pop from empty undo stack")
        value = self._top.value
        self._top = self._top.next
        self._size -= 1
        return value

    def peek(self) -> Item:
        """Return the latest snapshot without removing it."""
        if self._top is None:
            raise IndexError("peek from empty undo stack")
        return self._top.value

    def __len__(self) -> int:
        """Return the number of snapshots."""
        return self._size
