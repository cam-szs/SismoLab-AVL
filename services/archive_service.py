"""[STUB - team must implement] Archive and recovery service."""

from domain.event import Report


class ArchiveService:
    """Manage report archival and recovery branches."""

    def archive(self, report: Report) -> None:
        """Choose the archive branch required by the report rules."""
        raise NotImplementedError("TODO: implement archive branch selection")

    def recover(self, report_id: str) -> Report:
        """Recover a report and apply global recovery rules."""
        raise NotImplementedError("TODO: implement global rebalance and recovery")
