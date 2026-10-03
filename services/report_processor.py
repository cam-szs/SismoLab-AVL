"""Process queued reports according to the SismoLab revision rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Set

from domain.event import Event
from domain.queue_fifo import ReportQueue
from domain.report import Report


@dataclass(frozen=True)
class ProcessResult:
    """Describe the decision made for one consumed report."""

    decision: str
    report: Report
    event: Optional[Event] = None
    previous_event: Optional[Event] = None
    message: str = ""


class ReportProcessor:
    """Maintain report state without owning AVL topology."""

    def __init__(
        self,
        active_events: Optional[Dict[int, Event]] = None,
        archived_events: Optional[Dict[int, Event]] = None,
        deleted_ids: Optional[Set[int]] = None,
        populated_zone: Optional[Callable[[Report], bool]] = None,
    ) -> None:
        self.active_events = active_events if active_events is not None else {}
        self.archived_events = archived_events if archived_events is not None else {}
        self.deleted_ids = deleted_ids if deleted_ids is not None else set()
        self._populated_zone = populated_zone or (lambda report: False)
        self.stats = {
            "created": 0,
            "corrections": 0,
            "confirmations": 0,
            "conflicts": 0,
            "stale": 0,
            "rejected_deleted": 0,
        }

    def process_next(self, queue: ReportQueue[Report]) -> ProcessResult:
        """Consume and resolve exactly one report from ``queue``."""
        report = queue.dequeue()

        if report.event_id in self.deleted_ids:
            self.stats["rejected_deleted"] += 1
            return ProcessResult(
                "rejected_deleted", report,
                message="the event identifier was permanently retired",
            )

        active = self.active_events.get(report.event_id)
        if active is not None:
            return self._process_against_active(report, active)

        archived = self.archived_events.get(report.event_id)
        if archived is not None:
            return self._process_against_archived(report, archived)

        event = self._event_from_report(report)
        self.active_events[event.event_id] = event
        self.stats["created"] += 1
        return ProcessResult(
            "created", report, event=event,
            message="unknown identifier registered as a new event",
        )

    def calculate_priority(self, report: Report) -> int:
        """Calculate report priority using the scenario zone classification."""
        return self._event_from_report(report).priority

    def archive(self, event_id: int) -> Event:
        """Move one active event to history without changing its identity."""
        event = self.active_events.pop(event_id)
        self.archived_events[event_id] = event
        return event

    def recover(self, event_id: int) -> Event:
        """Bring a previously archived event back into the active catalog."""
        if event_id not in self.archived_events:
            raise KeyError(f"event {event_id} is not archived")
        event = self.archived_events.pop(event_id)
        self.active_events[event_id] = event
        return event

    def delete(self, event_id: int) -> Event:
        """Retire one active event so later reports cannot reactivate it."""
        event = self.active_events.pop(event_id)
        self.deleted_ids.add(event_id)
        return event

    def _process_against_active(self, report: Report, current: Event) -> ProcessResult:
        incoming = self._event_from_report(report)

        if report.revision < current.revision:
            self.stats["stale"] += 1
            return ProcessResult(
                "stale", report, event=current,
                message="report revision is older than the active revision",
            )

        if report.revision == current.revision:
            if not current.same_physical_data(incoming):
                self.stats["conflicts"] += 1
                return ProcessResult(
                    "conflict", report, event=current,
                    message="same revision contains different physical data",
                )

            confirmed = current.with_station(report.station)
            self.active_events[current.event_id] = confirmed
            self.stats["confirmations"] += 1
            decision = "duplicate_confirmation" if confirmed is current else "confirmed"
            return ProcessResult(
                decision, report, event=confirmed, previous_event=current,
                message="matching revision confirmed the event",
            )

        corrected = current.corrected(
            populated_zone=self._populated_zone(report),
            new_revision=report.revision,
            stations=current.stations | {report.station},
            magnitude_tenths=report.magnitude_tenths,
            depth_tenths=report.depth_tenths,
            x_tenths=report.x_tenths,
            y_tenths=report.y_tenths,
            occurred_at=report.occurred_at,
        )
        self.active_events[current.event_id] = corrected
        self.stats["corrections"] += 1
        return ProcessResult(
            "corrected", report, event=corrected, previous_event=current,
            message="newer revision replaced the active data",
        )

    def _process_against_archived(self, report: Report, current: Event) -> ProcessResult:
        incoming = self._event_from_report(report)

        if report.revision > current.revision:
            reactivated = incoming.corrected(
                populated_zone=self._populated_zone(report),
                new_revision=report.revision,
                stations=current.stations | {report.station},
            )
            self.archived_events.pop(current.event_id)
            self.active_events[current.event_id] = reactivated
            self.stats["corrections"] += 1
            return ProcessResult(
                "reactivated", report, event=reactivated, previous_event=current,
                message="newer revision reactivated the archived event",
            )

        if report.revision == current.revision and current.same_physical_data(incoming):
            confirmed = current.with_station(report.station)
            self.archived_events[current.event_id] = confirmed
            self.stats["confirmations"] += 1
            return ProcessResult(
                "archived_confirmation", report, event=confirmed, previous_event=current,
                message="matching report confirmed archived data without reactivation",
            )

        decision = "conflict" if report.revision == current.revision else "stale"
        self.stats[decision] += 1
        return ProcessResult(
            decision, report, event=current,
            message="archived event was not reactivated by this report",
        )

    def _event_from_report(self, report: Report) -> Event:
        return report.to_event(populated_zone=self._populated_zone(report))
