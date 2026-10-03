"""Scenario state, execution mode, and configurable academic parameters."""

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Zone:
    """Represent a scenario zone with simple bounds."""

    name: str
    x_min: float = 0.0
    x_max: float = 1000.0
    y_min: float = 0.0
    y_max: float = 1000.0
    populated: bool = False


@dataclass(frozen=True)
class Station:
    """Station metadata used to describe the network."""

    code: str
    x_km: float = 0.0
    y_km: float = 0.0


@dataclass
class Scenario:
    """Hold fixed scenario data and the normal/stress execution controls.

    W, R, L, and T are parameters from the assignment, not execution modes:
    W/R configure associations, L configures expensive access, and T
    configures branch archival age.
    """

    zones: dict[str, Zone] = field(default_factory=dict)
    stations: dict[str, Station] = field(default_factory=dict)
    clock: int = 0
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
        self.values["clock"] = self.clock

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
        """Return whether coordinates fall inside any populated configured zone."""
        return any(
            zone.populated
            and zone.x_min <= x_km <= zone.x_max
            and zone.y_min <= y_km <= zone.y_max
            for zone in self.zones.values()
        )
