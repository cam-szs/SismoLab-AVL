"""[STUB - team must implement] Event lifecycle service."""

from domain.event import Event


class EventService:
    """Coordinate creation, correction, deletion, and review marking."""

    def create(self, event: Event) -> Event:
        """Create an event under the scenario validation rules."""
        raise NotImplementedError("TODO: implement event creation")

    def correct(self, event_id: str, changes: dict[str, object]) -> Event:
        """Correct an event and preserve the required undo snapshot."""
        raise NotImplementedError("TODO: implement event correction")

    def delete(self, event_id: str) -> None:
        """Delete an event according to the history policy."""
        raise NotImplementedError("TODO: implement event deletion")

    def mark_reviewed(self, event_id: str) -> None:
        """Mark an event as reviewed under the report workflow rules."""
        raise NotImplementedError("TODO: implement reviewed status transition")
