# event.py
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, Optional

from event_key import EventKey  # adjust to the module where EventKey lives


class AttentionStatus(str, Enum):
    PENDING = "pending"
    REVIEWED = "reviewed"


def _to_tenths(value: float, name: str) -> int:
    """Convert a decimal with at most one decimal place to integer tenths."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a number")
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")
    tenths = round(value * 10)
    if abs(value * 10 - tenths) > 1e-9:
        raise ValueError(f"{name} must have at most one decimal")
    return tenths


@dataclass(frozen=True)
class Event:
    """
    Immutable snapshot of an earthquake's current data.

    Corrections never mutate an Event: they produce a new one (see `corrected`),
    so snapshots used by undo/versions can safely share instances.
    Quantities are stored as integer tenths to keep comparisons exact.
    """

    event_id: int                       # 1..999999, immutable identity
    magnitude_tenths: int               # -20..100  (M * 10)
    depth_tenths: int                   # 0..7000   (H * 10, hypocenter depth in km)
    x_tenths: int                       # 0..10000  (epicenter x in km * 10)
    y_tenths: int                       # 0..10000  (epicenter y in km * 10)
    occurred_at: datetime               # UTC, second precision
    revision: int = 1                   # positive, global per event
    stations: FrozenSet[str] = frozenset()   # stations with accepted reports
    status: AttentionStatus = AttentionStatus.PENDING
    populated_zone: bool = False        # derived from the scenario zones by the caller

    # ---------- construction / validation ----------

    def __post_init__(self) -> None:
        if not (1 <= self.event_id <= 999_999):
            raise ValueError("id must be between 1 and 999999")
        if not (-20 <= self.magnitude_tenths <= 100):
            raise ValueError("magnitude must be between -2.0 and 10.0")
        if not (0 <= self.depth_tenths <= 7000):
            raise ValueError("depth must be between 0.0 and 700.0 km")
        if not (0 <= self.x_tenths <= 10_000 and 0 <= self.y_tenths <= 10_000):
            raise ValueError("epicenter coordinates must be between 0.0 and 1000.0 km")
        if self.revision < 1:
            raise ValueError("revision must be a positive integer")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset().total_seconds() != 0:
            raise ValueError("occurrence time must be timezone-aware UTC")
        if self.occurred_at.microsecond != 0:
            raise ValueError("occurrence time must have second precision")

    @staticmethod
    def create(event_id: int, magnitude: float, depth_km: float, x_km: float,
               y_km: float, occurred_at: datetime, station: str,
               populated_zone: bool, revision: int = 1) -> Event:
        """Build a new event from user-facing decimal values."""
        return Event(
            event_id=event_id,
            magnitude_tenths=_to_tenths(magnitude, "magnitude"),
            depth_tenths=_to_tenths(depth_km, "depth"),
            x_tenths=_to_tenths(x_km, "x"),
            y_tenths=_to_tenths(y_km, "y"),
            occurred_at=occurred_at.astimezone(timezone.utc).replace(microsecond=0),
            revision=revision,
            stations=frozenset({station}),
            status=AttentionStatus.PENDING,
            populated_zone=populated_zone,
        )

    # ---------- derived values ----------

    @property
    def priority(self) -> int:
        """1 = low, 2 = medium, 3 = high. Limits are inclusive."""
        m, h = self.magnitude_tenths, self.depth_tenths
        if m >= 60 or (m >= 45 and h <= 300 and self.populated_zone):
            return 3
        if m >= 45:
            return 2
        return 1

    @property
    def key(self) -> EventKey:
        return EventKey(self.priority, self.magnitude_tenths, self.event_id)

    @property
    def magnitude(self) -> float:
        return self.magnitude_tenths / 10

    @property
    def depth_km(self) -> float:
        return self.depth_tenths / 10

    @property
    def x_km(self) -> float:
        return self.x_tenths / 10

    @property
    def y_km(self) -> float:
        return self.y_tenths / 10

    def age_hours(self, clock: datetime) -> float:
        """Age relative to the simulation clock."""
        return (clock - self.occurred_at).total_seconds() / 3600

    def distance_squared_tenths(self, other: Event) -> int:
        """Squared epicenter distance in tenths of km (exact integer math).
        Compare against (R * 10) ** 2 to avoid floating-point sqrt."""
        dx = self.x_tenths - other.x_tenths
        dy = self.y_tenths - other.y_tenths
        return dx * dx + dy * dy

    # ---------- comparison of report data ----------

    def same_physical_data(self, other: Event) -> bool:
        """Equality used when processing reports: magnitude, depth,
        epicenter and occurrence time. Ignores station, revision and format."""
        return (self.magnitude_tenths == other.magnitude_tenths
                and self.depth_tenths == other.depth_tenths
                and self.x_tenths == other.x_tenths
                and self.y_tenths == other.y_tenths
                and self.occurred_at == other.occurred_at)

    # ---------- state transitions (all return a new Event) ----------

    def with_station(self, station: str) -> Event:
        """Confirmation: add the station if it was not already listed."""
        if station in self.stations:
            return self
        return replace(self, stations=self.stations | {station})

    def mark_reviewed(self) -> Event:
        """Does not change P, M or I, so the tree does not need to change."""
        return replace(self, status=AttentionStatus.REVIEWED)

    def corrected(self, populated_zone: bool, new_revision: Optional[int] = None,
                  stations: Optional[FrozenSet[str]] = None, **changes: Any) -> Event:
        """
        Return a corrected copy: new revision (r + 1 unless given, e.g. from a
        report), status back to pending, populated_zone recomputed by the caller.
        `changes` may contain magnitude_tenths, depth_tenths, x_tenths,
        y_tenths, occurred_at. The id can never be changed.
        """
        if "event_id" in changes:
            raise ValueError("event id is immutable")
        return replace(
            self,
            revision=new_revision if new_revision is not None else self.revision + 1,
            stations=stations if stations is not None else self.stations,
            status=AttentionStatus.PENDING,
            populated_zone=populated_zone,
            **changes,
        )

    # ---------- JSON ----------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.event_id,
            "magnitude": self.magnitude,
            "depth_km": self.depth_km,
            "epicenter": {"x": self.x_km, "y": self.y_km},
            "occurred_at": self.occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "revision": self.revision,
            "stations": sorted(self.stations),
            "status": self.status.value,
            "populated_zone": self.populated_zone,
            "priority": self.priority,   # stored only to be verified on load
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> Event:
        """Rebuild an event and verify the stored priority matches the computed one."""
        occurred = datetime.strptime(d["occurred_at"], "%Y-%m-%dT%H:%M:%SZ") \
                           .replace(tzinfo=timezone.utc)
        event = Event(
            event_id=d["id"],
            magnitude_tenths=_to_tenths(d["magnitude"], "magnitude"),
            depth_tenths=_to_tenths(d["depth_km"], "depth"),
            x_tenths=_to_tenths(d["epicenter"]["x"], "x"),
            y_tenths=_to_tenths(d["epicenter"]["y"], "y"),
            occurred_at=occurred,
            revision=d["revision"],
            stations=frozenset(d["stations"]),
            status=AttentionStatus(d["status"]),
            populated_zone=d["populated_zone"],
        )
        if "priority" in d and d["priority"] != event.priority:
            raise ValueError(
                f"event {event.event_id}: stored priority {d['priority']} "
                f"does not match computed {event.priority}"
            )
        return event