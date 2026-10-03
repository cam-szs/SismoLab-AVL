"""Deterministic association matching for earthquake events."""

from __future__ import annotations

from math import sqrt

from domain.event import Association, Event


class AssociationService:
    """Match events using the project association criteria."""

    def __init__(self, max_hours: float = 48.0, max_distance_km: float = 40.0) -> None:
        self.max_hours = max_hours
        self.max_distance_km = max_distance_km

    def associate(
        self,
        source: Event,
        candidates: list[Event],
        *,
        max_hours: float | None = None,
        max_distance_km: float | None = None,
    ) -> list[Association]:
        """Return all valid candidate links and mark the chosen reference event."""
        hours_limit = self.max_hours if max_hours is None else max_hours
        distance_limit = (
            self.max_distance_km if max_distance_km is None else max_distance_km
        )
        valid: list[tuple[Event, Association]] = []
        for candidate in candidates:
            if candidate.event_id == source.event_id:
                continue
            if candidate.magnitude_tenths <= source.magnitude_tenths:
                continue
            if candidate.occurred_at >= source.occurred_at:
                continue

            hours = (source.occurred_at - candidate.occurred_at).total_seconds() / 3600
            if hours > hours_limit:
                continue

            dx = (candidate.x_tenths - source.x_tenths) / 10.0
            dy = (candidate.y_tenths - source.y_tenths) / 10.0
            distance = sqrt(dx * dx + dy * dy)
            if distance > distance_limit:
                continue

            valid.append(
                (
                    candidate,
                    Association(
                        source_id=source.event_id,
                        reference_id=candidate.event_id,
                        time_hours=hours,
                        distance_km=distance,
                        is_reference=False,
                    ),
                )
            )

        if not valid:
            return []

        reference_event, _ = max(
            valid,
            key=lambda item: (
                item[0].magnitude_tenths,
                -item[1].time_hours,
                -item[1].distance_km,
                -item[0].event_id,
            ),
        )

        result: list[Association] = []
        for candidate, item in sorted(
            valid,
            key=lambda pair: (
                not pair[1].reference_id == reference_event.event_id,
                pair[1].distance_km,
                pair[1].time_hours,
                pair[1].reference_id,
            ),
        ):
            result.append(
                Association(
                    source_id=item.source_id,
                    reference_id=item.reference_id,
                    time_hours=item.time_hours,
                    distance_km=item.distance_km,
                    is_reference=(candidate.event_id == reference_event.event_id),
                )
            )

        return result
