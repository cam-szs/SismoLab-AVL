"""Process queued reports according to the SismoLab revision rules."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Optional, Set
from collections import deque
from datetime import datetime, timezone

from domain.avl import ROTATION_COUNTER_KEYS, AVLTree, elementary_rotations
from domain.bst import BSTree
from domain.event import Event
from domain.event_key import EventKey
from domain.queue_fifo import ReportQueue
from domain.node import Node
from domain.report import Report


# Magnitude interval (in tenths, inclusive) that each priority can contain.
# It follows from the mandatory priority rules: P1 means M < 4.5, P2 means
# 4.5 <= M < 6.0 and P3 means M >= 4.5 (populated) or M >= 6.0.
PRIORITY_MAGNITUDE_TENTHS = {1: (-20, 44), 2: (45, 59), 3: (45, 100)}


def _magnitude_span(lower: Optional[EventKey], upper: Optional[EventKey]) -> Optional[tuple[int, int]]:
    """Return the magnitudes a subtree can hold given its exclusive key bounds.

    Every key in the subtree satisfies lower < K < upper. Because P is the
    first key component, the subtree can only contain priorities between
    lower.P and upper.P, and inside the boundary priorities the magnitude is
    further limited by the bound's own magnitude. Returns None when no
    magnitude is possible.
    """
    p_min = lower.priority if lower is not None else 1
    p_max = upper.priority if upper is not None else 3
    span_min: Optional[int] = None
    span_max: Optional[int] = None
    for priority in range(p_min, p_max + 1):
        m_low, m_high = PRIORITY_MAGNITUDE_TENTHS[priority]
        if lower is not None and priority == lower.priority:
            m_low = max(m_low, lower.magnitude_tenths)
        if upper is not None and priority == upper.priority:
            m_high = min(m_high, upper.magnitude_tenths)
        if m_low > m_high:
            continue
        span_min = m_low if span_min is None else min(span_min, m_low)
        span_max = m_high if span_max is None else max(span_max, m_high)
    if span_min is None or span_max is None:
        return None
    return span_min, span_max


@dataclass(frozen=True)
class ProcessResult:
    """Describe the decision made for one consumed report."""

    decision: str
    report: Report
    event: Optional[Event] = None
    previous_event: Optional[Event] = None
    message: str = ""
    rotations: tuple = ()   # AVL balancing cases applied while resolving the report


# Counters that are part of the restorable state (section 14).
STAT_KEYS = (
    "created", "corrections", "confirmations", "conflicts", "stale",
    "rejected_deleted", "recoveries", "deletions", "archive_operations",
    "archived_events",
)


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
        self.bst = BSTree()
        for event in self.active_events.values():
            self.tree.insert(event.key, event)
            self.bst.insert(event.key, event)
        self.stats = dict.fromkeys(STAT_KEYS, 0)

    # ---------- restorable counters ----------

    def counters(self) -> dict[str, dict[str, int]]:
        """Counters saved with snapshots, versions and exported JSON."""
        return {"stats": dict(self.stats), "rotations": dict(self.tree.rotations_count)}

    def restore_counters(self, payload: Any) -> None:
        """Validate and restore counters from a snapshot (all or nothing)."""
        if not isinstance(payload, dict):
            raise ValueError("counters must be an object")
        restored: dict[str, dict[str, int]] = {}
        for group, keys in (("stats", STAT_KEYS), ("rotations", ROTATION_COUNTER_KEYS)):
            values = payload.get(group, {})
            if not isinstance(values, dict):
                raise ValueError(f"counters.{group} must be an object")
            restored[group] = {}
            for name in keys:
                value = values.get(name, 0)
                if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                    raise ValueError(f"counter {group}.{name} must be a non-negative integer")
                restored[group][name] = value
        self.stats = restored["stats"]
        self.tree.rotations_count = restored["rotations"]

    def indicators(self) -> dict[str, int]:
        """Section 14 indicators derived from the counters."""
        return {
            "accepted_corrections": self.stats["corrections"],
            "discarded_reports": self.stats["stale"] + self.stats["rejected_deleted"],
            "conflicts": self.stats["conflicts"],
            "archive_operations": self.stats["archive_operations"],
            "archived_events": self.stats["archived_events"],
        }

    def set_stress_mode(self, enabled: bool, *, recover: bool = True) -> dict[str, object]:
        """Toggle deferred AVL balancing and optionally recover on exit."""
        if enabled:
            self.tree.enable_stress_mode()
        else:
            self.tree.disable_stress_mode(recover=recover)
        return self.tree_metrics()

    def recover_balance(self) -> dict[str, object]:
        """Restore the AVL invariant after a stress burst.

        Returns the tree metrics plus the cost of the recovery: the cases
        applied (node, balance, new subtree root) and the rotation counts.
        """
        unbalanced_before = self.audit_report()["unbalanced_events"]
        report = self.tree.recover_balance()
        self.stats["recoveries"] += 1
        return {
            **self.tree_metrics(),
            "unbalanced_before": unbalanced_before,
            "applied_cases": report["applied_cases"],
            "rotation_delta": report["rotation_delta"],
        }

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
            "rotations": elementary_rotations(self.tree.rotations_count),
            "rotation_counts": self.tree.rotations_count.copy(),
            "depths": depths,
        }

    def bst_metrics(self) -> dict[str, object]:
        """Return structural metrics for the unrotated comparison BST."""
        return {
            "size": self.bst.size,
            "height": self.bst.get_height(),
            "leaves": self.bst.count_leaves(),
        }

    def bst_export(self) -> dict[str, object] | None:
        """Export the comparison BST topology (same insertions, no rotations)."""
        return self.bst.export_to_dict()

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
        self.bst.insert(event.key, event)
        self.active_events[event.event_id] = event

    def _replace_active(self, previous: Event, updated: Event) -> None:
        if previous.key != updated.key:
            self.tree.remove(previous.key)
            self.tree.insert(updated.key, updated)
            self.bst.delete(previous.key)
            self.bst.insert(updated.key, updated)
        else:
            self.tree.update_value(updated.key, updated)
            self.bst.update_value(updated.key, updated)
        self.active_events[updated.event_id] = updated

    def process_next(self, queue: ReportQueue[Report]) -> ProcessResult:
        """Consume and resolve exactly one report from ``queue``.

        The result carries the AVL balancing cases the step produced.
        """
        log_start = len(self.tree.rotation_log)
        result = self._resolve(queue.dequeue())
        return replace(result, rotations=tuple(self.tree.rotation_log[log_start:]))

    def _resolve(self, report: Report) -> ProcessResult:

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
        self.bst.delete(event.key)
        self.archived_events[event_id] = event
        self.stats["archived_events"] += 1
        return event

    def select_archive_branch(self, *, clock: datetime, age_hours: float) -> dict[str, object]:
        """Choose the branch to archive without modifying anything (preview).

        A subtree is eligible when all of its events have low priority and an
        age strictly greater than T. One post-order pass decides eligibility
        bottom-up in O(n). Among eligible branches the largest wins; ties go
        to the deepest root and then to the largest root id. The returned
        set is fixed from the topology at this moment.
        """
        candidates: list[dict[str, object]] = []

        def visit(node: Optional[Node], depth: int) -> tuple[bool, list[Event]]:
            if node is None:
                return True, []
            left_ok, left_events = visit(node.left, depth + 1)
            right_ok, right_events = visit(node.right, depth + 1)
            own = node.event
            age = (clock - own.occurred_at).total_seconds() / 3600
            eligible = left_ok and right_ok and own.priority == 1 and age > age_hours
            events = left_events + [own] + right_events
            if eligible:
                candidates.append({
                    "root_id": own.event_id,
                    "size": len(events),
                    "depth": depth,
                    "events": events,
                })
            return eligible, events

        visit(self.tree.root, 0)
        if not candidates:
            return {
                "root_id": None,
                "events": [],
                "eligible_branches": 0,
                "alternatives": [],
                "reason": "no eligible branch: every subtree has a non-low priority "
                          f"event or an event not older than {age_hours:g} h",
            }
        ranked = sorted(
            candidates,
            key=lambda item: (item["size"], item["depth"], item["root_id"]),
            reverse=True,
        )
        chosen = ranked[0]
        return {
            "root_id": chosen["root_id"],
            "events": chosen["events"],
            "eligible_branches": len(candidates),
            "alternatives": [
                {key: item[key] for key in ("root_id", "size", "depth")} for item in ranked[:5]
            ],
            "reason": (
                f"branch rooted at {chosen['root_id']} has {chosen['size']} node(s), all low "
                f"priority and older than {age_hours:g} h; chosen among {len(candidates)} "
                "eligible branch(es) by size, then deeper root, then larger root id"
            ),
        }

    def archive_branch(self, *, clock: datetime, age_hours: float) -> dict[str, object]:
        """Archive the branch chosen by `select_archive_branch` as one action.

        The set is computed before the tree changes, so the rotations done by
        each removal cannot add or drop events from it.
        """
        plan = self.select_archive_branch(clock=clock, age_hours=age_hours)
        events: list[Event] = plan["events"]
        log_start = len(self.tree.rotation_log)
        for event in events:
            self.active_events.pop(event.event_id, None)
            self.tree.remove(event.key)
            self.bst.delete(event.key)
            self.archived_events[event.event_id] = event
        if events:
            self.stats["archive_operations"] += 1
            self.stats["archived_events"] += len(events)
        return {
            **plan,
            "archived": events,
            "rotations": self.tree.rotation_log[log_start:],
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
        self.bst.delete(event.key)
        self.deleted_ids.add(event_id)
        self.stats["deletions"] += 1
        return event

    def is_registered(self, event_id: int) -> bool:
        """Whether the id belongs to an active, archived or deleted event."""
        return (
            event_id in self.active_events
            or event_id in self.archived_events
            or event_id in self.deleted_ids
        )

    def create(self, report: Report) -> Event:
        """Manually create an event as one action (section 6).

        The id must be new in the whole scenario, the revision starts at 1,
        the populated-zone flag and the priority are derived, and the event
        starts as pending. Nothing is modified when validation fails.
        """
        if self.is_registered(report.event_id):
            raise ValueError(
                f"event {report.event_id} already exists as {self.status_of(report.event_id)}"
            )
        if report.revision != 1:
            raise ValueError("a manually created event starts at revision 1")
        event = self._event_from_report(report)
        self._insert_active(event)
        self.stats["created"] += 1
        return event

    def correct(self, event_id: int, changes: dict[str, object]) -> Event:
        """Apply a direct correction while preserving the event identity.

        The revision becomes r + 1 even when the key does not change, the
        populated-zone flag is recomputed from the new epicenter, and the
        event goes back to pending. `corrected()` validates every value
        before the tree is touched, so an invalid correction leaves no
        partial state.
        """
        current = self.active_events.get(event_id)
        if current is None:
            raise KeyError(f"event {event_id} is not active")
        if "event_id" in changes or "id" in changes:
            raise ValueError("event id is immutable")
        if "populated_zone" in changes:
            raise ValueError("populated zone is derived from the epicenter and cannot be set")

        updated = current.corrected(
            populated_zone=current.populated_zone,
            stations=current.stations,
            **changes,
        )
        updated = replace(updated, populated_zone=self._populated_zone(updated))
        self._replace_active(current, updated)
        self.stats["corrections"] += 1
        return updated

    # ---------- lookup by identity ----------

    def status_of(self, event_id: int) -> str:
        """Return active, archived, deleted or unknown for an identifier."""
        if event_id in self.active_events:
            return "active"
        if event_id in self.archived_events:
            return "archived"
        if event_id in self.deleted_ids:
            return "deleted"
        return "unknown"

    def locate(self, event_id: int) -> tuple[Optional[Node], int]:
        """Find the AVL node of an active event by its identifier.

        The id is only the third key component, so the tree alone cannot be
        searched by id. The `active_events` hash index (id -> current Event)
        gives the current key in O(1) on average; the key is then searched in
        the AVL in O(h). Memory cost: one dictionary entry per active event.
        Returns (node, nodes visited) or (None, 0) when the id is not active.
        """
        event = self.active_events.get(event_id)
        if event is None:
            return None, 0
        return self.tree.search(event.key)

    # ---------- queries (section 11) ----------

    def query_top_pending(self, k: int) -> dict[str, Any]:
        """First k pending events in descending K order.

        Iterative reverse in-order traversal that stops as soon as k pending
        events were found. The attention status is not part of K, so no
        branch can be discarded: the worst case (few pending events) is O(n).
        """
        if not isinstance(k, int) or isinstance(k, bool) or k < 1:
            raise ValueError("k must be a positive integer")
        found: list[Event] = []
        examined = 0
        stack: list[Node] = []
        node = self.tree.root
        while (stack or node is not None) and len(found) < k:
            while node is not None:
                stack.append(node)
                node = node.right
            node = stack.pop()
            examined += 1
            if node.event.status.value == "pending":
                found.append(node.event)
            node = node.left
        return {"events": found, "nodes_examined": examined}

    def query_magnitude_range(self, min_tenths: int, max_tenths: int) -> dict[str, Any]:
        """Active events with min <= M <= max (inclusive), in ascending K order.

        M is the second key component, so the tree is not sorted by M alone.
        A subtree is still discarded without visiting it when its key bounds
        (inherited from the ancestors) make every possible magnitude fall
        outside the interval; see `_magnitude_span`. Worst case O(n).
        """
        if min_tenths > max_tenths:
            raise ValueError("minimum magnitude cannot be greater than maximum magnitude")
        found: list[Event] = []
        examined = 0

        def visit(node: Optional[Node], lower: Optional[EventKey], upper: Optional[EventKey]) -> None:
            nonlocal examined
            if node is None:
                return
            span = _magnitude_span(lower, upper)
            if span is None or span[1] < min_tenths or span[0] > max_tenths:
                return
            examined += 1
            visit(node.left, lower, node.key)
            if min_tenths <= node.event.magnitude_tenths <= max_tenths:
                found.append(node.event)
            visit(node.right, node.key, upper)

        visit(self.tree.root, None, None)
        return {"events": found, "nodes_examined": examined}

    def query_depth_and_dates(
        self, max_depth_tenths: int, start: datetime, end: datetime
    ) -> dict[str, Any]:
        """Active events with H <= limit and start <= occurrence <= end.

        Neither hypocenter depth nor time is part of K, so no branch can be
        discarded and every node is examined: O(n).
        """
        if start > end:
            raise ValueError("start date cannot be after end date")
        found = [
            node.event
            for node in self.tree.inorder()
            if node.event.depth_tenths <= max_depth_tenths
            and start <= node.event.occurred_at <= end
        ]
        return {"events": found, "nodes_examined": self.tree.size}

    def mark_reviewed(self, event_id: int) -> Event:
        """Mark an active event reviewed without changing its AVL key.

        Only a pending event can be reviewed; a later accepted correction
        returns it to pending so it can be reviewed again.
        """
        current = self.active_events.get(event_id)
        if current is None:
            raise KeyError(f"event {event_id} is not active")
        if current.status.value == "reviewed":
            raise ValueError(f"event {event_id} is already reviewed")
        updated = current.mark_reviewed()
        self.tree.update_value(current.key, updated)
        self.bst.update_value(current.key, updated)
        self.active_events[event_id] = updated
        return updated

    def audit_report(self) -> dict[str, object]:
        """Verify the active AVL and report one entry per inconsistent event.

        Checks, in one O(n) post-order pass with inherited key bounds:
        - global order: every key lies strictly between the bounds set by all
          its ancestors (not only its parent);
        - uniqueness: each id appears once and is not also archived/deleted;
        - references: node key == key derived from the event, the event is
          the one indexed by id, and every indexed event is in the tree;
        - stored height == recomputed height (empty = -1, leaf = 0);
        - balance factor in {-1, 0, 1}. In stress mode an imbalance is
          reported as expected, separately from order or metadata errors.
        """
        issues: list[dict[str, object]] = []
        unbalanced: list[int] = []
        seen: set[int] = set()

        def report(event_id: int, kind: str, detail: str) -> None:
            issues.append({"event_id": event_id, "kind": kind, "detail": detail})

        def visit(node: Optional[Node], lower: Optional[EventKey], upper: Optional[EventKey]) -> int:
            if node is None:
                return -1
            event_id = node.key.event_id
            if lower is not None and not node.key > lower:
                report(event_id, "order", f"key {node.key} is not greater than ancestor bound {lower}")
            if upper is not None and not node.key < upper:
                report(event_id, "order", f"key {node.key} is not smaller than ancestor bound {upper}")
            if event_id in seen:
                report(event_id, "uniqueness", "identifier appears in more than one node")
            seen.add(event_id)
            event = node.event
            if not isinstance(event, Event) or event.event_id != event_id:
                report(event_id, "reference", "node does not reference the event with its id")
            else:
                if node.key != event.key:
                    report(event_id, "reference", f"node key {node.key} differs from derived key {event.key}")
                if self.active_events.get(event_id) is not event:
                    report(event_id, "reference", "node event is not the one indexed as active")
                if event_id in self.archived_events or event_id in self.deleted_ids:
                    report(event_id, "uniqueness", "identifier is also archived or deleted")
            left_height = visit(node.left, lower, node.key)
            right_height = visit(node.right, node.key, upper)
            height = 1 + max(left_height, right_height)
            if node.height != height:
                report(event_id, "height", f"stored height {node.height}, recomputed {height}")
            balance = left_height - right_height
            if abs(balance) > 1:
                unbalanced.append(event_id)
                report(
                    event_id,
                    "balance_expected" if self.tree.stress_mode else "balance",
                    f"balance factor {balance}",
                )
            return height

        visit(self.tree.root, None, None)
        for event_id in sorted(set(self.active_events) - seen):
            report(event_id, "reference", "active event is missing from the AVL")
        if len(seen) != self.tree.size:
            report(0, "metadata", f"stored size {self.tree.size}, counted {len(seen)} nodes")

        structural = [item for item in issues if not item["kind"].startswith("balance")]
        return {
            "valid_order": not any(item["kind"] == "order" for item in issues),
            "metadata_errors": [
                f"event {item['event_id']}: {item['kind']}: {item['detail']}" for item in structural
            ],
            "issues": issues,
            "unbalanced_events": unbalanced,
            "expected_unbalance": self.tree.stress_mode,
            "nodes_checked": len(seen),
            "balanced": not unbalanced and not structural,
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
