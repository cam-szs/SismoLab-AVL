"""Core event lifecycle service for the AVL-backed catalog."""

from __future__ import annotations

from typing import Any

from domain.avl import AVLTree
from domain.event import Event
from domain.event_key import EventKey


class EventService:
    """Coordinate creation, correction, deletion, and review marking."""

    def __init__(self) -> None:
        self.tree = AVLTree[EventKey, Event]()
        self.active: dict[int, Event] = {}
        self.archived: dict[int, Event] = {}
        self.deleted_ids: set[int] = set()

    def _assert_not_registered(self, event_id: int) -> None:
        """Reject any id that already exists in the active, archived, or deleted catalog."""
        if event_id in self.active or event_id in self.archived or event_id in self.deleted_ids:
            raise ValueError(f"event {event_id} already exists")

    def get_active(self, event_id: int) -> Event | None:
        """Return the active event by id, or None when it is not present."""
        return self.active.get(event_id)

    def create(self, event: Event) -> Event:
        """Create an event under the scenario validation rules."""
        self._assert_not_registered(event.event_id)
        self.tree.insert(event.key, event)
        self.active[event.event_id] = event
        return event

    def correct(self, event_id: int, changes: dict[str, object]) -> Event:
        """Correct an active event and preserve the same identity while updating its key."""
        if event_id not in self.active:
            raise KeyError(f"event {event_id} is not active")

        current = self.active[event_id]
        if "event_id" in changes:
            raise ValueError("event id is immutable")

        payload = {
            "populated_zone": current.populated_zone,
            "stations": current.stations,
            **changes,
        }
        updated = current.corrected(**payload)

        old_key = current.key
        if updated.key != old_key:
            self.tree.remove(old_key)
            self.tree.insert(updated.key, updated)

        self.active[event_id] = updated
        return updated

    def delete(self, event_id: int) -> None:
        """Delete an active event and record the id as removed."""
        if event_id not in self.active:
            raise KeyError(f"event {event_id} is not active")

        removed = self.active.pop(event_id)
        self.deleted_ids.add(event_id)
        self.tree.remove(removed.key)

    def mark_reviewed(self, event_id: int) -> Event:
        """Mark an event as reviewed under the report workflow rules."""
        if event_id not in self.active:
            raise KeyError(f"event {event_id} is not active")

        current = self.active[event_id]
        updated = current.mark_reviewed()
        self.tree.update_value(current.key, updated)
        self.active[event_id] = updated
        return updated
