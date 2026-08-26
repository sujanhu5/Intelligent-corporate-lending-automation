"""ORM model — financial_ratios table.

Stores all calculated ratios and their interpretations for one application.
The raw extracted financials and the computed values both live here so
the report can re-read everything from a single row.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any, Dict, Optional

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.application import Application


class FinancialRatio(Base):
    __tablename__ = "financial_ratios"

    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("loan_applications.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Financial year this ratio set covers (e.g. "FY2023-24")
    financial_year: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)

    # -------------------------------------------------------------------------
    # Extracted base financial figures (stored for audit / report display)
    # -------------------------------------------------------------------------
    # Each key maps to a float representing the extracted monetary value
    # in the document's currency unit (no currency conversion is performed).
    extracted_financials: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # -------------------------------------------------------------------------
    # Calculated ratios
    # Structure per ratio:
    #   {
    #     "current_ratio": {
    #       "value": 1.85,
    #       "formula": "Current Assets / Current Liabilities",
    #       "interpretation": "Adequate short-term liquidity.",
    #       "risk_level": "low",        # very_low | low | medium | high | very_high
    #       "benchmark_min": 1.0,
    #       "benchmark_max": 3.0
    #     },
    #     ...
    #   }
    # -------------------------------------------------------------------------
    ratios: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Overall financial health summary
    overall_health: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    health_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Calculation metadata (timestamp, version of ratio engine)
    calculation_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)

    # Relationship
    application: Mapped["Application"] = relationship(
        "Application", back_populates="financial_ratios"
    )

    def get_ratio_value(self, ratio_name: str) -> Optional[float]:
        if not self.ratios:
            return None
        ratio = self.ratios.get(ratio_name, {})
        return ratio.get("value")

    def __repr__(self) -> str:
        return (
            f"<FinancialRatio id={self.id} application_id={self.application_id} "
            f"fy={self.financial_year}>"
        )
