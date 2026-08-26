"""
Financial ratio interpreter.

For every RatioResult produced by calculator.py this module provides:
  - risk_level:      very_low | low | medium | high | very_high
  - interpretation:  human-readable sentence explaining what the value means
  - benchmark_min:   lower end of the healthy range
  - benchmark_max:   upper end of the healthy range
  - health_signal:   positive | neutral | negative (for dashboard colouring)

Benchmarks are based on general commercial banking standards for corporate
lending. Administrators can override thresholds via the rule engine; these
are the default narrative benchmarks used for the PDF report.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from ratios.calculator import RatioResult


@dataclass
class RatioInterpretation:
    ratio_name: str
    display_name: str
    value: Optional[float]
    unit: str
    formula: str
    risk_level: str           # very_low | low | medium | high | very_high
    health_signal: str        # positive | neutral | negative
    interpretation: str
    benchmark_min: Optional[float]
    benchmark_max: Optional[float]
    benchmark_note: str = ""


# ---------------------------------------------------------------------------
# Risk level helpers
# ---------------------------------------------------------------------------

def _level(value: float, thresholds: list, labels: list) -> str:
    """
    Map *value* to a risk label using ascending *thresholds*.
    thresholds: [t1, t2, t3, t4]  → labels: [l0, l1, l2, l3, l4]
    value < t1  → labels[0]
    t1 ≤ v < t2 → labels[1]
    ...
    value ≥ t4  → labels[4]
    """
    for i, t in enumerate(thresholds):
        if value < t:
            return labels[i]
    return labels[-1]


_RISK_ASCENDING = ["very_high", "high", "medium", "low", "very_low"]   # lower is worse
_RISK_DESCENDING = ["very_low", "low", "medium", "high", "very_high"]  # higher is worse


def _signal(risk: str) -> str:
    return {
        "very_low": "positive",
        "low": "positive",
        "medium": "neutral",
        "high": "negative",
        "very_high": "negative",
    }[risk]


# ---------------------------------------------------------------------------
# Per-ratio interpretation logic
# ---------------------------------------------------------------------------

def _interpret_current_ratio(v: float) -> RatioInterpretation:
    if v < 1.0:
        risk, text = "very_high", f"Critical: Current Ratio of {v:.2f}x is below 1.0. The company cannot cover short-term liabilities with current assets — immediate liquidity risk."
    elif v < 1.2:
        risk, text = "high", f"Weak: Current Ratio of {v:.2f}x is below the 1.2 comfort threshold. Liquidity buffer is thin."
    elif v < 1.5:
        risk, text = "medium", f"Acceptable: Current Ratio of {v:.2f}x meets minimum requirements but leaves limited buffer for unexpected cash demands."
    elif v <= 3.0:
        risk, text = "low", f"Healthy: Current Ratio of {v:.2f}x indicates strong short-term liquidity. The company can comfortably meet near-term obligations."
    else:
        risk, text = "very_low", f"Excellent: Current Ratio of {v:.2f}x is well above the benchmark. The company has a strong liquidity cushion."
    return RatioInterpretation("current_ratio", "Current Ratio", v, "x", "Current Assets ÷ Current Liabilities", risk, _signal(risk), text, 1.5, 3.0)


def _interpret_quick_ratio(v: float) -> RatioInterpretation:
    if v < 0.5:
        risk, text = "very_high", f"Critical: Quick Ratio of {v:.2f}x signals severe short-term liquidity stress. Liquid assets are insufficient to cover even half of current liabilities."
    elif v < 0.8:
        risk, text = "high", f"Weak: Quick Ratio of {v:.2f}x is below the 0.8 safety threshold. The company may struggle to meet immediate obligations without liquidating inventory."
    elif v < 1.0:
        risk, text = "medium", f"Moderate: Quick Ratio of {v:.2f}x is approaching the 1:1 benchmark. Manageable but warrants monitoring."
    elif v <= 2.0:
        risk, text = "low", f"Healthy: Quick Ratio of {v:.2f}x. Liquid assets adequately cover current liabilities without relying on inventory."
    else:
        risk, text = "very_low", f"Excellent: Quick Ratio of {v:.2f}x. Highly liquid position."
    return RatioInterpretation("quick_ratio", "Quick Ratio", v, "x", "(Current Assets − Inventory) ÷ Current Liabilities", risk, _signal(risk), text, 1.0, 2.0)


def _interpret_debt_equity(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Debt-Equity Ratio of {v:.2f}x is negative, indicating negative equity (technical insolvency)."
    elif v <= 1.0:
        risk, text = "very_low", f"Excellent: Debt-Equity Ratio of {v:.2f}x reflects conservative financing with equity dominance."
    elif v <= 1.5:
        risk, text = "low", f"Good: Debt-Equity Ratio of {v:.2f}x is within acceptable lending parameters."
    elif v <= 2.0:
        risk, text = "medium", f"Moderate: Debt-Equity Ratio of {v:.2f}x indicates elevated leverage. Manageable if cash flows are stable."
    elif v <= 2.5:
        risk, text = "high", f"High: Debt-Equity Ratio of {v:.2f}x approaches the lending limit of 2.5x. Increased default risk."
    else:
        risk, text = "very_high", f"Critical: Debt-Equity Ratio of {v:.2f}x exceeds the 2.5x threshold. Excessive leverage significantly increases default risk."
    return RatioInterpretation("debt_equity_ratio", "Debt-Equity Ratio", v, "x", "Total Liabilities ÷ Shareholders' Equity", risk, _signal(risk), text, 0.5, 2.0)


def _interpret_debt_ratio(v: float) -> RatioInterpretation:
    if v < 0.3:
        risk, text = "very_low", f"Excellent: Debt Ratio of {v:.2f}x shows that only {v*100:.1f}% of assets are financed by debt."
    elif v <= 0.5:
        risk, text = "low", f"Good: Debt Ratio of {v:.2f}x. Balanced financing structure."
    elif v <= 0.65:
        risk, text = "medium", f"Moderate: Debt Ratio of {v:.2f}x. Majority of assets funded by debt — monitor debt servicing capacity."
    elif v <= 0.8:
        risk, text = "high", f"High: Debt Ratio of {v:.2f}x. Company is heavily debt-financed; {v*100:.1f}% of assets are funded by creditors."
    else:
        risk, text = "very_high", f"Critical: Debt Ratio of {v:.2f}x. Over 80% of assets funded by debt — extremely high insolvency risk."
    return RatioInterpretation("debt_ratio", "Debt Ratio", v, "x", "Total Liabilities ÷ Total Assets", risk, _signal(risk), text, 0.3, 0.6)


def _interpret_current_asset_ratio(v: float) -> RatioInterpretation:
    if v < 0.2:
        risk, text = "high", f"Low: Current Asset Ratio of {v:.2f}x. Only {v*100:.1f}% of assets are current — limited liquidity flexibility."
    elif v <= 0.4:
        risk, text = "medium", f"Moderate: Current Asset Ratio of {v:.2f}x is typical for asset-heavy industries."
    elif v <= 0.6:
        risk, text = "low", f"Healthy: Current Asset Ratio of {v:.2f}x shows a balanced asset structure."
    else:
        risk, text = "very_low", f"High Liquidity: Current Asset Ratio of {v:.2f}x — predominantly liquid assets."
    return RatioInterpretation("current_asset_ratio", "Current Asset Ratio", v, "x", "Current Assets ÷ Total Assets", risk, _signal(risk), text, 0.3, 0.6)


def _interpret_working_capital(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Negative Working Capital of RM {v:,.0f}. Current liabilities exceed current assets — immediate liquidity concern."
    elif v == 0:
        risk, text = "high", "Borderline: Working Capital is zero. No buffer for unexpected short-term obligations."
    else:
        risk, text = "low", f"Positive: Working Capital of RM {v:,.0f} provides a buffer for short-term operations."
    return RatioInterpretation("working_capital", "Working Capital", v, "RM", "Current Assets − Current Liabilities", risk, _signal(risk), text, None, None, "Positive = healthy; negative = risk")


def _interpret_gross_profit_margin(v: float) -> RatioInterpretation:
    if v < 10:
        risk, text = "very_high", f"Very Low: Gross Profit Margin of {v:.2f}% leaves almost no room to cover operating expenses."
    elif v < 20:
        risk, text = "high", f"Low: Gross Profit Margin of {v:.2f}%. Cost of goods is consuming a large share of revenue."
    elif v < 30:
        risk, text = "medium", f"Moderate: Gross Profit Margin of {v:.2f}%. Acceptable for trade/distribution businesses."
    elif v < 50:
        risk, text = "low", f"Good: Gross Profit Margin of {v:.2f}%. Adequate cost efficiency."
    else:
        risk, text = "very_low", f"Excellent: Gross Profit Margin of {v:.2f}%. Strong pricing power and/or low production costs."
    return RatioInterpretation("gross_profit_margin", "Gross Profit Margin", v, "%", "(Gross Profit ÷ Revenue) × 100", risk, _signal(risk), text, 20.0, 60.0)


def _interpret_operating_margin(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Operating Margin of {v:.2f}% — the core business is losing money before interest and tax."
    elif v < 5:
        risk, text = "high", f"Weak: Operating Margin of {v:.2f}%. Very little profit generated from operations."
    elif v < 10:
        risk, text = "medium", f"Moderate: Operating Margin of {v:.2f}%. Sufficient to service debt but minimal slack."
    elif v < 20:
        risk, text = "low", f"Good: Operating Margin of {v:.2f}%. Healthy operating efficiency."
    else:
        risk, text = "very_low", f"Excellent: Operating Margin of {v:.2f}%. Strong operational profitability."
    return RatioInterpretation("operating_margin", "Operating Profit Margin", v, "%", "(Operating Profit ÷ Revenue) × 100", risk, _signal(risk), text, 10.0, 25.0)


def _interpret_net_profit_margin(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Net Profit Margin of {v:.2f}% — company is loss-making after all expenses."
    elif v < 3:
        risk, text = "high", f"Weak: Net Profit Margin of {v:.2f}%. Razor-thin profitability; highly vulnerable to cost increases."
    elif v < 8:
        risk, text = "medium", f"Moderate: Net Profit Margin of {v:.2f}%. Adequate for lending consideration with close monitoring."
    elif v < 15:
        risk, text = "low", f"Good: Net Profit Margin of {v:.2f}%. Solid bottom-line profitability."
    else:
        risk, text = "very_low", f"Excellent: Net Profit Margin of {v:.2f}%. Strong overall profitability."
    return RatioInterpretation("net_profit_margin", "Net Profit Margin", v, "%", "(Net Profit ÷ Revenue) × 100", risk, _signal(risk), text, 5.0, 20.0)


def _interpret_roa(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: ROA of {v:.2f}% — assets are not generating returns; company is loss-making."
    elif v < 2:
        risk, text = "high", f"Low: ROA of {v:.2f}% indicates poor asset utilisation."
    elif v < 5:
        risk, text = "medium", f"Moderate: ROA of {v:.2f}%. Assets generating modest returns."
    elif v < 10:
        risk, text = "low", f"Good: ROA of {v:.2f}%. Assets employed efficiently."
    else:
        risk, text = "very_low", f"Excellent: ROA of {v:.2f}%. Highly efficient use of assets."
    return RatioInterpretation("return_on_assets", "Return on Assets (ROA)", v, "%", "(Net Profit ÷ Total Assets) × 100", risk, _signal(risk), text, 5.0, 15.0)


def _interpret_roe(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: ROE of {v:.2f}% — shareholders' equity is being eroded."
    elif v < 5:
        risk, text = "high", f"Weak: ROE of {v:.2f}%. Returns below the minimum institutional threshold."
    elif v < 10:
        risk, text = "medium", f"Moderate: ROE of {v:.2f}%. Marginal shareholder returns."
    elif v < 20:
        risk, text = "low", f"Good: ROE of {v:.2f}%. Solid return on shareholders' investment."
    else:
        risk, text = "very_low", f"Excellent: ROE of {v:.2f}%. Exceptional shareholder value creation."
    return RatioInterpretation("return_on_equity", "Return on Equity (ROE)", v, "%", "(Net Profit ÷ Shareholders' Equity) × 100", risk, _signal(risk), text, 10.0, 25.0)


def _interpret_icr(v: float) -> RatioInterpretation:
    if v < 1.0:
        risk, text = "very_high", f"Critical: ICR of {v:.2f}x — EBIT does not cover interest payments. Immediate default risk."
    elif v < 1.5:
        risk, text = "high", f"Weak: ICR of {v:.2f}x is below the minimum threshold of 1.5x. Very limited debt servicing capacity."
    elif v < 2.5:
        risk, text = "medium", f"Moderate: ICR of {v:.2f}x meets minimum requirements with limited buffer."
    elif v < 5.0:
        risk, text = "low", f"Good: ICR of {v:.2f}x. Earnings comfortably cover interest obligations."
    else:
        risk, text = "very_low", f"Excellent: ICR of {v:.2f}x. Strong earnings coverage for interest payments."
    return RatioInterpretation("interest_coverage_ratio", "Interest Coverage Ratio (ICR)", v, "x", "EBIT ÷ Interest Expense", risk, _signal(risk), text, 2.5, 5.0)


def _interpret_cash_flow_ratio(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Cash Flow Ratio of {v:.2f}x — negative operating cash flow cannot cover current liabilities."
    elif v < 0.4:
        risk, text = "high", f"Weak: Cash Flow Ratio of {v:.2f}x. Operating cash flow insufficient to cover current liabilities."
    elif v < 0.7:
        risk, text = "medium", f"Moderate: Cash Flow Ratio of {v:.2f}x provides some coverage."
    elif v <= 1.0:
        risk, text = "low", f"Good: Cash Flow Ratio of {v:.2f}x. Operating cash flow adequately covers current liabilities."
    else:
        risk, text = "very_low", f"Excellent: Cash Flow Ratio of {v:.2f}x. Strong cash generation relative to short-term obligations."
    return RatioInterpretation("cash_flow_ratio", "Cash Flow Ratio", v, "x", "Operating Cash Flow ÷ Current Liabilities", risk, _signal(risk), text, 0.5, 1.0)


def _interpret_ocf_ratio(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Negative Operating Cash Flow Ratio of {v:.2f}% — operations are burning cash."
    elif v < 5:
        risk, text = "high", f"Weak: Operating Cash Flow Ratio of {v:.2f}%. Very little cash generated per rupee of revenue."
    elif v < 10:
        risk, text = "medium", f"Moderate: Operating Cash Flow Ratio of {v:.2f}%."
    else:
        risk, text = "low", f"Good: Operating Cash Flow Ratio of {v:.2f}%. Healthy cash conversion."
    return RatioInterpretation("operating_cash_flow_ratio", "Operating Cash Flow Ratio", v, "%", "(Operating Cash Flow ÷ Revenue) × 100", risk, _signal(risk), text, 10.0, 25.0)


def _interpret_asset_turnover(v: float) -> RatioInterpretation:
    if v < 0.3:
        risk, text = "high", f"Low: Asset Turnover of {v:.2f}x. Revenue generated is low relative to asset base — possible asset underutilisation."
    elif v < 0.7:
        risk, text = "medium", f"Moderate: Asset Turnover of {v:.2f}x. Typical for capital-intensive industries."
    elif v <= 1.5:
        risk, text = "low", f"Good: Asset Turnover of {v:.2f}x. Efficient use of asset base to generate revenue."
    else:
        risk, text = "very_low", f"Excellent: Asset Turnover of {v:.2f}x. High revenue generation relative to assets."
    return RatioInterpretation("asset_turnover", "Asset Turnover Ratio", v, "x", "Revenue ÷ Total Assets", risk, _signal(risk), text, 0.5, 1.5)


def _interpret_inventory_turnover(v: float) -> RatioInterpretation:
    if v < 2:
        risk, text = "high", f"Low: Inventory Turnover of {v:.2f}x. Slow-moving stock may indicate weak sales or poor inventory management."
    elif v < 4:
        risk, text = "medium", f"Moderate: Inventory Turnover of {v:.2f}x. Adequate stock cycling."
    elif v <= 10:
        risk, text = "low", f"Good: Inventory Turnover of {v:.2f}x. Efficient inventory management."
    else:
        risk, text = "very_low", f"Excellent: Inventory Turnover of {v:.2f}x. Very fast inventory cycling — strong sales or lean inventory."
    return RatioInterpretation("inventory_turnover", "Inventory Turnover Ratio", v, "x", "Cost of Revenue ÷ Inventory", risk, _signal(risk), text, 4.0, 12.0)


def _interpret_receivable_turnover(v: float) -> RatioInterpretation:
    if v < 4:
        risk, text = "high", f"Low: Receivable Turnover of {v:.2f}x. Slow collection cycle — elevated credit risk."
    elif v < 8:
        risk, text = "medium", f"Moderate: Receivable Turnover of {v:.2f}x. Average collection efficiency."
    elif v <= 15:
        risk, text = "low", f"Good: Receivable Turnover of {v:.2f}x. Efficient debtor collection."
    else:
        risk, text = "very_low", f"Excellent: Receivable Turnover of {v:.2f}x. Very fast collection cycle."
    return RatioInterpretation("receivable_turnover", "Receivable Turnover Ratio", v, "x", "Revenue ÷ Accounts Receivable", risk, _signal(risk), text, 6.0, 15.0)


def _interpret_dscr(v: float) -> RatioInterpretation:
    if v < 1.0:
        risk, text = "very_high", f"Critical: DSCR of {v:.2f}x — cash flow is insufficient to service total debt obligations. Default risk is high."
    elif v < 1.2:
        risk, text = "high", f"Weak: DSCR of {v:.2f}x is below the minimum threshold of 1.2x. Limited debt servicing headroom."
    elif v < 1.5:
        risk, text = "medium", f"Moderate: DSCR of {v:.2f}x meets minimum requirements with a narrow buffer."
    elif v < 2.0:
        risk, text = "low", f"Good: DSCR of {v:.2f}x. Adequate cash flow to comfortably service debt."
    else:
        risk, text = "very_low", f"Excellent: DSCR of {v:.2f}x. Strong debt servicing capacity."
    return RatioInterpretation("debt_service_coverage_ratio", "Debt Service Coverage Ratio (DSCR)", v, "x", "(Net Profit + D&A + Interest) ÷ (Interest + Short-Term Debt)", risk, _signal(risk), text, 1.25, 2.0)


def _interpret_ebitda_margin(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: EBITDA Margin of {v:.2f}% — company fails to cover operating costs before non-cash items."
    elif v < 10:
        risk, text = "high", f"Weak: EBITDA Margin of {v:.2f}%. Limited cash earnings relative to revenue."
    elif v < 15:
        risk, text = "medium", f"Moderate: EBITDA Margin of {v:.2f}%. Acceptable for most industries."
    elif v < 25:
        risk, text = "low", f"Good: EBITDA Margin of {v:.2f}%. Strong operational cash generation."
    else:
        risk, text = "very_low", f"Excellent: EBITDA Margin of {v:.2f}%. Very high operational efficiency."
    return RatioInterpretation("ebitda_margin", "EBITDA Margin", v, "%", "(EBITDA ÷ Revenue) × 100", risk, _signal(risk), text, 12.0, 30.0)


def _interpret_financial_leverage(v: float) -> RatioInterpretation:
    if v < 0:
        risk, text = "very_high", f"Critical: Negative Financial Leverage of {v:.2f}x indicates negative equity (technical insolvency)."
    elif v <= 2.0:
        risk, text = "very_low", f"Excellent: Financial Leverage of {v:.2f}x. Conservative use of debt financing."
    elif v <= 3.0:
        risk, text = "low", f"Good: Financial Leverage of {v:.2f}x within normal lending parameters."
    elif v <= 5.0:
        risk, text = "medium", f"Moderate: Financial Leverage of {v:.2f}x. Elevated but manageable financial risk."
    elif v <= 10.0:
        risk, text = "high", f"High: Financial Leverage of {v:.2f}x. Assets funded predominantly by debt."
    else:
        risk, text = "very_high", f"Critical: Financial Leverage of {v:.2f}x. Extreme leverage — equity is minimal relative to total assets."
    return RatioInterpretation("financial_leverage", "Financial Leverage", v, "x", "Total Assets ÷ Shareholders' Equity", risk, _signal(risk), text, 1.5, 4.0)


# ---------------------------------------------------------------------------
# Dispatch table
# ---------------------------------------------------------------------------

_INTERPRETERS = {
    "current_ratio":              _interpret_current_ratio,
    "quick_ratio":                _interpret_quick_ratio,
    "debt_equity_ratio":          _interpret_debt_equity,
    "debt_ratio":                 _interpret_debt_ratio,
    "current_asset_ratio":        _interpret_current_asset_ratio,
    "working_capital":            _interpret_working_capital,
    "gross_profit_margin":        _interpret_gross_profit_margin,
    "operating_margin":           _interpret_operating_margin,
    "net_profit_margin":          _interpret_net_profit_margin,
    "return_on_assets":           _interpret_roa,
    "return_on_equity":           _interpret_roe,
    "interest_coverage_ratio":    _interpret_icr,
    "cash_flow_ratio":            _interpret_cash_flow_ratio,
    "operating_cash_flow_ratio":  _interpret_ocf_ratio,
    "asset_turnover":             _interpret_asset_turnover,
    "inventory_turnover":         _interpret_inventory_turnover,
    "receivable_turnover":        _interpret_receivable_turnover,
    "debt_service_coverage_ratio": _interpret_dscr,
    "ebitda_margin":              _interpret_ebitda_margin,
    "financial_leverage":         _interpret_financial_leverage,
}


def interpret(ratio: RatioResult) -> RatioInterpretation:
    """Interpret a single RatioResult and return a RatioInterpretation."""
    if ratio.value is None:
        return RatioInterpretation(
            ratio_name=ratio.name,
            display_name=ratio.display_name,
            value=None,
            unit=ratio.unit,
            formula=ratio.formula,
            risk_level="unknown",
            health_signal="neutral",
            interpretation="Insufficient data to calculate this ratio.",
            benchmark_min=None,
            benchmark_max=None,
        )
    fn = _INTERPRETERS.get(ratio.name)
    if fn is None:
        return RatioInterpretation(
            ratio_name=ratio.name,
            display_name=ratio.display_name,
            value=ratio.value,
            unit=ratio.unit,
            formula=ratio.formula,
            risk_level="unknown",
            health_signal="neutral",
            interpretation="No interpretation rule defined for this ratio.",
            benchmark_min=None,
            benchmark_max=None,
        )
    return fn(ratio.value)


def overall_health(interpretations: dict) -> tuple[str, str]:
    """
    Derive an overall financial health label from all interpreted ratios.
    Returns (health_label, summary_note).
    """
    counts = {"very_high": 0, "high": 0, "medium": 0, "low": 0, "very_low": 0}
    for interp in interpretations.values():
        if isinstance(interp, RatioInterpretation) and interp.risk_level in counts:
            counts[interp.risk_level] += 1

    total = sum(counts.values())
    if total == 0:
        return "unknown", "Insufficient data for overall health assessment."

    critical = counts["very_high"] + counts["high"]
    healthy = counts["low"] + counts["very_low"]

    if counts["very_high"] >= 2:
        return "critical", f"{counts['very_high']} critical risk indicators detected. Loan application carries very high risk."
    if critical > total * 0.5:
        return "poor", f"{critical} of {total} ratios indicate high or very high risk."
    if counts["medium"] > total * 0.4:
        return "moderate", "Mixed financial signals — several ratios require attention."
    if healthy > total * 0.6:
        return "good", f"{healthy} of {total} ratios indicate healthy financial performance."
    return "satisfactory", "Financial profile is broadly acceptable with some areas of concern."
