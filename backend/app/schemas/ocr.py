"""
Pydantic schemas for OCR endpoints.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

from app.models.document import DocumentStatus


class OCRTriggerResponse(BaseModel):
    """Returned immediately when OCR is kicked off."""
    document_id: uuid.UUID
    application_id: uuid.UUID
    status: str = "processing"
    message: str


class ExtractedFieldItem(BaseModel):
    """Single financial field with its parsed value and confidence."""
    field_name: str
    display_name: str
    value: Optional[float]
    confidence: float          # 0.0 – 1.0
    formatted_value: Optional[str] = None


class OCRResultResponse(BaseModel):
    """Full OCR result for one document."""
    id: uuid.UUID
    document_id: uuid.UUID
    document_status: DocumentStatus
    raw_text: Optional[str]
    page_count: Optional[int]
    confidence_score: Optional[float]
    extracted_fields: Optional[Dict[str, Any]]
    extraction_metadata: Optional[Dict[str, Any]]
    field_details: List[ExtractedFieldItem] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ApplicationOCRSummary(BaseModel):
    """Aggregated OCR status for all documents in an application."""
    application_id: uuid.UUID
    total_documents: int
    extracted_documents: int
    failed_documents: int
    pending_documents: int
    combined_fields: Dict[str, Optional[float]]  # merged best-values across all docs
    field_sources: Dict[str, str]               # field_name → document_id that provided it
    overall_confidence: float
    warnings: List[str] = []


# Human-readable display names for every financial field
FIELD_DISPLAY_NAMES: Dict[str, str] = {
    "revenue":                   "Revenue / Net Sales",
    "cost_of_revenue":           "Cost of Revenue (COGS)",
    "gross_profit":              "Gross Profit",
    "operating_profit":          "Operating Profit (PBIT)",
    "ebit":                      "EBIT",
    "ebitda":                    "EBITDA",
    "net_profit":                "Net Profit (PAT)",
    "cash":                      "Cash & Cash Equivalents",
    "inventory":                 "Inventory / Stock",
    "accounts_receivable":       "Accounts Receivable (Trade Debtors)",
    "accounts_payable":          "Accounts Payable (Trade Creditors)",
    "current_assets":            "Total Current Assets",
    "current_liabilities":       "Total Current Liabilities",
    "total_assets":              "Total Assets",
    "total_liabilities":         "Total Liabilities",
    "equity":                    "Shareholders' Equity",
    "long_term_debt":            "Long-Term Debt",
    "short_term_debt":           "Short-Term Debt",
    "interest_expense":          "Interest Expense (Finance Costs)",
    "operating_cash_flow":       "Operating Cash Flow",
    "investing_cash_flow":       "Investing Cash Flow",
    "financing_cash_flow":       "Financing Cash Flow",
    "depreciation_amortisation": "Depreciation & Amortisation",
    "tax_expense":               "Income Tax Expense",
    "net_worth":                 "Net Worth",
}
