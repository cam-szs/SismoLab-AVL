"""[STUB - team must implement] Report queue and state-machine service."""

from domain.event import Report
from domain.queue_fifo import ReportQueue


class ReportProcessor:
    """Consume reports and apply the required state-machine transitions."""

    def process_next(self, queue: ReportQueue[Report]) -> Report:
        """Consume one queued report and advance its state."""
        raise NotImplementedError("TODO: implement report queue consumption and state machine")

    def calculate_priority(self, report: Report) -> int:
        """Calculate report priority using the project priority rules."""
        raise NotImplementedError("TODO: implement report priority calculation")
