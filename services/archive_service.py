"""Archive and recovery service."""

from domain.historial import Historial
from domain.report import Report


class ArchiveService:
    """Manage report archival and recovery branches."""

    def __init__(self) -> None:
        self.history = Historial()
        self.archived: dict[int, Report] = {}
        self.deleted: dict[int, Report] = {}

    def archive(self, report: Report) -> Report:
        """Choose the archive branch required by the report rules."""
        self.history.archive(report)
        self.archived[report.event_id] = report
        return report

    def recover(self, report_id: str | int) -> Report:
        """Recover a report and apply global recovery rules."""
        target_id = int(report_id)
        if target_id in self.archived:
            report = self.archived.pop(target_id)
            self.history.restore(target_id)
            return report
        if target_id in self.deleted:
            report = self.deleted.pop(target_id)
            self.history.restore(target_id)
            return report
        raise KeyError(f"report {target_id} is not archived or deleted")
