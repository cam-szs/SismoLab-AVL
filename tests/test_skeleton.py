"""[BOILERPLATE - implemented] Minimal smoke tests for mechanical utilities."""

from sismolab_avl.domain.queue_fifo import ReportQueue
from sismolab_avl.domain.undo_stack import UndoStack


def test_report_queue_is_fifo() -> None:
    """Verify the linked queue's mechanical FIFO behavior."""
    queue = ReportQueue[int]()
    queue.enqueue(1)
    queue.enqueue(2)
    assert queue.dequeue() == 1


def test_undo_stack_is_lifo() -> None:
    """Verify the linked stack's mechanical LIFO behavior."""
    stack = UndoStack[int]()
    stack.push(1)
    stack.push(2)
    assert stack.pop() == 2
