"""[STUB - team must implement] Scenario state and simulation controls."""

from dataclasses import dataclass, field
from typing import Any

from domain.event import Station, Zone


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
        raise NotImplementedError("TODO: implement scenario clock progression")

    def set_mode(self, mode: str) -> None:
        """Set W, R, L, or T after validating the scenario mode rules."""
        raise NotImplementedError("TODO: implement W/R/L/T mode transitions")
