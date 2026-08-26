"""
Financial text parser — converts raw OCR text into a structured dictionary
of financial field values.

Approach:
  - Each target field has an ordered list of regex patterns ranked by specificity.
  - The first pattern that yields a non-None result is used.
  - Monetary values are normalised to a plain float (currency symbols and
    thousand-separators stripped; crore/lakh/million/billion suffixes resolved).
  - A confidence dict is returned alongside values so the UI can flag low-quality
    extractions.

All amounts are returned in the unit as written in the document (no currency
conversion is performed). The caller decides the display currency.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Target fields (aligned with the project specification)
# ---------------------------------------------------------------------------

FINANCIAL_FIELDS = [
    "revenue",
    "cost_of_revenue",
    "operating_profit",
    "ebit",
    "ebitda",
    "net_profit",
    "cash",
    "inventory",
    "accounts_receivable",
    "accounts_payable",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_liabilities",
    "equity",
    "long_term_debt",
    "short_term_debt",
    "interest_expense",
    "operating_cash_flow",
    "investing_cash_flow",
    "financing_cash_flow",
    "depreciation_amortisation",
    "tax_expense",
    "gross_profit",
    "net_worth",
]


@dataclass
class ParsedFinancials:
    """Result of parsing one document's OCR text."""
    fields: Dict[str, Optional[float]] = field(default_factory=dict)
    confidence: Dict[str, float] = field(default_factory=dict)  # 0.0 – 1.0 per field
    warnings: List[str] = field(default_factory=list)

    @property
    def extracted_count(self) -> int:
        return sum(1 for v in self.fields.values() if v is not None)

    @property
    def overall_confidence(self) -> float:
        vals = [v for v in self.confidence.values() if v > 0]
        return round(sum(vals) / len(vals), 3) if vals else 0.0


# ---------------------------------------------------------------------------
# Regex helpers
# ---------------------------------------------------------------------------

# Number pattern: handles "1,23,456.78", "1234567", "1,234,567.89"
# Optionally preceded by currency symbols: ₹ $ £ € ¥
_CURRENCY_SYM = r"[₹$£€¥]?\s*"
_NUM = r"-?\s*" + _CURRENCY_SYM + r"([\d,]+(?:\.\d+)?)"

# Suffix multipliers (Indian and international notation)
_SUFFIXES: Dict[str, float] = {
    "crore": 1e7,
    "cr":    1e7,
    "lakh":  1e5,
    "lac":   1e5,
    "l":     1e5,
    "million": 1e6,
    "mn":    1e6,
    "m":     1e6,
    "billion": 1e9,
    "bn":    1e9,
    "b":     1e9,
    "thousand": 1e3,
    "k":     1e3,
}

_SUFFIX_PATTERN = re.compile(
    r"([\d,]+(?:\.\d+)?)\s*(" + "|".join(_SUFFIXES.keys()) + r")\b",
    re.IGNORECASE,
)


def _parse_number(text: str) -> Optional[float]:
    """
    Convert a string like '1,23,456.78', '45.6 crore', '12.5 million' to float.
    Returns None if the string cannot be interpreted as a number.
    """
    if not text:
        return None
    t = text.strip()

    # Suffix check first
    m = _SUFFIX_PATTERN.search(t)
    if m:
        base = float(m.group(1).replace(",", ""))
        mult = _SUFFIXES.get(m.group(2).lower(), 1.0)
        return round(base * mult, 2)

    # Strip currency symbols and thousand separators
    t = re.sub(r"[₹$£€¥\s]", "", t)
    t = t.replace(",", "")
    # Handle parenthesised negatives: (1234) → -1234
    if t.startswith("(") and t.endswith(")"):
        t = "-" + t[1:-1]
    try:
        return float(t)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Field-specific pattern groups
# Each entry: (label_pattern, value_after_label_pattern)
# We capture the value immediately following the label.
# ---------------------------------------------------------------------------

def _build_label_pattern(labels: List[str]) -> re.Pattern:
    """Build a regex that captures a numeric value after any of *labels*."""
    label_re = "|".join(re.escape(l) for l in labels)
    return re.compile(
        r"(?:" + label_re + r")\s*[:\-–—]?\s*" + _NUM,
        re.IGNORECASE | re.MULTILINE,
    )


_FIELD_PATTERNS: Dict[str, re.Pattern] = {
    "revenue": _build_label_pattern([
        "Total Revenue", "Revenue from Operations", "Net Revenue",
        "Revenue from Contracts", "Turnover", "Net Sales", "Total Sales",
        "Revenue", "Sales",
    ]),
    "cost_of_revenue": _build_label_pattern([
        "Cost of Revenue", "Cost of Goods Sold", "COGS",
        "Cost of Sales", "Cost of Materials Consumed", "Direct Costs",
    ]),
    "gross_profit": _build_label_pattern([
        "Gross Profit", "Gross Margin",
    ]),
    "operating_profit": _build_label_pattern([
        "Operating Profit", "Profit from Operations", "Operating Income",
        "PBIT", "Profit Before Interest and Tax",
    ]),
    "ebit": _build_label_pattern([
        r"EBIT\b", "Earnings Before Interest and Tax",
        "Profit Before Interest and Tax",
    ]),
    "ebitda": _build_label_pattern([
        r"EBITDA\b", "Earnings Before Interest, Tax, Depreciation and Amortisation",
        "Earnings Before Interest Tax Depreciation Amortisation",
    ]),
    "net_profit": _build_label_pattern([
        "Net Profit", "Net Income", "Profit After Tax", "PAT",
        "Profit for the Year", "Net Earnings", "Net Profit After Tax",
    ]),
    "cash": _build_label_pattern([
        "Cash and Cash Equivalents", "Cash and Bank Balances",
        "Cash & Cash Equivalents", "Cash in Hand", "Cash Balance", "Cash",
    ]),
    "inventory": _build_label_pattern([
        "Inventories", "Inventory", "Stock in Trade", "Closing Stock",
    ]),
    "accounts_receivable": _build_label_pattern([
        "Trade Receivables", "Accounts Receivable", "Debtors",
        "Sundry Debtors", "Trade Debtors",
    ]),
    "accounts_payable": _build_label_pattern([
        "Trade Payables", "Accounts Payable", "Creditors",
        "Sundry Creditors", "Trade Creditors",
    ]),
    "current_assets": _build_label_pattern([
        "Total Current Assets", "Current Assets",
    ]),
    "current_liabilities": _build_label_pattern([
        "Total Current Liabilities", "Current Liabilities",
    ]),
    "total_assets": _build_label_pattern([
        "Total Assets", "Aggregate of Assets",
    ]),
    "total_liabilities": _build_label_pattern([
        "Total Liabilities", "Total Debt and Liabilities",
    ]),
    "equity": _build_label_pattern([
        "Shareholders.{0,10}Equity", "Shareholder.{0,10}Funds",
        "Stockholders.{0,10}Equity", "Total Equity",
        "Owners.{0,10}Equity", "Net Worth", "Book Value",
    ]),
    "long_term_debt": _build_label_pattern([
        "Long.?Term Borrowings", "Long.?Term Debt", "Non.?Current Borrowings",
        "Term Loans",
    ]),
    "short_term_debt": _build_label_pattern([
        "Short.?Term Borrowings", "Short.?Term Debt", "Current Borrowings",
        "Bank Overdraft",
    ]),
    "interest_expense": _build_label_pattern([
        "Finance Costs", "Interest Expense", "Interest Costs",
        "Borrowing Costs", "Interest Paid",
    ]),
    "operating_cash_flow": _build_label_pattern([
        "Cash Flow from Operating Activities",
        "Net Cash from Operating Activities",
        "Cash Generated from Operations",
        r"Operating Activities\s+[:\-]",
    ]),
    "investing_cash_flow": _build_label_pattern([
        "Cash Flow from Investing Activities",
        "Net Cash from Investing Activities",
        r"Investing Activities\s+[:\-]",
    ]),
    "financing_cash_flow": _build_label_pattern([
        "Cash Flow from Financing Activities",
        "Net Cash from Financing Activities",
        r"Financing Activities\s+[:\-]",
    ]),
    "depreciation_amortisation": _build_label_pattern([
        "Depreciation and Amortisation", "Depreciation & Amortisation",
        "Depreciation", "Amortisation",
    ]),
    "tax_expense": _build_label_pattern([
        "Income Tax Expense", "Tax Expense", "Provision for Tax",
        "Current Tax", "Income Tax",
    ]),
    "net_worth": _build_label_pattern([
        "Net Worth", "Net Asset Value", "Book Value of Equity",
    ]),
}


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def parse_financials(raw_text: str) -> ParsedFinancials:
    """
    Parse all target financial fields from *raw_text* (OCR output).

    Returns a ParsedFinancials with:
      - fields: {field_name: float | None}
      - confidence: {field_name: 0.0–1.0}
    """
    result = ParsedFinancials()

    # Normalise whitespace — collapse multiple spaces/newlines into single space
    normalised = re.sub(r"[ \t]+", " ", raw_text)
    normalised = re.sub(r"\n{2,}", "\n", normalised)

    for field_name, pattern in _FIELD_PATTERNS.items():
        value, conf = _extract_field(normalised, pattern, field_name)
        result.fields[field_name] = value
        result.confidence[field_name] = conf

    # --- Post-processing: derive EBITDA if not found directly
    if result.fields.get("ebitda") is None:
        ebit = result.fields.get("ebit")
        da = result.fields.get("depreciation_amortisation")
        if ebit is not None and da is not None:
            result.fields["ebitda"] = round(ebit + da, 2)
            result.confidence["ebitda"] = round(
                (result.confidence.get("ebit", 0) + result.confidence.get("depreciation_amortisation", 0)) / 2, 3
            )

    # --- Post-processing: derive EBIT from net_profit + tax + interest if EBIT missing
    if result.fields.get("ebit") is None:
        np_ = result.fields.get("net_profit")
        tax = result.fields.get("tax_expense")
        ie = result.fields.get("interest_expense")
        if np_ is not None and tax is not None and ie is not None:
            result.fields["ebit"] = round(np_ + tax + ie, 2)
            result.confidence["ebit"] = 0.6  # derived, lower confidence

    # --- Post-processing: derive gross profit if not found
    if result.fields.get("gross_profit") is None:
        rev = result.fields.get("revenue")
        cog = result.fields.get("cost_of_revenue")
        if rev is not None and cog is not None:
            result.fields["gross_profit"] = round(rev - cog, 2)
            result.confidence["gross_profit"] = min(
                result.confidence.get("revenue", 0),
                result.confidence.get("cost_of_revenue", 0),
            )

    extracted = result.extracted_count
    total = len(FINANCIAL_FIELDS)
    logger.info(
        "Financial parsing complete",
        extra={"extracted": extracted, "total": total, "confidence": result.overall_confidence},
    )

    if extracted < total * 0.3:
        result.warnings.append(
            f"Only {extracted}/{total} financial fields were extracted. "
            "The document may be poorly formatted, scanned at low resolution, "
            "or in an unsupported layout."
        )

    return result


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _extract_field(
    text: str,
    pattern: re.Pattern,
    field_name: str,
) -> Tuple[Optional[float], float]:
    """
    Find the first match of *pattern* in *text*, parse the captured number,
    and return (value, confidence).

    Confidence is 1.0 for a clean exact match, 0.7 for a match with caveats.
    Returns (None, 0.0) if no match is found.
    """
    matches = list(pattern.finditer(text))
    if not matches:
        return None, 0.0

    # Use the first (highest-priority) match
    m = matches[0]
    raw_val = m.group(1)  # captured number group
    value = _parse_number(raw_val)

    if value is None:
        return None, 0.0

    # Assign confidence — multiple matches suggest ambiguity
    confidence = 1.0 if len(matches) == 1 else 0.75

    # Zero values are valid but flag them
    if value == 0.0:
        confidence = min(confidence, 0.5)

    return value, round(confidence, 3)
