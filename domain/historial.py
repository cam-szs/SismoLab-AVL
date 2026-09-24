"""[STUB - team must implement] Archived and deleted report history."""

from dataclasses import dataclass, field

from sismolab_avl.domain.event import Report


@dataclass
class Historial:
    """Store report history while branch and recovery rules remain explicit."""

    archived: list[Report] = field(default_factory=list)
    deleted: list[Report] = field(default_factory=list)

    def archive(self, report: Report) -> None:
        """Archive a report using the required archive-branch policy."""
        raise NotImplementedError("TODO: implement archive branch selection")

    def restore(self, report_id: str) -> Report:
        """Restore a report using the required history policy."""
        raise NotImplementedError("TODO: implement report restoration")
