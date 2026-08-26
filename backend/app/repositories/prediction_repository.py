"""
PredictionRepository — database operations for the predictions table.
"""

from __future__ import annotations

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.models.prediction import ModelUsed, Prediction, PredictionOutcome, RiskLevel


class PredictionRepository:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get_latest_for_application(
        self, application_id: uuid.UUID
    ) -> Optional[Prediction]:
        return (
            self._db.query(Prediction)
            .filter(Prediction.application_id == application_id)
            .order_by(Prediction.created_at.desc())
            .first()
        )

    def create(self, **kwargs) -> Prediction:
        pred = Prediction(**kwargs)
        self._db.add(pred)
        self._db.flush()
        return pred

    def upsert(self, application_id: uuid.UUID, **kwargs) -> Prediction:
        """Overwrite the most recent prediction for this application, or create new."""
        existing = self.get_latest_for_application(application_id)
        if existing:
            for k, v in kwargs.items():
                if hasattr(existing, k):
                    setattr(existing, k, v)
            self._db.flush()
            return existing
        return self.create(application_id=application_id, **kwargs)
