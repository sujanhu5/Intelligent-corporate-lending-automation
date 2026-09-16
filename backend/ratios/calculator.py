"""
Financial ratio calculator.

Each function takes the extracted financial fields dict and returns a RatioResult.
Division-by-zero and missing-field cases produce RatioResult with value=None
rather than raising, so the pipeline can continue with partial data.

All ratio values are returned as plain floats; percentages are NOT pre-multiplied
(so 12.5% is returned as 12.5, not 0.125). The interpreter layer decides display.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class RatioResult:
    """One computed ratio with its formula and input components."""
    name: str
    display_name: str
    value: Optional[float]
    formula: str
    components: Dict[str, Optional[float]] = field(default_factory=dict)
    is_percentage: bool = False
    unit: str = "x"       # "x" for multiples, "%" for margins, "days" for turnover in days


@dataclass
class RatioSet:
    """Full set of computed ratios for one application."""
    ratios: Dict[str, RatioResult] = field(default_factory=dict)
    missing_fields: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_div(numerator: Optional[float], denominator: Optional[float]) -> Optional[float]:
    """Return numerator/denominator or None if either is None or denominator is 0."""
    if numerator is None or denominator is None:
        return None
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def _pct(value: Optional[float]) -> Optional[float]:
    """Convert a ratio to percentage (multiply by 100)."""
    if value is None:
        return None
    return round(value * 100, 4)


def _get(fields: Dict[str, Any], key: str) -> Optional[float]:
    val = fields.get(key)
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Individual ratio functions
# ---------------------------------------------------------------------------

def current_ratio(f: Dict) -> RatioResult:
    ca = _get(f, "current_assets")
    cl = _get(f, "current_liabilities")
    return RatioResult(
        name="current_ratio",
        display_name="Current Ratio",
        value=_safe_div(ca, cl),
        formula="Current Assets ÷ Current Liabilities",
        components={"current_assets": ca, "current_liabilities": cl},
        unit="x",
    )


def quick_ratio(f: Dict) -> RatioResult:
    ca = _get(f, "current_assets")
    inv = _get(f, "inventory") or 0.0
    cl = _get(f, "current_liabilities")
    quick_assets = (ca - inv) if ca is not None else None
    return RatioResult(
        name="quick_ratio",
        display_name="Quick Ratio",
        value=_safe_div(quick_assets, cl),
        formula="(Current Assets − Inventory) ÷ Current Liabilities",
        components={"current_assets": ca, "inventory": inv, "current_liabilities": cl},
        unit="x",
    )


def debt_equity_ratio(f: Dict) -> RatioResult:
    tl = _get(f, "total_liabilities")
    eq = _get(f, "equity")
    return RatioResult(
        name="debt_equity_ratio",
        display_name="Debt-Equity Ratio",
        value=_safe_div(tl, eq),
        formula="Total Liabilities ÷ Shareholders' Equity",
        components={"total_liabilities": tl, "equity": eq},
        unit="x",
    )


def debt_ratio(f: Dict) -> RatioResult:
    tl = _get(f, "total_liabilities")
    ta = _get(f, "total_assets")
    return RatioResult(
        name="debt_ratio",
        display_name="Debt Ratio",
        value=_safe_div(tl, ta),
        formula="Total Liabilities ÷ Total Assets",
        components={"total_liabilities": tl, "total_assets": ta},
        unit="x",
    )


def current_asset_ratio(f: Dict) -> RatioResult:
    ca = _get(f, "current_assets")
    ta = _get(f, "total_assets")
    return RatioResult(
        name="current_asset_ratio",
        display_name="Current Asset Ratio",
        value=_safe_div(ca, ta),
        formula="Current Assets ÷ Total Assets",
        components={"current_assets": ca, "total_assets": ta},
        unit="x",
    )


def working_capital(f: Dict) -> RatioResult:
    ca = _get(f, "current_assets")
    cl = _get(f, "current_liabilities")
    wc = (ca - cl) if (ca is not None and cl is not None) else None
    return RatioResult(
        name="working_capital",
        display_name="Working Capital",
        value=round(wc, 2) if wc is not None else None,
        formula="Current Assets − Current Liabilities",
        components={"current_assets": ca, "current_liabilities": cl},
        unit="INR",
    )


def gross_profit_margin(f: Dict) -> RatioResult:
    gp = _get(f, "gross_profit")
    rev = _get(f, "revenue")
    # Derive gross profit if not directly available
    if gp is None:
        cogs = _get(f, "cost_of_revenue")
        if rev is not None and cogs is not None:
            gp = rev - cogs
    val = _pct(_safe_div(gp, rev))
    return RatioResult(
        name="gross_profit_margin",
        display_name="Gross Profit Margin",
        value=val,
        formula="(Gross Profit ÷ Revenue) × 100",
        components={"gross_profit": gp, "revenue": rev},
        is_percentage=True,
        unit="%",
    )


def operating_margin(f: Dict) -> RatioResult:
    op = _get(f, "operating_profit")
    rev = _get(f, "revenue")
    val = _pct(_safe_div(op, rev))
    return RatioResult(
        name="operating_margin",
        display_name="Operating Profit Margin",
        value=val,
        formula="(Operating Profit ÷ Revenue) × 100",
        components={"operating_profit": op, "revenue": rev},
        is_percentage=True,
        unit="%",
    )


def net_profit_margin(f: Dict) -> RatioResult:
    np_ = _get(f, "net_profit")
    rev = _get(f, "revenue")
    val = _pct(_safe_div(np_, rev))
    return RatioResult(
        name="net_profit_margin",
        display_name="Net Profit Margin",
        value=val,
        formula="(Net Profit ÷ Revenue) × 100",
        components={"net_profit": np_, "revenue": rev},
        is_percentage=True,
        unit="%",
    )


def return_on_assets(f: Dict) -> RatioResult:
    np_ = _get(f, "net_profit")
    ta = _get(f, "total_assets")
    val = _pct(_safe_div(np_, ta))
    return RatioResult(
        name="return_on_assets",
        display_name="Return on Assets (ROA)",
        value=val,
        formula="(Net Profit ÷ Total Assets) × 100",
        components={"net_profit": np_, "total_assets": ta},
        is_percentage=True,
        unit="%",
    )


def return_on_equity(f: Dict) -> RatioResult:
    np_ = _get(f, "net_profit")
    eq = _get(f, "equity")
    val = _pct(_safe_div(np_, eq))
    return RatioResult(
        name="return_on_equity",
        display_name="Return on Equity (ROE)",
        value=val,
        formula="(Net Profit ÷ Shareholders' Equity) × 100",
        components={"net_profit": np_, "equity": eq},
        is_percentage=True,
        unit="%",
    )


def interest_coverage_ratio(f: Dict) -> RatioResult:
    ebit = _get(f, "ebit")
    ie = _get(f, "interest_expense")
    # Derive EBIT if not directly available
    if ebit is None:
        np_ = _get(f, "net_profit")
        tax = _get(f, "tax_expense")
        if np_ is not None and ie is not None and tax is not None:
            ebit = np_ + tax + ie
        elif np_ is not None and ie is not None:
            ebit = np_ + ie  # approximate (no tax data)
    return RatioResult(
        name="interest_coverage_ratio",
        display_name="Interest Coverage Ratio (ICR)",
        value=_safe_div(ebit, ie),
        formula="EBIT ÷ Interest Expense",
        components={"ebit": ebit, "interest_expense": ie},
        unit="x",
    )


def cash_flow_ratio(f: Dict) -> RatioResult:
    ocf = _get(f, "operating_cash_flow")
    cl = _get(f, "current_liabilities")
    return RatioResult(
        name="cash_flow_ratio",
        display_name="Cash Flow Ratio",
        value=_safe_div(ocf, cl),
        formula="Operating Cash Flow ÷ Current Liabilities",
        components={"operating_cash_flow": ocf, "current_liabilities": cl},
        unit="x",
    )


def operating_cash_flow_ratio(f: Dict) -> RatioResult:
    ocf = _get(f, "operating_cash_flow")
    rev = _get(f, "revenue")
    val = _pct(_safe_div(ocf, rev))
    return RatioResult(
        name="operating_cash_flow_ratio",
        display_name="Operating Cash Flow Ratio",
        value=val,
        formula="(Operating Cash Flow ÷ Revenue) × 100",
        components={"operating_cash_flow": ocf, "revenue": rev},
        is_percentage=True,
        unit="%",
    )


def asset_turnover(f: Dict) -> RatioResult:
    rev = _get(f, "revenue")
    ta = _get(f, "total_assets")
    return RatioResult(
        name="asset_turnover",
        display_name="Asset Turnover Ratio",
        value=_safe_div(rev, ta),
        formula="Revenue ÷ Total Assets",
        components={"revenue": rev, "total_assets": ta},
        unit="x",
    )


def inventory_turnover(f: Dict) -> RatioResult:
    cogs = _get(f, "cost_of_revenue")
    inv = _get(f, "inventory")
    return RatioResult(
        name="inventory_turnover",
        display_name="Inventory Turnover Ratio",
        value=_safe_div(cogs, inv),
        formula="Cost of Revenue ÷ Inventory",
        components={"cost_of_revenue": cogs, "inventory": inv},
        unit="x",
    )


def receivable_turnover(f: Dict) -> RatioResult:
    rev = _get(f, "revenue")
    ar = _get(f, "accounts_receivable")
    return RatioResult(
        name="receivable_turnover",
        display_name="Receivable Turnover Ratio",
        value=_safe_div(rev, ar),
        formula="Revenue ÷ Accounts Receivable",
        components={"revenue": rev, "accounts_receivable": ar},
        unit="x",
    )


def debt_service_coverage_ratio(f: Dict) -> RatioResult:
    """
    DSCR = (Net Profit + Depreciation + Interest Expense) ÷
           (Interest Expense + Short-Term Debt)

    If Short-Term Debt (principal repayment proxy) is unavailable,
    we use 2× Interest Expense as a conservative estimate of total debt service.
    """
    np_ = _get(f, "net_profit")
    da = _get(f, "depreciation_amortisation") or 0.0
    ie = _get(f, "interest_expense")
    std = _get(f, "short_term_debt")

    if np_ is None or ie is None:
        return RatioResult(
            name="debt_service_coverage_ratio",
            display_name="Debt Service Coverage Ratio (DSCR)",
            value=None,
            formula="(Net Profit + D&A + Interest) ÷ (Interest + Short-Term Debt)",
            components={"net_profit": np_, "depreciation_amortisation": da, "interest_expense": ie, "short_term_debt": std},
            unit="x",
        )

    numerator = np_ + da + ie
    denominator = ie + (std if std is not None else ie)  # conservative fallback

    return RatioResult(
        name="debt_service_coverage_ratio",
        display_name="Debt Service Coverage Ratio (DSCR)",
        value=_safe_div(numerator, denominator),
        formula="(Net Profit + D&A + Interest) ÷ (Interest + Short-Term Debt)",
        components={
            "net_profit": np_,
            "depreciation_amortisation": da,
            "interest_expense": ie,
            "short_term_debt": std,
        },
        unit="x",
    )


def ebitda_margin(f: Dict) -> RatioResult:
    ebitda = _get(f, "ebitda")
    rev = _get(f, "revenue")
    # Derive EBITDA if not extracted
    if ebitda is None:
        ebit = _get(f, "ebit")
        da = _get(f, "depreciation_amortisation")
        if ebit is not None and da is not None:
            ebitda = ebit + da
    val = _pct(_safe_div(ebitda, rev))
    return RatioResult(
        name="ebitda_margin",
        display_name="EBITDA Margin",
        value=val,
        formula="(EBITDA ÷ Revenue) × 100",
        components={"ebitda": ebitda, "revenue": rev},
        is_percentage=True,
        unit="%",
    )


def financial_leverage(f: Dict) -> RatioResult:
    ta = _get(f, "total_assets")
    eq = _get(f, "equity")
    return RatioResult(
        name="financial_leverage",
        display_name="Financial Leverage",
        value=_safe_div(ta, eq),
        formula="Total Assets ÷ Shareholders' Equity",
        components={"total_assets": ta, "equity": eq},
        unit="x",
    )


# ---------------------------------------------------------------------------
# Orchestrator — compute all ratios from a field dict
# ---------------------------------------------------------------------------

_ALL_RATIO_FUNCTIONS = [
    current_ratio,
    quick_ratio,
    debt_equity_ratio,
    debt_ratio,
    current_asset_ratio,
    working_capital,
    gross_profit_margin,
    operating_margin,
    net_profit_margin,
    return_on_assets,
    return_on_equity,
    interest_coverage_ratio,
    cash_flow_ratio,
    operating_cash_flow_ratio,
    asset_turnover,
    inventory_turnover,
    receivable_turnover,
    debt_service_coverage_ratio,
    ebitda_margin,
    financial_leverage,
]


def calculate_all(extracted_fields: Dict[str, Any]) -> RatioSet:
    """
    Compute every ratio from *extracted_fields* (the dict stored in OCRData).

    Returns RatioSet with:
      - ratios:          {ratio_name: RatioResult}
      - missing_fields:  field names that were None in input
      - warnings:        human-readable notes about data gaps
    """
    # Identify which fields are missing
    from ocr.parser import FINANCIAL_FIELDS
    missing = [f for f in FINANCIAL_FIELDS if extracted_fields.get(f) is None]

    result_set = RatioSet(missing_fields=missing)

    for fn in _ALL_RATIO_FUNCTIONS:
        try:
            r = fn(extracted_fields)
            result_set.ratios[r.name] = r
        except Exception as exc:
            logger.warning("Ratio function %s failed: %s", fn.__name__, exc)
            result_set.warnings.append(f"Could not compute {fn.__name__}: {exc}")

    computed = sum(1 for r in result_set.ratios.values() if r.value is not None)
    total = len(_ALL_RATIO_FUNCTIONS)

    if computed < total * 0.5:
        result_set.warnings.append(
            f"Only {computed}/{total} ratios could be calculated. "
            "Key financial fields may be missing from OCR extraction."
        )

    logger.info(
        "Ratio calculation complete",
        extra={"computed": computed, "total": total, "missing_fields": len(missing)},
    )
    return result_set
