# event_key.py
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, order=True)
class EventKey:
    """
    Immutable ordering key K = (P, M, I).

    Field order matters: `order=True` generates lexicographic comparison
    (priority first, then magnitude, then id), which is exactly the
    comparison rule required by the project.

    Magnitude is stored in tenths (5.2 -> 52) as an int to avoid
    floating-point issues.
    """
    priority: int          # 1 (low), 2 (medium), 3 (high)
    magnitude_tenths: int  # magnitude * 10
    event_id: int          # numeric id (1..999999)

    @staticmethod
    def to_tenths(magnitude: float) -> int:
        """Convert a magnitude with at most one decimal to integer tenths."""
        return round(magnitude * 10)

    @property
    def magnitude(self) -> float:
        """Magnitude as a decimal, for display and JSON only."""
        return self.magnitude_tenths / 10

    def __str__(self) -> str:
        return f"({self.priority}, {self.magnitude:.1f}, {self.event_id})"