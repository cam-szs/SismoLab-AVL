"""Incoming station reports used by the report-processing workflow."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict

from .event import Event, _to_tenths


@dataclass(frozen=True)
class Report:
	"""Immutable observation received from one seismic station.

	A report is an input record, while :class:`Event` is the consolidated
	state stored by the application. Numeric values use integer tenths so that
	report comparisons do not depend on floating-point arithmetic.
	"""

	event_id: int
	magnitude_tenths: int
	depth_tenths: int
	x_tenths: int
	y_tenths: int
	occurred_at: datetime
	station: str
	revision: int = 1

	def __post_init__(self) -> None:
		if not isinstance(self.event_id, int) or isinstance(self.event_id, bool):
			raise ValueError("id must be an integer")
		if not isinstance(self.station, str) or not self.station.strip():
			raise ValueError("station must be a non-empty string")
		if not isinstance(self.revision, int) or isinstance(self.revision, bool):
			raise ValueError("revision must be a positive integer")
		if self.revision < 1:
			raise ValueError("revision must be a positive integer")

		Event(
			event_id=self.event_id,
			magnitude_tenths=self.magnitude_tenths,
			depth_tenths=self.depth_tenths,
			x_tenths=self.x_tenths,
			y_tenths=self.y_tenths,
			occurred_at=self.occurred_at,
			stations=frozenset({self.station}),
		)

	@classmethod
	def create(
		cls,
		event_id: int,
		magnitude: float,
		depth_km: float,
		x_km: float,
		y_km: float,
		occurred_at: datetime,
		station: str,
		revision: int = 1,
	) -> "Report":
		"""Build a report from the decimal values used by the API/UI."""
		return cls(
			event_id=event_id,
			magnitude_tenths=_to_tenths(magnitude, "magnitude"),
			depth_tenths=_to_tenths(depth_km, "depth"),
			x_tenths=_to_tenths(x_km, "x"),
			y_tenths=_to_tenths(y_km, "y"),
			occurred_at=occurred_at.astimezone(timezone.utc).replace(microsecond=0),
			station=station.strip(),
			revision=revision,
		)

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

	def to_event(self, populated_zone: bool = False) -> Event:
		"""Convert this observation into a new pending event snapshot."""
		return Event(
			event_id=self.event_id,
			magnitude_tenths=self.magnitude_tenths,
			depth_tenths=self.depth_tenths,
			x_tenths=self.x_tenths,
			y_tenths=self.y_tenths,
			occurred_at=self.occurred_at,
			revision=self.revision,
			stations=frozenset({self.station}),
			populated_zone=populated_zone,
		)

	def to_dict(self) -> Dict[str, Any]:
		"""Return the stable JSON shape used for queued reports."""
		return {
			"id": self.event_id,
			"magnitude": self.magnitude,
			"depth_km": self.depth_km,
			"epicenter": {"x": self.x_km, "y": self.y_km},
			"occurred_at": self.occurred_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
			"station": self.station,
			"revision": self.revision,
		}
