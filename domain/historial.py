"""Archived and deleted report history."""

from dataclasses import dataclass, field

from domain.report import Report


@dataclass
class Historial:
    """Store report history while branch and recovery rules remain explicit."""

    archived: list[Report] = field(default_factory=list)
    deleted: list[Report] = field(default_factory=list)

    def archive(self, report: Report) -> None:
        """Archive a report using the required archive-branch policy."""
        self.archived.append(report)

    def restore(self, report_id: str | int) -> Report:
        """Restore a report using the required history policy."""
        target_id = int(report_id)
        for index, candidate in enumerate(self.archived):
            if candidate.event_id == target_id:
                return self.archived.pop(index)
        for index, candidate in enumerate(self.deleted):
            if candidate.event_id == target_id:
                return self.deleted.pop(index)
        raise KeyError(f"report {target_id} is not in history")
