"""
PDF Report Builder — generates a multi-section credit assessment report using ReportLab.

Sections:
  Cover Page          — Institution header, application reference, confidentiality notice
  1. Application Overview  — loan details, pipeline stages, assigned officer
  2. Company Profile        — company info, contact, incorporation
  3. Submitted Documents    — table of uploaded files with status
  4. OCR Extraction Summary — extracted financial figures
  5. Financial Ratios       — all computed ratios with risk levels and interpretations
  6. Rule Engine Evaluation — per-rule pass/fail table with summary verdict
  7. ML Prediction          — model, probability, risk score, SHAP contributors
  8. Recommendation         — combined recommendation paragraph
  9. Officer Notes          — free-text notes from the assigned officer
  Footer                — page number, generation timestamp, confidentiality watermark
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    HRFlowable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Design constants
# ---------------------------------------------------------------------------

PAGE_W, PAGE_H = A4
MARGIN = 2.0 * cm

# Brand palette
C_NAVY      = colors.HexColor("#1A2E4A")
C_BLUE      = colors.HexColor("#2471A3")
C_LIGHT_BG  = colors.HexColor("#EBF5FB")
C_HEADER_BG = colors.HexColor("#D6EAF8")

C_GREEN      = colors.HexColor("#1E8449")
C_GREEN_SOFT = colors.HexColor("#D5F5E3")
C_AMBER      = colors.HexColor("#D68910")
C_AMBER_SOFT = colors.HexColor("#FDEBD0")
C_RED        = colors.HexColor("#C0392B")
C_RED_SOFT   = colors.HexColor("#FADBD8")
C_ORANGE     = colors.HexColor("#CA6F1E")
C_ORANGE_SOFT= colors.HexColor("#FAE5D3")
C_GREY_LIGHT = colors.HexColor("#F2F3F4")
C_GREY_RULE  = colors.HexColor("#BDC3C7")
C_WHITE      = colors.white

INSTITUTION_NAME = "Corporate Lending Automation System"
INSTITUTION_SUB  = "Intelligent Credit Assessment Platform"


# ---------------------------------------------------------------------------
# Style helpers
# ---------------------------------------------------------------------------

def _styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "cover_title", fontSize=22, leading=28, textColor=C_NAVY,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ),
        "cover_sub": ParagraphStyle(
            "cover_sub", fontSize=13, leading=18, textColor=C_BLUE,
            alignment=TA_CENTER, fontName="Helvetica",
        ),
        "cover_label": ParagraphStyle(
            "cover_label", fontSize=10, leading=14, textColor=colors.grey,
            alignment=TA_CENTER, fontName="Helvetica",
        ),
        "cover_value": ParagraphStyle(
            "cover_value", fontSize=12, leading=16, textColor=C_NAVY,
            alignment=TA_CENTER, fontName="Helvetica-Bold",
        ),
        "section_header": ParagraphStyle(
            "section_header", fontSize=13, leading=18, textColor=C_WHITE,
            fontName="Helvetica-Bold", leftIndent=6,
        ),
        "body": ParagraphStyle(
            "body", fontSize=9, leading=13, textColor=colors.black,
            fontName="Helvetica",
        ),
        "body_bold": ParagraphStyle(
            "body_bold", fontSize=9, leading=13, textColor=C_NAVY,
            fontName="Helvetica-Bold",
        ),
        "small": ParagraphStyle(
            "small", fontSize=8, leading=11, textColor=colors.grey,
            fontName="Helvetica",
        ),
        "cell_wrap": ParagraphStyle(
            "cell_wrap", fontSize=8, leading=11, fontName="Helvetica",
        ),
        "cell_bold": ParagraphStyle(
            "cell_bold", fontSize=8, leading=11, fontName="Helvetica-Bold",
        ),
        "recommendation": ParagraphStyle(
            "recommendation", fontSize=10, leading=15, textColor=C_NAVY,
            fontName="Helvetica", leftIndent=8, rightIndent=8,
        ),
        "confidential": ParagraphStyle(
            "confidential", fontSize=8, leading=11, textColor=colors.grey,
            alignment=TA_CENTER, fontName="Helvetica-Oblique",
        ),
    }


# ---------------------------------------------------------------------------
# Page decorators (footer with page number + watermark)
# ---------------------------------------------------------------------------

def _make_footer(generated_at: str, generated_by: str):
    def _draw_footer(canvas, doc):
        canvas.saveState()
        w, h = A4
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.grey)
        footer_y = MARGIN - 0.8 * cm
        canvas.drawString(MARGIN, footer_y,
            f"{INSTITUTION_NAME}  |  Generated: {generated_at}  |  By: {generated_by}"
        )
        canvas.drawRightString(w - MARGIN, footer_y, f"Page {doc.page}")
        canvas.setFont("Helvetica-Oblique", 7)
        canvas.drawCentredString(w / 2, footer_y, "CONFIDENTIAL — FOR INTERNAL USE ONLY")

        # Diagonal watermark
        canvas.setFont("Helvetica-Bold", 40)
        canvas.setFillColor(colors.Color(0, 0, 0, alpha=0.04))
        canvas.translate(w / 2, h / 2)
        canvas.rotate(35)
        canvas.drawCentredString(0, 0, "CONFIDENTIAL")
        canvas.restoreState()

    return _draw_footer


# ---------------------------------------------------------------------------
# Section header helper
# ---------------------------------------------------------------------------

def _section_header(title: str, s: Dict) -> List:
    """Returns a coloured section header band."""
    p = Paragraph(title, s["section_header"])
    tbl = Table([[p]], colWidths=[PAGE_W - 2 * MARGIN])
    tbl.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), C_NAVY),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
    ]))
    return [Spacer(1, 6 * mm), tbl, Spacer(1, 3 * mm)]


def _kv_table(rows: List[tuple], col_widths=None) -> Table:
    """Two-column label → value table for profile sections."""
    w = PAGE_W - 2 * MARGIN
    cw = col_widths or [w * 0.35, w * 0.65]
    s = _styles()
    data = [
        [Paragraph(str(label), s["body_bold"]), Paragraph(str(value), s["body"])]
        for label, value in rows
    ]
    tbl = Table(data, colWidths=cw)
    tbl.setStyle(TableStyle([
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 4),
        ("ROWBACKGROUNDS",(0, 0), (-1, -1), [C_GREY_LIGHT, C_WHITE]),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
    ]))
    return tbl


def _risk_color(risk_level: Optional[str]) -> colors.Color:
    mapping = {
        "very_high": C_RED,
        "high":      C_ORANGE,
        "medium":    C_AMBER,
        "low":       C_GREEN,
        "very_low":  C_GREEN,
    }
    return mapping.get(risk_level or "", colors.grey)


def _risk_bg(risk_level: Optional[str]) -> colors.Color:
    mapping = {
        "very_high": C_RED_SOFT,
        "high":      C_ORANGE_SOFT,
        "medium":    C_AMBER_SOFT,
        "low":       C_GREEN_SOFT,
        "very_low":  C_GREEN_SOFT,
    }
    return mapping.get(risk_level or "", C_GREY_LIGHT)


def _fmt_currency(v: Optional[float]) -> str:
    """Format as Ringgit. Helvetica has no glyph for most currency symbols,
    so the ISO code is spelled out rather than rendered as a tofu box."""
    if v is None:
        return "N/A"
    return f"RM {v:,.0f}"


def _fmt_val(v: Optional[float], is_pct: bool = False) -> str:
    if v is None:
        return "N/A"
    if is_pct:
        return f"{v:.2f}%"
    if abs(v) >= 1e6:
        return f"{v:,.0f}"
    return f"{v:.4f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def build_report(
    output_path: Path,
    app_data: Dict[str, Any],
    company_data: Dict[str, Any],
    documents: List[Dict[str, Any]],
    ocr_fields: Dict[str, Any],
    ratios: List[Dict[str, Any]],
    overall_health: Optional[str],
    rule_evaluation: Dict[str, Any],
    prediction: Dict[str, Any],
    generated_by: str,
) -> None:
    """
    Build and write the PDF report to output_path.

    All data is passed as plain dicts — no ORM objects here.
    """
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    footer_fn = _make_footer(generated_at, generated_by)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 0.5 * cm,
        title=f"Credit Assessment — {app_data.get('application_number', '')}",
        author=INSTITUTION_NAME,
    )

    s = _styles()
    story: List = []

    # ── Cover Page ────────────────────────────────────────────────────────────
    story += _cover_page(app_data, company_data, generated_at, s)
    story.append(PageBreak())

    # ── Section 1: Application Overview ──────────────────────────────────────
    story += _section_header("1.  Application Overview", s)
    story += _application_overview(app_data, s)
    story.append(Spacer(1, 4 * mm))

    # ── Section 2: Company Profile ────────────────────────────────────────────
    story += _section_header("2.  Company Profile", s)
    story += _company_profile(company_data, s)
    story.append(Spacer(1, 4 * mm))

    # ── Section 3: Submitted Documents ───────────────────────────────────────
    story += _section_header("3.  Submitted Documents", s)
    story += _documents_section(documents, s)
    story.append(Spacer(1, 4 * mm))

    # ── Section 4: OCR Extraction Summary ────────────────────────────────────
    story += _section_header("4.  Financial Data — OCR Extraction", s)
    story += _ocr_section(ocr_fields, s)
    story.append(PageBreak())

    # ── Section 5: Financial Ratios ───────────────────────────────────────────
    story += _section_header("5.  Financial Ratios Analysis", s)
    story += _ratios_section(ratios, overall_health, s)
    story.append(PageBreak())

    # ── Section 6: Rule Engine Evaluation ────────────────────────────────────
    story += _section_header("6.  Rule Engine Evaluation", s)
    story += _rule_engine_section(rule_evaluation, s)
    story.append(Spacer(1, 4 * mm))

    # ── Section 7: ML Prediction & Risk Assessment ────────────────────────────
    story += _section_header("7.  ML Prediction & Risk Assessment", s)
    story += _prediction_section(prediction, s)
    story.append(Spacer(1, 4 * mm))

    # ── Section 8: Recommendation ─────────────────────────────────────────────
    story += _section_header("8.  Credit Recommendation", s)
    story += _recommendation_section(prediction, rule_evaluation, s)
    story.append(Spacer(1, 4 * mm))

    # ── Section 9: Officer Notes ──────────────────────────────────────────────
    story += _section_header("9.  Officer Notes", s)
    story += _officer_notes_section(app_data.get("officer_notes"), generated_at, s)

    doc.build(story, onFirstPage=footer_fn, onLaterPages=footer_fn)


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------

def _cover_page(app_data, company_data, generated_at, s) -> List:
    elems = []
    elems.append(Spacer(1, 2 * cm))

    # Institution header
    elems.append(Paragraph(INSTITUTION_NAME, s["cover_title"]))
    elems.append(Spacer(1, 3 * mm))
    elems.append(Paragraph(INSTITUTION_SUB, s["cover_sub"]))
    elems.append(Spacer(1, 8 * mm))
    elems.append(HRFlowable(width="100%", thickness=2, color=C_NAVY))
    elems.append(Spacer(1, 6 * mm))

    # Report type
    elems.append(Paragraph("CREDIT ASSESSMENT REPORT", s["cover_title"]))
    elems.append(Spacer(1, 1 * cm))

    # Key fields
    status = app_data.get("status", "").replace("_", " ").title()
    decision = app_data.get("final_decision", "pending").replace("_", " ").upper()
    cover_rows = [
        ("Application Number", app_data.get("application_number", "—")),
        ("Company", company_data.get("name", "—")),
        ("Registration No.", company_data.get("registration_number", "—")),
        ("Loan Amount Requested", _fmt_currency(app_data.get("loan_amount_requested"))),
        ("Loan Purpose", str(app_data.get("loan_purpose", "—")).replace("_", " ").title()),
        ("Tenure", f"{app_data.get('loan_tenure_months', '—')} months"),
        ("Pipeline Status", status),
        ("Preliminary Decision", decision),
        ("Report Generated", generated_at),
    ]
    tbl = _kv_table(cover_rows, col_widths=[(PAGE_W - 2 * MARGIN) * 0.4,
                                             (PAGE_W - 2 * MARGIN) * 0.6])
    elems.append(tbl)
    elems.append(Spacer(1, 1 * cm))
    elems.append(HRFlowable(width="100%", thickness=1, color=C_GREY_RULE))
    elems.append(Spacer(1, 6 * mm))
    elems.append(Paragraph(
        "This report is CONFIDENTIAL and intended solely for the use of authorised "
        "personnel of the lending institution. It contains sensitive financial information "
        "about the applicant company and must not be disclosed to third parties without "
        "written authorisation.",
        s["confidential"],
    ))
    return elems


def _application_overview(app_data, s) -> List:
    rows = [
        ("Application No.", app_data.get("application_number", "—")),
        ("Loan Amount", _fmt_currency(app_data.get("loan_amount_requested"))),
        ("Loan Purpose", str(app_data.get("loan_purpose", "—")).replace("_", " ").title()),
        ("Tenure", f"{app_data.get('loan_tenure_months', '—')} months"),
        ("Interest Rate Requested", f"{app_data.get('interest_rate_requested', '—')}%"
            if app_data.get("interest_rate_requested") else "—"),
        ("Collateral Description", app_data.get("collateral_description") or "Not provided"),
        ("Collateral Value", _fmt_currency(app_data.get("collateral_value"))),
        ("Current Status", str(app_data.get("status", "—")).replace("_", " ").title()),
        ("Final Decision", str(app_data.get("final_decision", "Pending")).replace("_", " ").upper()),
        ("Assigned Officer", app_data.get("assigned_officer", "Not assigned")),
        ("Decision Reason", app_data.get("decision_reason") or "—"),
    ]
    return [_kv_table(rows)]


def _company_profile(company_data, s) -> List:
    rows = [
        ("Company Name", company_data.get("name", "—")),
        ("Registration Number", company_data.get("registration_number", "—")),
        ("Tax ID", company_data.get("tax_id") or "—"),
        ("GST Number", company_data.get("gst_number") or "—"),
        ("Company Type", str(company_data.get("company_type", "—")).replace("_", " ").title()),
        ("Industry", str(company_data.get("industry", "—")).replace("_", " ").title()),
        ("Incorporation Date", company_data.get("incorporation_date") or "—"),
        ("Country", company_data.get("country_of_incorporation", "—")),
        ("Registered Address", company_data.get("registered_address") or "—"),
        ("City / State", f"{company_data.get('city', '') or ''}, "
                         f"{company_data.get('state', '') or ''}".strip(", ") or "—"),
        ("Contact Email", company_data.get("contact_email") or "—"),
        ("Contact Phone", company_data.get("contact_phone") or "—"),
        ("Annual Turnover", _fmt_currency(company_data.get("annual_turnover"))),
        ("Employees", str(company_data.get("number_of_employees") or "—")),
    ]
    return [_kv_table(rows)]


def _documents_section(documents: List[Dict], s) -> List:
    if not documents:
        return [Paragraph("No documents have been submitted.", s["body"])]

    W = PAGE_W - 2 * MARGIN
    header = ["#", "Type", "Filename", "Financial Year", "Size (KB)", "Status"]
    col_widths = [W * 0.04, W * 0.16, W * 0.38, W * 0.12, W * 0.12, W * 0.18]
    data = [header]
    for i, doc in enumerate(documents, 1):
        size_kb = f"{doc.get('file_size_bytes', 0) / 1024:.1f}"
        doc_type = str(doc.get("document_type", "—")).replace("_", " ").title()
        status = str(doc.get("status", "—")).title()
        data.append([
            str(i),
            doc_type,
            doc.get("original_filename", "—")[:50],
            doc.get("financial_year") or "—",
            size_kb,
            status,
        ])

    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]))
    return [tbl]


def _ocr_section(ocr_fields: Dict[str, Any], s) -> List:
    field_display = {
        "revenue": "Revenue / Turnover",
        "cost_of_revenue": "Cost of Revenue",
        "gross_profit": "Gross Profit",
        "operating_profit": "Operating Profit",
        "ebit": "EBIT",
        "ebitda": "EBITDA",
        "net_profit": "Net Profit / PAT",
        "cash": "Cash & Cash Equivalents",
        "inventory": "Inventory",
        "accounts_receivable": "Accounts Receivable",
        "accounts_payable": "Accounts Payable",
        "current_assets": "Current Assets",
        "current_liabilities": "Current Liabilities",
        "total_assets": "Total Assets",
        "total_liabilities": "Total Liabilities",
        "equity": "Shareholders' Equity",
        "long_term_debt": "Long-term Debt",
        "short_term_debt": "Short-term Debt",
        "interest_expense": "Interest Expense",
        "operating_cash_flow": "Operating Cash Flow",
        "investing_cash_flow": "Investing Cash Flow",
        "financing_cash_flow": "Financing Cash Flow",
        "depreciation_amortisation": "Depreciation & Amortisation",
        "tax_expense": "Tax Expense",
        "net_worth": "Net Worth",
    }

    if not ocr_fields:
        return [Paragraph("No OCR data available.", s["body"])]

    W = PAGE_W - 2 * MARGIN
    n = len(ocr_fields)
    half = math.ceil(n / 2)
    items = list(ocr_fields.items())

    header_row = ["Financial Metric", "Extracted Value", "Financial Metric", "Extracted Value"]
    data = [header_row]
    for i in range(half):
        left_k, left_v = items[i]
        if i + half < n:
            right_k, right_v = items[i + half]
        else:
            right_k, right_v = "", None
        data.append([
            field_display.get(left_k, left_k.replace("_", " ").title()),
            _fmt_currency(left_v) if isinstance(left_v, (int, float)) else str(left_v or "—"),
            field_display.get(right_k, right_k.replace("_", " ").title()) if right_k else "",
            _fmt_currency(right_v) if isinstance(right_v, (int, float)) else str(right_v or "—") if right_k else "",
        ])

    col_widths = [W * 0.28, W * 0.22, W * 0.28, W * 0.22]
    tbl = Table(data, colWidths=col_widths)
    tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), C_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ("FONTNAME",      (0, 1), (0, -1), "Helvetica-Bold"),
        ("FONTNAME",      (2, 1), (2, -1), "Helvetica-Bold"),
    ]))
    return [tbl]


def _ratios_section(ratios: List[Dict], overall_health: Optional[str], s) -> List:
    elems = []

    # Overall health badge
    health_color = _risk_color(overall_health)
    health_bg = _risk_bg(overall_health)
    health_label = (overall_health or "unknown").replace("_", " ").upper()
    health_p = Paragraph(f"Overall Financial Health: <b>{health_label}</b>", s["body_bold"])
    health_tbl = Table([[health_p]], colWidths=[PAGE_W - 2 * MARGIN])
    health_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), health_bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 8),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ROUNDEDCORNERS",(0, 0), (-1, -1), [4, 4, 4, 4]),
    ]))
    elems.append(health_tbl)
    elems.append(Spacer(1, 4 * mm))

    if not ratios:
        elems.append(Paragraph("No ratio data available.", s["body"]))
        return elems

    W = PAGE_W - 2 * MARGIN
    header = ["Ratio", "Value", "Unit", "Risk Level", "Benchmark", "Interpretation"]
    col_widths = [W * 0.22, W * 0.08, W * 0.06, W * 0.12, W * 0.14, W * 0.38]

    data = [header]
    risk_row_styles = []

    for i, r in enumerate(ratios, 1):
        rl = r.get("risk_level", "unknown")
        val_raw = r.get("value")
        is_pct = r.get("unit", "") == "%"
        val_str = _fmt_val(val_raw, is_pct=is_pct)
        bmin = r.get("benchmark_min")
        bmax = r.get("benchmark_max")
        bench = f"{_fmt_val(bmin)} – {_fmt_val(bmax)}" if bmin is not None and bmax is not None else "—"

        interp = r.get("interpretation", "")
        if len(interp) > 90:
            interp = interp[:87] + "..."

        data.append([
            Paragraph(r.get("display_name", r.get("name", "—")), s["cell_bold"]),
            Paragraph(val_str, s["cell_wrap"]),
            Paragraph(r.get("unit", ""), s["cell_wrap"]),
            Paragraph(rl.replace("_", " ").title(), s["cell_wrap"]),
            Paragraph(bench, s["cell_wrap"]),
            Paragraph(interp, s["cell_wrap"]),
        ])
        # Color risk-level cell
        risk_row_styles.append(
            ("BACKGROUND", (3, i), (3, i), _risk_bg(rl))
        )
        risk_row_styles.append(
            ("TEXTCOLOR", (3, i), (3, i), _risk_color(rl))
        )
        risk_row_styles.append(
            ("FONTNAME", (3, i), (3, i), "Helvetica-Bold")
        )

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    base_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_BLUE),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]
    tbl.setStyle(TableStyle(base_style + risk_row_styles))
    elems.append(tbl)
    return elems


def _rule_engine_section(rule_eval: Dict[str, Any], s) -> List:
    elems = []

    outcome = rule_eval.get("overall_outcome", "unknown")
    triggered = rule_eval.get("triggered_count", 0)
    total = rule_eval.get("total_rules", 0)
    ml_runs = rule_eval.get("ml_should_run", True)

    outcome_color = {"pass": C_GREEN, "manual_review": C_AMBER, "reject": C_RED}.get(outcome, colors.grey)
    outcome_bg = {"pass": C_GREEN_SOFT, "manual_review": C_AMBER_SOFT, "reject": C_RED_SOFT}.get(outcome, C_GREY_LIGHT)
    outcome_label = outcome.replace("_", " ").upper()

    summary_data = [
        [
            Paragraph(f"Verdict: <b>{outcome_label}</b>", s["body_bold"]),
            Paragraph(f"Rules Evaluated: <b>{total}</b>", s["body"]),
            Paragraph(f"Rules Triggered: <b>{triggered}</b>", s["body"]),
            Paragraph(f"ML Pipeline: <b>{'Will Run' if ml_runs else 'SKIPPED'}</b>", s["body"]),
        ]
    ]
    W = PAGE_W - 2 * MARGIN
    stbl = Table(summary_data, colWidths=[W * 0.28, W * 0.22, W * 0.22, W * 0.28])
    stbl.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (0, 0), outcome_bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 6),
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
        ("TEXTCOLOR",     (0, 0), (0, 0), outcome_color),
    ]))
    elems.append(stbl)
    elems.append(Spacer(1, 3 * mm))

    results = rule_eval.get("results", [])
    if not results:
        elems.append(Paragraph("No rule results available.", s["body"]))
        return elems

    header = ["Priority", "Rule Name", "Category", "Metric Value", "Threshold", "Mandatory", "Status", "Action"]
    col_widths = [W * 0.07, W * 0.22, W * 0.10, W * 0.10, W * 0.10, W * 0.09, W * 0.10, W * 0.10]  # Removed message column for space

    data = [header]
    row_color_styles = []

    for i, r in enumerate(results, 1):
        triggered_flag = r.get("triggered", False)
        is_mandatory = r.get("is_mandatory", False)

        if triggered_flag:
            status_label = "FAIL"
            status_fg = C_RED if is_mandatory else C_AMBER
            status_bg = C_RED_SOFT if is_mandatory else C_AMBER_SOFT
        else:
            status_label = "PASS"
            status_fg = C_GREEN
            status_bg = C_GREEN_SOFT

        val = r.get("metric_value")
        thresh = r.get("threshold")

        data.append([
            str(r.get("priority", "—")),
            Paragraph(r.get("rule_name", "—"), s["cell_bold"]),
            r.get("category", "—").title(),
            _fmt_val(val) if val is not None else "N/A",
            _fmt_val(thresh) if thresh is not None else "—",
            "Yes" if is_mandatory else "No",
            Paragraph(f"<b>{status_label}</b>", s["cell_bold"]),
            r.get("action", "—").replace("_", " ").title(),
        ])
        row_color_styles.extend([
            ("BACKGROUND", (6, i), (6, i), status_bg),
            ("TEXTCOLOR",  (6, i), (6, i), status_fg),
        ])

    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    base_style = [
        ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
        ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GREY_LIGHT]),
        ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING",   (0, 0), (-1, -1), 4),
    ]
    tbl.setStyle(TableStyle(base_style + row_color_styles))
    elems.append(tbl)

    # Failure messages for triggered rules
    triggered_results = [r for r in results if r.get("triggered")]
    if triggered_results:
        elems.append(Spacer(1, 3 * mm))
        elems.append(Paragraph("<b>Triggered Rule Details:</b>", s["body_bold"]))
        elems.append(Spacer(1, 2 * mm))
        for r in triggered_results:
            msg = r.get("message", "")
            prefix = "⚠ " if not r.get("is_mandatory") else "✖ "
            elems.append(Paragraph(f"{prefix}<b>{r.get('rule_name', '')}:</b> {msg}", s["body"]))
            elems.append(Spacer(1, 1 * mm))

    return elems


def _prediction_section(prediction: Dict[str, Any], s) -> List:
    if not prediction:
        return [Paragraph("No ML prediction data available.", s["body"])]

    elems = []
    ml_executed = prediction.get("ml_executed", False)

    if not ml_executed:
        reason = prediction.get("skip_reason", "ML pipeline was not executed.")
        p = Paragraph(f"<b>ML PIPELINE SKIPPED</b><br/>{reason}", s["body"])
        box = Table([[p]], colWidths=[PAGE_W - 2 * MARGIN])
        box.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), C_RED_SOFT),
            ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        elems.append(box)
        return elems

    risk_score = prediction.get("risk_score", 0)
    risk_level = prediction.get("risk_level", "unknown")
    prob = prediction.get("probability_of_default", 0)
    outcome = prediction.get("outcome", "—")
    model_used = str(prediction.get("model_used", "—")).replace("_", " ").title()

    rl_color = _risk_color(risk_level)
    rl_bg = _risk_bg(risk_level)

    W = PAGE_W - 2 * MARGIN
    summary_rows = [
        ("Model Used", model_used),
        ("Probability of Default", f"{prob * 100:.2f}%"),
        ("Composite Risk Score", f"{risk_score:.1f} / 100"),
        ("Risk Level", risk_level.replace("_", " ").upper()),
        ("Prediction Outcome", str(outcome).replace("_", " ").replace("_", " ").title()),
    ]
    pred_tbl = _kv_table(summary_rows)
    elems.append(pred_tbl)
    elems.append(Spacer(1, 3 * mm))

    # Risk score bar (text-based)
    filled = int(risk_score / 5)  # 20 chars = 100%
    bar_str = "█" * filled + "░" * (20 - filled)
    elems.append(Paragraph(
        f"<b>Risk Score Bar:</b>  [{bar_str}]  {risk_score:.1f}%",
        s["body"],
    ))
    elems.append(Spacer(1, 3 * mm))

    # SHAP top contributors
    shap_values = prediction.get("shap_values") or {}
    if shap_values:
        elems.append(Paragraph("<b>Top Predictive Factors (SHAP Analysis):</b>", s["body_bold"]))
        elems.append(Spacer(1, 2 * mm))
        header = ["Feature", "SHAP Value", "Direction"]
        shap_sorted = sorted(shap_values.items(), key=lambda kv: abs(kv[1]), reverse=True)[:12]
        shap_data = [header]
        row_styles_shap = []
        for j, (feat, val) in enumerate(shap_sorted, 1):
            direction = "↑ Increases Risk" if val > 0 else "↓ Reduces Risk"
            dir_color = C_RED if val > 0 else C_GREEN
            short_feat = feat if len(feat) <= 45 else feat[:42] + "..."
            shap_data.append([short_feat, f"{val:+.4f}", direction])
            row_styles_shap.extend([
                ("TEXTCOLOR", (2, j), (2, j), dir_color),
                ("FONTNAME",  (2, j), (2, j), "Helvetica-Bold"),
            ])

        shap_col_widths = [W * 0.62, W * 0.18, W * 0.20]
        shap_tbl = Table(shap_data, colWidths=shap_col_widths)
        shap_base = [
            ("BACKGROUND",    (0, 0), (-1, 0), C_BLUE),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GREY_LIGHT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ]
        shap_tbl.setStyle(TableStyle(shap_base + row_styles_shap))
        elems.append(shap_tbl)
        elems.append(Spacer(1, 2 * mm))

    # ML explanation
    explanation = prediction.get("explanation_text", "")
    if explanation:
        elems.append(Paragraph("<b>Model Explanation:</b>", s["body_bold"]))
        elems.append(Paragraph(explanation, s["body"]))

    # Model comparison metrics
    model_metrics = prediction.get("model_metrics") or {}
    if model_metrics:
        elems.append(Spacer(1, 3 * mm))
        elems.append(Paragraph("<b>Model Comparison (Training Evaluation):</b>", s["body_bold"]))
        elems.append(Spacer(1, 2 * mm))
        metric_header = ["Model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "CV ROC-AUC"]
        metric_data = [metric_header]
        for mname, mvals in model_metrics.items():
            metric_data.append([
                mname.replace("_", " ").title(),
                f"{mvals.get('accuracy', 0):.3f}",
                f"{mvals.get('precision', 0):.3f}",
                f"{mvals.get('recall', 0):.3f}",
                f"{mvals.get('f1', 0):.3f}",
                f"{mvals.get('roc_auc', 0):.3f}",
                f"{mvals.get('cv_roc_auc_mean', 0):.3f} ± {mvals.get('cv_roc_auc_std', 0):.3f}",
            ])
        mc_col = [W * 0.22] + [W * 0.10] * 5 + [W * 0.18]
        mc_tbl = Table(metric_data, colWidths=mc_col)
        mc_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0, 0), (-1, 0), C_NAVY),
            ("TEXTCOLOR",     (0, 0), (-1, 0), C_WHITE),
            ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE",      (0, 0), (-1, -1), 8),
            ("ROWBACKGROUNDS",(0, 1), (-1, -1), [C_WHITE, C_GREY_LIGHT]),
            ("GRID",          (0, 0), (-1, -1), 0.25, C_GREY_RULE),
            ("TOPPADDING",    (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("LEFTPADDING",   (0, 0), (-1, -1), 4),
        ]))
        elems.append(mc_tbl)

    return elems


def _recommendation_section(prediction: Dict, rule_eval: Dict, s) -> List:
    recommendation = prediction.get("recommendation") or rule_eval.get("rejection_reason") or (
        "No recommendation available — ensure all pipeline stages have been completed."
    )
    outcome = rule_eval.get("overall_outcome", "pass")
    bg = {"reject": C_RED_SOFT, "manual_review": C_AMBER_SOFT, "pass": C_GREEN_SOFT}.get(outcome, C_LIGHT_BG)

    p = Paragraph(recommendation, s["recommendation"])
    box = Table([[p]], colWidths=[PAGE_W - 2 * MARGIN])
    box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), bg),
        ("LEFTPADDING",   (0, 0), (-1, -1), 10),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 10),
        ("TOPPADDING",    (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("GRID",          (0, 0), (-1, -1), 0.5, C_GREY_RULE),
    ]))
    return [box]


def _officer_notes_section(officer_notes: Optional[str], generated_at: str, s) -> List:
    elems = []
    if officer_notes:
        elems.append(Paragraph(officer_notes, s["body"]))
    else:
        elems.append(Paragraph("No officer notes recorded at the time of report generation.", s["small"]))
    elems.append(Spacer(1, 6 * mm))
    elems.append(HRFlowable(width="100%", thickness=0.5, color=C_GREY_RULE))
    elems.append(Spacer(1, 2 * mm))
    elems.append(Paragraph(
        f"Report generated by {INSTITUTION_NAME} on {generated_at}. "
        "This is a system-generated document and does not require a physical signature.",
        s["confidential"],
    ))
    return elems
