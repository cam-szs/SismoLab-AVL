"""[STUB - team must implement] Event association service."""

from domain.event import Association, Event


class AssociationService:
    """Match events using the project association criteria."""

    def associate(self, source: Event, candidates: list[Event]) -> list[Association]:
        """Return matches according to temporal, spatial, and magnitude rules."""
        raise NotImplementedError("TODO: implement association matching")
