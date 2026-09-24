"""[BOILERPLATE - implemented] Core seismic data records."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Event:
    """Represent one seismic event received by the application."""

    event_id: str
    magnitude: float
    latitude: float
    longitude: float
    depth_km: float
    timestamp: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Association:
    """Represent an association between two seismic records."""

    source_id: str
    target_id: str
    score: float = 0.0


@dataclass
class Report:
    """Represent a report without implementing its processing rules."""

    report_id: str
    event_ids: list[str] = field(default_factory=list)
    state: str = "draft"
    notes: str = ""


@dataclass
class Station:
    """Represent a seismic station."""

    station_id: str
    name: str
    latitude: float
    longitude: float


@dataclass
class Zone:
    """Represent a geographic zone containing stations or events."""

    zone_id: str
    name: str
    station_ids: list[str] = field(default_factory=list)
