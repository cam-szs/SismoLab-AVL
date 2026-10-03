from datetime import datetime, timezone

import pytest

from domain.event import Event
from domain.event_key import EventKey
from services.event_service import EventService


def _sample_event(event_id: int, magnitude: float = 5.0, depth_km: float = 20.0) -> Event:
    return Event.create(
        event_id=event_id,
        magnitude=magnitude,
        depth_km=depth_km,
        x_km=10.0,
        y_km=15.0,
        occurred_at=datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc),
        station="S1",
        populated_zone=True,
    )


def test_create_event_stores_in_active_index_and_tree() -> None:
    service = EventService()
    event = _sample_event(101, magnitude=4.8, depth_km=70.0)

    created = service.create(event)

    assert created == event
    assert service.get_active(101) == event
    assert service.tree.find(event.key) == event


def test_create_rejects_duplicate_id_even_if_key_changes() -> None:
    service = EventService()
    first = _sample_event(42, magnitude=5.0, depth_km=20.0)
    service.create(first)

    second = _sample_event(42, magnitude=6.2, depth_km=15.0)

    with pytest.raises(ValueError, match="already exists"):
        service.create(second)


def test_correct_recalculates_key_and_keeps_event_identity() -> None:
    service = EventService()
    after = _sample_event(77, magnitude=4.8, depth_km=70.0)
    service.create(after)

    updated = service.correct(77, {"magnitude_tenths": EventKey.to_tenths(6.2), "depth_tenths": EventKey.to_tenths(15.0), "populated_zone": True})

    assert updated.event_id == 77
    assert updated.key == EventKey(3, EventKey.to_tenths(6.2), 77)
    assert service.get_active(77) == updated
    assert service.tree.find(after.key) is None


def test_delete_marks_id_as_removed_and_keeps_it_out_of_active_catalog() -> None:
    service = EventService()
    event = _sample_event(9)
    service.create(event)

    service.delete(9)

    assert service.get_active(9) is None
    assert 9 in service.deleted_ids
    assert service.tree.find(event.key) is None


def test_mark_reviewed_updates_the_active_index_and_avl_value() -> None:
    service = EventService()
    event = _sample_event(12)
    service.create(event)

    reviewed = service.mark_reviewed(12)

    assert reviewed.status.value == "reviewed"
    assert service.get_active(12) == reviewed
    assert service.tree.find(reviewed.key) == reviewed
    assert service.tree.find(reviewed.key) is not event
