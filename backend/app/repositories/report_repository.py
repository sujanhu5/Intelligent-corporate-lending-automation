"""
ReportRepository — database operations for the reports table.
"""

from __future__ import annotations

import uuid
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.report import Report, ReportStatus


class ReportRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_by_id(self, report_id: uuid.UUID) -> Optional[Report]:
        return self._db.query(Report).filter(Report.id == report_id).first()

    def get_latest_for_application(self, application_id: uuid.UUID) -> Optional[Report]:
        return (
            self._db.query(Report)
            .filter(Report.application_id == application_id)
            .order_by(Report.version.desc())
            .first()
        )

    def list_for_application(self, application_id: uuid.UUID) -> List[Report]:
        return (
            self._db.query(Report)
            .filter(Report.application_id == application_id)
            .order_by(Report.version.desc())
            .all()
        )

    def next_version(self, application_id: uuid.UUID) -> int:
        latest = self.get_latest_for_application(application_id)
        return (latest.version + 1) if latest else 1

    def create(self, **kwargs) -> Report:
        report = Report(**kwargs)
        self._db.add(report)
        self._db.flush()
        return report

    def mark_complete(self, report: Report, file_size_bytes: int) -> Report:
        report.status = ReportStatus.COMPLETE
        report.file_size_bytes = file_size_bytes
        self._db.flush()
        return report

    def mark_failed(self, report: Report, error: str) -> Report:
        report.status = ReportStatus.FAILED
        report.generation_error = error[:2000]
        self._db.flush()
        return report
