from datetime import datetime, timezone

from domain.event import Event
from services.association_service import AssociationService


def _event(event_id: int, magnitude: float, x_km: float, y_km: float, occurred_at: datetime) -> Event:
    return Event.create(
        event_id=event_id,
        magnitude=magnitude,
        depth_km=20.0,
        x_km=x_km,
        y_km=y_km,
        occurred_at=occurred_at,
        station="S1",
        populated_zone=True,
    )


def test_association_service_filters_and_selects_reference() -> None:
    base_time = datetime(2026, 10, 1, 12, 0, tzinfo=timezone.utc)
    source = _event(10, 5.0, 0.0, 0.0, base_time)
    close_but_smaller = _event(11, 5.4, 5.0, 0.0, base_time.replace(hour=10))
    best_candidate = _event(12, 6.1, 8.0, 0.0, base_time.replace(hour=9))
    too_far = _event(13, 7.0, 100.0, 0.0, base_time.replace(hour=1))

    associations = AssociationService().associate(source, [close_but_smaller, best_candidate, too_far])

    assert len(associations) == 2
    assert associations[0].reference_id == 12
    assert associations[0].is_reference is True
    assert associations[1].reference_id == 11
    assert associations[1].is_reference is False
