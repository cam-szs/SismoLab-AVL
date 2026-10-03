"""Archived and deleted report history."""

from __future__ import annotations

from dataclasses import dataclass, field

from .event import Event
from .report import Report

HistoryEntry = Report | Event


def _normalize_id(report_id: int | str) -> int:
    """Accept numeric IDs and display IDs such as ``SIS-000010``."""
    if isinstance(report_id, bool):
        raise ValueError("report id must be an integer or SIS-XXXXXX")
    if isinstance(report_id, int):
        return report_id
    if not isinstance(report_id, str):
        raise ValueError("report id must be an integer or SIS-XXXXXX")
    value = report_id.strip().upper()
    if value.startswith("SIS-"):
        value = value[4:]
    if not value.isdigit():
        raise ValueError("report id must be an integer or SIS-XXXXXX")
    return int(value)


@dataclass
class Historial:
    """Keep recoverable archived and deleted report snapshots."""

    archived: list[HistoryEntry] = field(default_factory=list)
    deleted: list[HistoryEntry] = field(default_factory=list)

    def archive(self, report: HistoryEntry) -> None:
        """Store a report in the archive, replacing an existing same-ID entry."""
        self._validate(report)
        self._replace(self.archived, report)

    def delete(self, report: HistoryEntry) -> None:
        """Move a report from the archive to the deleted history branch."""
        self._validate(report)
        self._remove(self.archived, report.event_id)
        self._replace(self.deleted, report)

    def restore(self, report_id: int | str) -> Report:
        """Remove and return a report from either history branch."""
        target_id = _normalize_id(report_id)
        report = self._pop(self.archived, target_id)
        if report is not None:
            return report
        report = self._pop(self.deleted, target_id)
        if report is not None:
            return report
        raise KeyError(f"report {target_id} is not archived or deleted")

    def find_archived(self, report_id: int | str) -> HistoryEntry | None:
        return self._find(self.archived, _normalize_id(report_id))

    def find_deleted(self, report_id: int | str) -> HistoryEntry | None:
        return self._find(self.deleted, _normalize_id(report_id))

    @property
    def archived_count(self) -> int:
        return len(self.archived)

    @property
    def deleted_count(self) -> int:
        return len(self.deleted)

    @staticmethod
    def _validate(report: HistoryEntry) -> None:
        if not isinstance(report, (Report, Event)):
            raise TypeError("history entries must be Report or Event instances")

    @staticmethod
    def _find(reports: list[HistoryEntry], event_id: int) -> HistoryEntry | None:
        return next((item for item in reports if item.event_id == event_id), None)

    @staticmethod
    def _remove(reports: list[HistoryEntry], event_id: int) -> None:
        reports[:] = [item for item in reports if item.event_id != event_id]

    @staticmethod
    def _replace(reports: list[HistoryEntry], report: HistoryEntry) -> None:
        Historial._remove(reports, report.event_id)
        reports.append(report)

    @staticmethod
    def _pop(reports: list[HistoryEntry], event_id: int) -> HistoryEntry | None:
        for index, item in enumerate(reports):
            if item.event_id == event_id:
                return reports.pop(index)
        return None
