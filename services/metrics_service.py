"""[BOILERPLATE - implemented] Mechanical counters."""


class MetricsService:
    """Track named integer counters without applying academic rules."""

    def __init__(self) -> None:
        """Create empty metrics."""
        self._counts: dict[str, int] = {}

    def increment(self, name: str, amount: int = 1) -> int:
        """Increase a named counter and return its new value."""
        self._counts[name] = self._counts.get(name, 0) + amount
        return self._counts[name]

    def get(self, name: str) -> int:
        """Return a counter value, defaulting to zero."""
        return self._counts.get(name, 0)
