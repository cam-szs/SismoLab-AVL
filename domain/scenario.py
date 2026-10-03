"""Scenario state and simulation controls."""

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
    """Hold zones, stations, clock, W/R/L/T controls, and current mode."""

    zones: dict[str, Zone] = field(default_factory=dict)
    stations: dict[str, Station] = field(default_factory=dict)
    clock: int = 0
    mode: str = "W"
    values: dict[str, Any] = field(default_factory=dict)

    def advance_clock(self, amount: int = 1) -> None:
        """Advance the simulation clock according to scenario rules."""
        if not isinstance(amount, int) or isinstance(amount, bool) or amount < 0:
            raise ValueError("amount must be a non-negative integer")
        self.clock += amount
        self.values["clock"] = self.clock

    def set_mode(self, mode: str) -> None:
        """Set W, R, L, or T after validating the scenario mode rules."""
        normalized = str(mode).strip().upper()
        if normalized not in {"W", "R", "L", "T"}:
            raise ValueError("mode must be one of W, R, L, T")
        if self.mode != normalized:
            self.values["previous_mode"] = self.mode
        self.mode = normalized
        self.values["mode"] = self.mode
