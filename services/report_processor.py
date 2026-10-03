"""Process queued reports according to the SismoLab revision rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Optional, Set
from collections import deque
from datetime import datetime, timezone

from domain.avl import AVLTree
from domain.event import Event
from domain.event_key import EventKey
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
    """Maintain report state and its AVL-backed active-event topology."""

    def __init__(
        self,
        active_events: Optional[Dict[int, Event]] = None,
        archived_events: Optional[Dict[int, Event]] = None,
        deleted_ids: Optional[Set[int]] = None,
        populated_zone: Optional[Callable[[Report], bool]] = None,
        stress_mode: bool = False,
    ) -> None:
        self.active_events = active_events if active_events is not None else {}
        self.archived_events = archived_events if archived_events is not None else {}
        self.deleted_ids = deleted_ids if deleted_ids is not None else set()
        self._populated_zone = populated_zone or (lambda report: False)
        self.tree = AVLTree[EventKey, Event](stress_mode=stress_mode)
        for event in self.active_events.values():
            self.tree.insert(event.key, event)
        self.stats = {
            "created": 0,
            "corrections": 0,
            "confirmations": 0,
            "conflicts": 0,
            "stale": 0,
            "rejected_deleted": 0,
            "recoveries": 0,
        }

    def set_stress_mode(self, enabled: bool, *, recover: bool = True) -> dict[str, object]:
        """Toggle deferred AVL balancing and optionally recover on exit."""
        if enabled:
            self.tree.enable_stress_mode()
        else:
            self.tree.disable_stress_mode(recover=recover)
        return self.tree_metrics()

    def recover_balance(self) -> dict[str, object]:
        """Restore the AVL invariant after a stress burst."""
        self.tree.recover_balance()
        self.stats["recoveries"] += 1
        return self.tree_metrics()

    def tree_metrics(self) -> dict[str, object]:
        """Return structural AVL metrics without hiding stress-mode imbalance."""
        try:
            balanced = self.tree.is_balanced()
        except AssertionError:
            balanced = False
        depths: dict[int, int] = {}
        expensive: list[int] = []
        if self.tree.root is not None:
            pending = deque([(self.tree.root, 0)])
            while pending:
                node, depth = pending.popleft()
                depths[node.event.event_id] = depth
                if node.left is not None:
                    pending.append((node.left, depth + 1))
                if node.right is not None:
                    pending.append((node.right, depth + 1))
        return {
            "size": self.tree.size,
            "height": self.tree.get_height(),
            "leaves": self.tree.count_leaves(),
            "balanced": balanced,
            "stress_mode": self.tree.stress_mode,
            "rotations": sum(self.tree.rotations_count.values()),
            "rotation_counts": self.tree.rotations_count.copy(),
            "depths": depths,
        }

    def query_expensive_access(self, depth_limit: int) -> list[dict[str, object]]:
        """Return high-priority active events deeper than ``depth_limit``."""
        metrics = self.tree_metrics()
        depths = metrics["depths"]
        return [
            {
                "event": event,
                "depth": depths[event.event_id],
                "visited": depths[event.event_id] + 1,
            }
            for event in self.active_events.values()
            if event.priority == 3 and depths.get(event.event_id, 0) > depth_limit
        ]

    def _insert_active(self, event: Event) -> None:
        self.tree.insert(event.key, event)
        self.active_events[event.event_id] = event

    def _replace_active(self, previous: Event, updated: Event) -> None:
        if previous.key != updated.key:
            self.tree.remove(previous.key)
            self.tree.insert(updated.key, updated)
        else:
            self.tree.update_value(updated.key, updated)
        self.active_events[updated.event_id] = updated

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
        self._insert_active(event)
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
        self.tree.remove(event.key)
        self.archived_events[event_id] = event
        return event

    def archive_branch(
        self,
        *,
        clock: datetime,
        age_hours: float,
    ) -> dict[str, object]:
        """Archive the largest eligible subtree from the current topology."""
        if self.tree.root is None:
            return {"archived": [], "root_id": None, "reason": "empty tree"}

        candidates: list[tuple[int, int, int, list[Event]]] = []

        def visit(node, depth: int) -> tuple[bool, list[Event]]:
            if node is None:
                return True, []
            left_ok, left_events = visit(node.left, depth + 1)
            right_ok, right_events = visit(node.right, depth + 1)
            own = node.event
            age = (clock - own.occurred_at).total_seconds() / 3600
            eligible = (
                left_ok
                and right_ok
                and own.priority == 1
                and age > age_hours
            )
            events = left_events + [own] + right_events
            if eligible:
                candidates.append((len(events), depth, own.event_id, list(events)))
            return eligible, events

        visit(self.tree.root, 0)
        if not candidates:
            return {"archived": [], "root_id": None, "reason": "no eligible branch"}
        _, _, root_id, events = max(candidates, key=lambda item: (item[0], item[1], item[2]))
        for event in events:
            self.active_events.pop(event.event_id, None)
            self.tree.remove(event.key)
            self.archived_events[event.event_id] = event
        return {
            "archived": events,
            "root_id": root_id,
            "reason": "largest eligible branch",
        }

    def recover(self, event_id: int) -> Event:
        """Bring a previously archived event back into the active catalog."""
        if event_id not in self.archived_events:
            raise KeyError(f"event {event_id} is not archived")
        event = self.archived_events.pop(event_id)
        self._insert_active(event)
        return event

    def delete(self, event_id: int) -> Event:
        """Retire one active event so later reports cannot reactivate it."""
        event = self.active_events.pop(event_id)
        self.tree.remove(event.key)
        self.deleted_ids.add(event_id)
        return event

    def correct(self, event_id: int, changes: dict[str, object]) -> Event:
        """Apply a direct correction while preserving the event identity."""
        current = self.active_events.get(event_id)
        if current is None:
            raise KeyError(f"event {event_id} is not active")
        if "event_id" in changes or "id" in changes:
            raise ValueError("event id is immutable")

        payload = {
            "populated_zone": current.populated_zone,
            "stations": current.stations,
            **changes,
        }
        updated = current.corrected(**payload)
        self._replace_active(current, updated)
        self.stats["corrections"] += 1
        return updated

    def mark_reviewed(self, event_id: int) -> Event:
        """Mark an active event reviewed without changing its AVL key."""
        current = self.active_events.get(event_id)
        if current is None:
            raise KeyError(f"event {event_id} is not active")
        updated = current.mark_reviewed()
        self.tree.update_value(current.key, updated)
        self.active_events[event_id] = updated
        return updated

    def audit_report(self) -> dict[str, object]:
        """Return structural errors while distinguishing expected stress imbalance."""
        errors: list[str] = []
        nodes = self.tree.inorder()
        keys = [node.key for node in nodes]
        if keys != sorted(keys):
            errors.append("in-order keys are not sorted")
        if len(nodes) != self.tree.size:
            errors.append("tree size does not match node count")
        unbalanced: list[int] = []
        for node in nodes:
            expected = node.compute_height()
            if node.height != expected:
                errors.append(f"stale height for {node.event.event_id}")
            if abs(node.balance_factor()) > 1:
                unbalanced.append(node.event.event_id)
        return {
            "valid_order": not any("keys" in error for error in errors),
            "metadata_errors": errors,
            "unbalanced_events": unbalanced,
            "expected_unbalance": self.tree.stress_mode,
            "balanced": not unbalanced and not errors,
        }

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
            self._replace_active(current, confirmed)
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
        self._replace_active(current, corrected)
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
            self._insert_active(reactivated)
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
