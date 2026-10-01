"""[BOILERPLATE - implemented] Minimal smoke tests for mechanical utilities."""

from datetime import datetime, timezone

import pytest

from domain.report import Report
from domain.queue_fifo import ReportQueue
from domain.undo_stack import UndoStack
from services.report_processor import ReportProcessor


REPORT_TIME = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


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


def test_report_converts_to_pending_event() -> None:
    report = Report.create(7, 5.2, 10.0, 3.0, 4.0, REPORT_TIME, "  ST-01  ", revision=3)

    event = report.to_event()

    assert report.station == "ST-01"
    assert event.event_id == 7
    assert event.magnitude == 5.2
    assert event.revision == 3
    assert event.stations == frozenset({"ST-01"})


def test_report_rejects_precision_and_empty_station() -> None:
    with pytest.raises(ValueError, match="at most one decimal"):
        Report.create(7, 5.25, 10.0, 3.0, 4.0, REPORT_TIME, "ST-01")

    with pytest.raises(ValueError, match="non-empty"):
        Report.create(7, 5.2, 10.0, 3.0, 4.0, REPORT_TIME, "   ")


def make_report(event_id: int, revision: int, magnitude: float, station: str) -> Report:
    return Report.create(
        event_id, magnitude, 5.0, 10.0, 20.0, REPORT_TIME, station, revision=revision
    )


def test_report_processor_resolves_revision_states() -> None:
    queue = ReportQueue[Report]()
    processor = ReportProcessor()

    queue.enqueue(make_report(10, 1, 4.8, "A"))
    assert processor.process_next(queue).decision == "created"

    queue.enqueue(make_report(10, 1, 4.8, "B"))
    confirmation = processor.process_next(queue)
    assert confirmation.decision == "confirmed"
    assert processor.active_events[10].stations == frozenset({"A", "B"})

    queue.enqueue(make_report(10, 1, 5.0, "C"))
    assert processor.process_next(queue).decision == "conflict"
    assert processor.active_events[10].magnitude == 4.8

    queue.enqueue(make_report(10, 2, 6.2, "C"))
    correction = processor.process_next(queue)
    assert correction.decision == "corrected"
    assert processor.active_events[10].revision == 2
    assert processor.active_events[10].magnitude == 6.2

    queue.enqueue(make_report(10, 1, 4.8, "D"))
    assert processor.process_next(queue).decision == "stale"


def test_report_processor_rejects_deleted_ids_and_reactivates_archive() -> None:
    queue = ReportQueue[Report]()
    processor = ReportProcessor()

    queue.enqueue(make_report(20, 1, 4.0, "A"))
    processor.process_next(queue)
    archived = processor.archive(20)

    queue.enqueue(make_report(20, 1, 4.0, "B"))
    assert processor.process_next(queue).decision == "archived_confirmation"
    assert 20 not in processor.active_events
    assert processor.archived_events[20].stations == frozenset({"A", "B"})

    queue.enqueue(make_report(20, 2, 6.1, "C"))
    assert processor.process_next(queue).decision == "reactivated"
    assert processor.active_events[20].revision == 2
    assert processor.active_events[20].stations == frozenset({"A", "B", "C"})
    assert archived.event_id == 20

    processor.delete(20)
    queue.enqueue(make_report(20, 3, 7.0, "D"))
    assert processor.process_next(queue).decision == "rejected_deleted"


def test_report_processor_uses_inclusive_populated_zone_priority() -> None:
    report = Report.create(30, 4.5, 30.0, 10.0, 20.0, REPORT_TIME, "A")
    processor = ReportProcessor(populated_zone=lambda candidate: candidate.event_id == 30)

    assert processor.calculate_priority(report) == 3
