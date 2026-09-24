"""[BOILERPLATE - implemented] Linked FIFO report queue."""

from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

Item = TypeVar("Item")


@dataclass
class _QueueNode(Generic[Item]):
    """Hold one queue item and its successor."""

    value: Item
    next: Optional["_QueueNode[Item]"] = None


class ReportQueue(Generic[Item]):
    """Provide FIFO operations backed by linked nodes."""

    def __init__(self) -> None:
        """Create an empty report queue."""
        self._front: Optional[_QueueNode[Item]] = None
        self._rear: Optional[_QueueNode[Item]] = None
        self._size = 0

    def enqueue(self, value: Item) -> None:
        """Add an item at the rear."""
        node = _QueueNode(value)
        if self._rear is None:
            self._front = node
        else:
            self._rear.next = node
        self._rear = node
        self._size += 1

    def dequeue(self) -> Item:
        """Remove and return the oldest item."""
        if self._front is None:
            raise IndexError("dequeue from empty report queue")
        value = self._front.value
        self._front = self._front.next
        self._size -= 1
        if self._front is None:
            self._rear = None
        return value

    def __len__(self) -> int:
        """Return the number of queued items."""
        return self._size

    def is_empty(self) -> bool:
        """Return whether the queue is empty."""
        return self._size == 0
