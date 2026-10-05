"""Scenario state, execution mode, and configurable academic parameters."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any


@dataclass(frozen=True)
class Zone:
    """Represent a scenario zone as an axis-aligned rectangle in km.

    Bounds are inclusive: an epicenter on the border belongs to the zone.
    """

    name: str
    x_min: float = 0.0
    x_max: float = 1000.0
    y_min: float = 0.0
    y_max: float = 1000.0
    populated: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("zone name must be a non-empty string")
        for value in (self.x_min, self.x_max, self.y_min, self.y_max):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise ValueError(f"zone {self.name}: bounds must be numbers")
            if not 0.0 <= value <= 1000.0:
                raise ValueError(f"zone {self.name}: bounds must be between 0 and 1000 km")
        if self.x_min > self.x_max or self.y_min > self.y_max:
            raise ValueError(f"zone {self.name}: min bound is greater than max bound")

    def contains(self, x_km: float, y_km: float) -> bool:
        """Return whether a point is inside the rectangle or on its border."""
        return self.x_min <= x_km <= self.x_max and self.y_min <= y_km <= self.y_max

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "x_min": self.x_min,
            "x_max": self.x_max,
            "y_min": self.y_min,
            "y_max": self.y_max,
            "populated": self.populated,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Zone":
        if not isinstance(data, dict):
            raise ValueError("zone entries must be objects")
        if not isinstance(data.get("populated"), bool):
            raise ValueError("zone populated flag must be a boolean")
        return Zone(
            name=data.get("name", ""),
            x_min=data.get("x_min"),
            x_max=data.get("x_max"),
            y_min=data.get("y_min"),
            y_max=data.get("y_max"),
            populated=data["populated"],
        )


def default_zones() -> dict[str, Zone]:
    """Fixed geometry of the fictional territory used when no file provides one.

    "Valle Central" and "Sierra Alta" share the border x = 500 so the
    border rule (populated wins) can be demonstrated.
    """
    zones = [
        Zone("Valle Central", 300.0, 500.0, 300.0, 500.0, populated=True),
        Zone("Sierra Alta", 500.0, 700.0, 300.0, 500.0, populated=False),
        Zone("Puerto Norte", 650.0, 900.0, 700.0, 950.0, populated=True),
        Zone("Desierto Sur", 100.0, 900.0, 50.0, 250.0, populated=False),
    ]
    return {zone.name: zone for zone in zones}


@dataclass(frozen=True)
class Station:
    """Station metadata used to describe the network (fixed during a run)."""

    code: str
    x_km: float = 0.0
    y_km: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"code": self.code, "x_km": self.x_km, "y_km": self.y_km}

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Station":
        if not isinstance(data, dict):
            raise ValueError("station entries must be objects")
        code = data.get("code")
        if not isinstance(code, str) or not code.strip():
            raise ValueError("station code must be a non-empty string")
        x_km, y_km = data.get("x_km", 0.0), data.get("y_km", 0.0)
        for value in (x_km, y_km):
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1000:
                raise ValueError(f"station {code}: coordinates must be between 0 and 1000 km")
        return Station(code.strip(), float(x_km), float(y_km))


def default_stations() -> dict[str, Station]:
    """Station network of the fictional territory."""
    stations = [
        Station("ST-1", 400.0, 420.0),
        Station("ST-2", 620.0, 380.0),
        Station("ST-3", 780.0, 820.0),
        Station("ST-4", 500.0, 150.0),
        Station("ST-5", 150.0, 850.0),
    ]
    return {station.code: station for station in stations}


@dataclass
class Scenario:
    """Hold fixed scenario data and the normal/stress execution controls.

    W, R, L, and T are parameters from the assignment, not execution modes:
    W/R configure associations, L configures expensive access, and T
    configures branch archival age.
    """

    zones: dict[str, Zone] = field(default_factory=default_zones)
    stations: dict[str, Station] = field(default_factory=default_stations)
    clock: int = 0
    simulation_time: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc).replace(microsecond=0)
    )
    mode: str = "normal"
    values: dict[str, Any] = field(default_factory=dict)
    association_window_hours: float = 48.0
    association_distance_km: float = 40.0
    access_depth_limit: int = 3
    archive_age_hours: float = 72.0

    def advance_clock(self, amount: int = 1) -> None:
        """Advance the simulation clock according to scenario rules."""
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        self.clock += amount
        self.simulation_time += timedelta(hours=amount)
        self.values["clock"] = self.clock
        self.values["simulation_time"] = self.simulation_time.isoformat().replace("+00:00", "Z")

    def set_mode(self, mode: str) -> None:
        """Set the execution mode.

        ``W`` and ``T`` remain accepted as deprecated aliases for clients
        from the first prototype. ``R`` and ``L`` are parameters and are not
        accepted as modes.
        """
        normalized = str(mode).strip().upper()
        aliases = {"W": "normal", "T": "stress", "NORMAL": "normal", "STRESS": "stress"}
        if normalized not in aliases:
            raise ValueError("mode must be one of normal or stress")
        normalized = aliases[normalized]
        if self.mode != normalized:
            self.values["previous_mode"] = self.mode
        self.mode = normalized
        self.values["mode"] = self.mode

    @property
    def stress_mode(self) -> bool:
        """Whether the scenario is currently processing a deferred-balance burst."""
        return self.mode == "stress"

    def set_parameters(
        self,
        *,
        W: float | None = None,
        R: float | None = None,
        L: int | None = None,
        T: float | None = None,
    ) -> None:
        """Validate and update the assignment's W/R/L/T parameters."""
        if W is not None and (not isinstance(W, (int, float)) or W <= 0):
            raise ValueError("W must be positive")
        if R is not None and (not isinstance(R, (int, float)) or R <= 0):
            raise ValueError("R must be positive")
        if L is not None and (not isinstance(L, int) or isinstance(L, bool) or L < 0):
            raise ValueError("L must be a non-negative integer")
        if T is not None and (not isinstance(T, (int, float)) or T <= 0):
            raise ValueError("T must be positive")
        if W is not None:
            self.association_window_hours = float(W)
        if R is not None:
            self.association_distance_km = float(R)
        if L is not None:
            self.access_depth_limit = L
        if T is not None:
            self.archive_age_hours = float(T)
        self.values.update(self.parameters)

    @property
    def parameters(self) -> dict[str, float | int]:
        """Return the serializable W/R/L/T parameter set."""
        return {
            "W": self.association_window_hours,
            "R": self.association_distance_km,
            "L": self.access_depth_limit,
            "T": self.archive_age_hours,
        }

    def is_populated(self, x_km: float, y_km: float) -> bool:
        """Return whether coordinates fall inside (or on the border of) any
        populated zone. A point on the border of a populated and an
        unpopulated zone is therefore classified as populated."""
        return any(
            zone.populated and zone.contains(x_km, y_km)
            for zone in self.zones.values()
        )

    def stations_payload(self) -> list[dict[str, Any]]:
        return [station.to_dict() for station in self.stations.values()]

    @staticmethod
    def stations_from_payload(payload: Any) -> dict[str, Station]:
        if not isinstance(payload, list):
            raise ValueError("stations must be an array")
        stations: dict[str, Station] = {}
        for item in payload:
            station = Station.from_dict(item)
            if station.code in stations:
                raise ValueError(f"duplicate station {station.code}")
            stations[station.code] = station
        return stations

    def zones_payload(self) -> list[dict[str, Any]]:
        return [zone.to_dict() for zone in self.zones.values()]

    @staticmethod
    def zones_from_payload(payload: Any) -> dict[str, Zone]:
        """Validate a serialized zone list; names must be unique."""
        if not isinstance(payload, list):
            raise ValueError("zones must be an array")
        zones: dict[str, Zone] = {}
        for item in payload:
            zone = Zone.from_dict(item)
            if zone.name in zones:
                raise ValueError(f"duplicate zone {zone.name}")
            zones[zone.name] = zone
        return zones
