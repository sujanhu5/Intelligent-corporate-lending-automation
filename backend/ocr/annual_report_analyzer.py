"""
Annual Report Analyzer — detects and extracts financial statement sections
from a complete company annual report PDF (typically 300-500+ pages).

Pipeline:
  1. Open PDF with PyMuPDF, extract text per page
  2. Detect Table of Contents (TOC) pages
  3. Parse TOC entries to map section names → page numbers
  4. If TOC parsing fails, scan all pages for section headers
  5. Identify financial statement boundaries:
     - Balance Sheet / Statement of Financial Position
     - Statement of Profit and Loss / Income Statement
     - Cash Flow Statement
  6. Distinguish Consolidated vs Standalone; prefer Standalone for
     single-entity corporate lending assessment
  7. Extract text from detected page ranges only
  8. Return structured result with per-section text, page ranges,
     confidence scores, and unit context (crore/lakh/million)

The caller (OCRService) feeds each section's text into the existing
parse_financials() pipeline — no changes needed downstream.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from app.core.logging import get_logger

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class SectionType(str, Enum):
    BALANCE_SHEET = "balance_sheet"
    PROFIT_LOSS = "profit_loss"
    CASH_FLOW = "cash_flow"


class StatementVariant(str, Enum):
    STANDALONE = "standalone"
    CONSOLIDATED = "consolidated"
    UNKNOWN = "unknown"


@dataclass
class DetectedSection:
    section_type: SectionType
    variant: StatementVariant
    start_page: int          # 1-indexed
    end_page: int            # 1-indexed, inclusive
    title_found: str         # exact heading text matched
    text: str                # extracted text from pages
    page_count: int = 0
    confidence: float = 0.0  # 0.0–1.0

    def __post_init__(self):
        self.page_count = self.end_page - self.start_page + 1


@dataclass
class UnitContext:
    """Detected monetary unit used in the financial statements."""
    unit: str = "unknown"       # "crore", "lakh", "million", "billion", "thousand", "units"
    multiplier: float = 1.0
    currency: str = "INR"
    source_text: str = ""


@dataclass
class AnalysisResult:
    total_pages: int
    toc_found: bool = False
    toc_pages: List[int] = field(default_factory=list)
    sections: List[DetectedSection] = field(default_factory=list)
    unit_context: Optional[UnitContext] = None
    financial_year: Optional[str] = None
    company_name: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    analysis_method: str = "unknown"  # "toc_based" | "keyword_scan"

    @property
    def section_types_found(self) -> List[str]:
        return [s.section_type.value for s in self.sections]

    @property
    def has_all_statements(self) -> bool:
        found = set(self.section_types_found)
        return found >= {"balance_sheet", "profit_loss", "cash_flow"}

    @property
    def overall_confidence(self) -> float:
        if not self.sections:
            return 0.0
        return round(sum(s.confidence for s in self.sections) / len(self.sections), 3)


# ---------------------------------------------------------------------------
# Section detection patterns
# ---------------------------------------------------------------------------

_BALANCE_SHEET_PATTERNS = [
    re.compile(r"(?:standalone\s+)?balance\s+sheet", re.IGNORECASE),
    re.compile(r"statement\s+of\s+financial\s+position", re.IGNORECASE),
    re.compile(r"(?:standalone\s+)?consolidated\s+balance\s+sheet", re.IGNORECASE),
    re.compile(r"statement\s+of\s+assets\s+and\s+liabilities", re.IGNORECASE),
    re.compile(r"balance\s+sheet\s+as\s+(?:at|on)", re.IGNORECASE),
]

_PROFIT_LOSS_PATTERNS = [
    re.compile(r"statement\s+of\s+profit\s+and\s+loss", re.IGNORECASE),
    re.compile(r"profit\s+and\s+loss\s+(?:account|statement)", re.IGNORECASE),
    re.compile(r"(?:consolidated\s+)?income\s+statement", re.IGNORECASE),
    re.compile(r"statement\s+of\s+(?:comprehensive\s+)?income", re.IGNORECASE),
    re.compile(r"profit\s*&\s*loss", re.IGNORECASE),
    re.compile(r"statement\s+of\s+(?:total\s+)?comprehensive\s+(?:income|loss)", re.IGNORECASE),
    re.compile(r"statement\s+of\s+operations", re.IGNORECASE),
]

_CASH_FLOW_PATTERNS = [
    re.compile(r"(?:statement\s+of\s+)?cash\s+flow(?:s)?(?:\s+statement)?", re.IGNORECASE),
    re.compile(r"cash\s+flow\s+from\s+operat", re.IGNORECASE),
    re.compile(r"(?:statement\s+of\s+)?cash\s+and\s+cash\s+equivalents", re.IGNORECASE),
]

_SECTION_PATTERNS: Dict[SectionType, List[re.Pattern]] = {
    SectionType.BALANCE_SHEET: _BALANCE_SHEET_PATTERNS,
    SectionType.PROFIT_LOSS: _PROFIT_LOSS_PATTERNS,
    SectionType.CASH_FLOW: _CASH_FLOW_PATTERNS,
}

_VARIANT_PATTERNS = {
    StatementVariant.STANDALONE: re.compile(r"\bstandalone\b", re.IGNORECASE),
    StatementVariant.CONSOLIDATED: re.compile(r"\bconsolidated\b", re.IGNORECASE),
}

# Patterns that mark the END of a financial statement section
_SECTION_END_MARKERS = [
    re.compile(r"notes\s+(?:to|on|forming\s+part\s+of)\s+(?:the\s+)?(?:standalone\s+|consolidated\s+)?financial\s+statements", re.IGNORECASE),
    re.compile(r"significant\s+accounting\s+policies", re.IGNORECASE),
    re.compile(r"schedules?\s+(?:to|forming\s+part)", re.IGNORECASE),
    re.compile(r"annexure", re.IGNORECASE),
    re.compile(r"auditor.{0,5}s?\s+report", re.IGNORECASE),
    re.compile(r"director.{0,5}s?\s+report", re.IGNORECASE),
    re.compile(r"management\s+discussion", re.IGNORECASE),
    re.compile(r"corporate\s+governance", re.IGNORECASE),
]

# TOC detection
_TOC_PATTERNS = [
    re.compile(r"table\s+of\s+contents", re.IGNORECASE),
    re.compile(r"\bcontents?\b\s*$", re.IGNORECASE | re.MULTILINE),
    re.compile(r"\bindex\b\s*$", re.IGNORECASE | re.MULTILINE),
]

# TOC entry: "Balance Sheet ... 45" or "Balance Sheet 45"
_TOC_ENTRY = re.compile(
    r"(.{10,80}?)\s*[.…·\-–—\s]{2,}\s*(\d{1,4})\s*$",
    re.MULTILINE,
)

# Unit detection
_UNIT_PATTERNS = [
    (re.compile(r"(?:₹|rs\.?|inr)\s*(?:in\s+)?(?:lakhs?|lacs?)\b", re.IGNORECASE), "lakh", 1e5, "INR"),
    (re.compile(r"(?:₹|rs\.?|inr)\s*(?:in\s+)?crores?\b", re.IGNORECASE), "crore", 1e7, "INR"),
    (re.compile(r"(?:in\s+)?(?:lakhs?|lacs?)\s+of\s+rupees", re.IGNORECASE), "lakh", 1e5, "INR"),
    (re.compile(r"(?:in\s+)?crores?\s+of\s+rupees", re.IGNORECASE), "crore", 1e7, "INR"),
    (re.compile(r"\((?:₹|rs\.?)\s*(?:in\s+)?crores?\)", re.IGNORECASE), "crore", 1e7, "INR"),
    (re.compile(r"\((?:₹|rs\.?)\s*(?:in\s+)?(?:lakhs?|lacs?)\)", re.IGNORECASE), "lakh", 1e5, "INR"),
    (re.compile(r"\(?\s*in\s+crores?\s*\)?", re.IGNORECASE), "crore", 1e7, "INR"),
    (re.compile(r"\(?\s*in\s+(?:lakhs?|lacs?)\s*\)?", re.IGNORECASE), "lakh", 1e5, "INR"),
    (re.compile(r"(?:\$|usd)\s*(?:in\s+)?millions?\b", re.IGNORECASE), "million", 1e6, "USD"),
    (re.compile(r"(?:\$|usd)\s*(?:in\s+)?billions?\b", re.IGNORECASE), "billion", 1e9, "USD"),
    (re.compile(r"(?:in\s+)?millions?\s+of\s+(?:dollars|usd)", re.IGNORECASE), "million", 1e6, "USD"),
    (re.compile(r"(?:in\s+)?thousands?\b", re.IGNORECASE), "thousand", 1e3, "unknown"),
]

# Financial year detection
_FY_PATTERNS = [
    re.compile(r"(?:for\s+the\s+)?(?:year|period)\s+ended?\s+(?:\w+\s+)?\d{1,2}(?:st|nd|rd|th)?\s+\w+\s*,?\s*(\d{4})", re.IGNORECASE),
    re.compile(r"(?:FY|F\.Y\.?)\s*(\d{4})\s*[-–]\s*(\d{2,4})", re.IGNORECASE),
    re.compile(r"(\d{4})\s*[-–]\s*(\d{2,4})", re.IGNORECASE),
    re.compile(r"(?:march|april|september|december)\s+\d{1,2},?\s+(\d{4})", re.IGNORECASE),
]

# Max pages to extract per financial statement section
_MAX_SECTION_PAGES = 12

# Pages to scan for TOC (from the beginning)
_TOC_SCAN_RANGE = 40


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def analyze_annual_report(file_path: str | Path) -> AnalysisResult:
    """
    Analyze a complete annual report PDF to detect and extract
    financial statement sections.

    Returns an AnalysisResult with detected sections, their page ranges,
    extracted text, and confidence scores.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Annual report file not found: {file_path}")

    try:
        import fitz  # PyMuPDF
    except ImportError:
        raise ImportError("PyMuPDF (fitz) is required for annual report analysis.")

    doc = fitz.open(str(path))
    total_pages = len(doc)

    logger.info(
        "Annual report analysis started",
        extra={"file": path.name, "pages": total_pages},
    )

    # Extract text from every page (we need it for scanning)
    page_texts: List[str] = []
    for page in doc:
        page_texts.append(page.get_text("text"))

    doc.close()

    result = AnalysisResult(total_pages=total_pages)

    # Detect company name from first few pages
    result.company_name = _detect_company_name(page_texts[:5])

    # Detect financial year
    result.financial_year = _detect_financial_year(page_texts[:10])

    # Strategy 1: Try TOC-based detection
    toc_sections = _detect_via_toc(page_texts, result)

    if toc_sections:
        result.analysis_method = "toc_based"
        _extract_sections(page_texts, toc_sections, result)
    else:
        # Strategy 2: Keyword scan across all pages
        result.analysis_method = "keyword_scan"
        keyword_sections = _detect_via_keywords(page_texts)
        _extract_sections(page_texts, keyword_sections, result)

    # Detect unit context from the extracted section text
    if result.sections:
        combined_text = " ".join(s.text[:2000] for s in result.sections)
        result.unit_context = _detect_unit(combined_text)

    # Quality checks
    if not result.sections:
        result.warnings.append(
            "No financial statement sections detected. "
            "The PDF may not contain standard financial statements, "
            "or the format is not recognized."
        )
    elif not result.has_all_statements:
        missing = {"balance_sheet", "profit_loss", "cash_flow"} - set(result.section_types_found)
        result.warnings.append(
            f"Missing financial statements: {', '.join(m.replace('_', ' ').title() for m in missing)}. "
            "The system will proceed with available data but some ratios may be incomplete."
        )

    logger.info(
        "Annual report analysis complete",
        extra={
            "file": path.name,
            "sections_found": len(result.sections),
            "types": result.section_types_found,
            "method": result.analysis_method,
            "confidence": result.overall_confidence,
        },
    )

    return result


# ---------------------------------------------------------------------------
# TOC-based detection
# ---------------------------------------------------------------------------

def _detect_via_toc(
    page_texts: List[str],
    result: AnalysisResult,
) -> List[Tuple[SectionType, StatementVariant, int, str]]:
    """
    Look for a Table of Contents and parse it for financial statement entries.
    Returns list of (section_type, variant, page_number, title_text).
    """
    toc_page_indices: List[int] = []

    scan_end = min(len(page_texts), _TOC_SCAN_RANGE)
    for i in range(scan_end):
        text = page_texts[i]
        for pat in _TOC_PATTERNS:
            if pat.search(text):
                toc_page_indices.append(i)
                break

    if not toc_page_indices:
        return []

    result.toc_found = True
    result.toc_pages = [i + 1 for i in toc_page_indices]

    # Parse TOC entries from all detected TOC pages
    toc_text = "\n".join(page_texts[i] for i in toc_page_indices)
    entries = _TOC_ENTRY.findall(toc_text)

    sections: List[Tuple[SectionType, StatementVariant, int, str]] = []

    for entry_title, page_str in entries:
        title_clean = entry_title.strip()
        page_num = int(page_str)

        if page_num < 1 or page_num > len(page_texts):
            continue

        for section_type, patterns in _SECTION_PATTERNS.items():
            for pat in patterns:
                if pat.search(title_clean):
                    variant = _detect_variant(title_clean)
                    sections.append((section_type, variant, page_num, title_clean))
                    break

    # Deduplicate: prefer standalone over consolidated for same section type
    sections = _deduplicate_sections(sections)

    logger.info(
        "TOC-based detection",
        extra={
            "toc_pages": result.toc_pages,
            "toc_entries": len(entries),
            "sections_matched": len(sections),
        },
    )

    return sections


# ---------------------------------------------------------------------------
# Keyword-scan detection
# ---------------------------------------------------------------------------

def _detect_via_keywords(
    page_texts: List[str],
) -> List[Tuple[SectionType, StatementVariant, int, str]]:
    """
    Scan all pages for financial statement section headers.
    Returns list of (section_type, variant, page_number, matched_title).
    """
    sections: List[Tuple[SectionType, StatementVariant, int, str]] = []

    for i, text in enumerate(page_texts):
        page_num = i + 1

        # Check the first 1500 chars — financial headers may appear after
        # company name, statutory info, and other preamble on the page
        header_region = text[:1500]

        for section_type, patterns in _SECTION_PATTERNS.items():
            for pat in patterns:
                m = pat.search(header_region)
                if m:
                    matched_text = m.group(0).strip()
                    variant = _detect_variant(header_region)
                    sections.append((section_type, variant, page_num, matched_text))
                    break

    sections = _deduplicate_sections(sections)

    logger.info(
        "Keyword-scan detection",
        extra={"pages_scanned": len(page_texts), "sections_matched": len(sections)},
    )

    return sections


# ---------------------------------------------------------------------------
# Section extraction
# ---------------------------------------------------------------------------

def _extract_sections(
    page_texts: List[str],
    raw_sections: List[Tuple[SectionType, StatementVariant, int, str]],
    result: AnalysisResult,
) -> None:
    """
    For each detected section, determine the page range and extract text.
    Populates result.sections.
    """
    total_pages = len(page_texts)

    # Sort sections by start page
    sorted_sections = sorted(raw_sections, key=lambda s: s[2])

    for idx, (section_type, variant, start_page, title) in enumerate(sorted_sections):
        # Determine end page:
        # 1. Next section's start page - 1
        # 2. Or first "end marker" found after start
        # 3. Or start + MAX_SECTION_PAGES
        if idx + 1 < len(sorted_sections):
            next_start = sorted_sections[idx + 1][2]
            max_end = min(start_page + _MAX_SECTION_PAGES - 1, next_start - 1)
        else:
            max_end = min(start_page + _MAX_SECTION_PAGES - 1, total_pages)

        # Scan for end markers within the range
        end_page = max_end
        for p in range(start_page, min(max_end + 1, total_pages)):
            page_idx = p - 1
            if p == start_page:
                continue
            page_text = page_texts[page_idx][:500]
            if _is_section_end(page_text, section_type):
                end_page = p - 1
                break

        end_page = max(end_page, start_page)

        # Extract text from the page range
        section_text = "\n".join(
            page_texts[p - 1] for p in range(start_page, end_page + 1)
        )

        # Compute confidence based on heuristics
        confidence = _compute_section_confidence(
            section_type, section_text, title, start_page, end_page
        )

        result.sections.append(DetectedSection(
            section_type=section_type,
            variant=variant,
            start_page=start_page,
            end_page=end_page,
            title_found=title,
            text=section_text,
            confidence=confidence,
        ))


def _is_section_end(header_text: str, current_section: SectionType) -> bool:
    """Check if a page header signals the end of the current section."""
    for pat in _SECTION_END_MARKERS:
        if pat.search(header_text):
            return True

    # A new financial statement section also ends the current one
    for section_type, patterns in _SECTION_PATTERNS.items():
        if section_type == current_section:
            continue
        for pat in patterns:
            if pat.search(header_text):
                return True

    return False


def _compute_section_confidence(
    section_type: SectionType,
    text: str,
    title: str,
    start_page: int,
    end_page: int,
) -> float:
    """
    Heuristic confidence score for a detected section.
    Higher when we find expected keywords in the extracted text.
    """
    confidence = 0.5  # base for having found a title match

    # Reward: title is specific (not just "Balance Sheet" but includes year/context)
    if len(title) > 20:
        confidence += 0.1

    # Reward: multiple pages (financial statements are rarely single-page)
    page_count = end_page - start_page + 1
    if page_count >= 2:
        confidence += 0.1

    text_lower = text.lower()

    # Check for expected content keywords
    if section_type == SectionType.BALANCE_SHEET:
        markers = ["total assets", "total liabilities", "equity", "current assets",
                    "non-current", "shareholders", "reserves"]
    elif section_type == SectionType.PROFIT_LOSS:
        markers = ["revenue", "profit", "tax", "expenses", "depreciation",
                    "earnings", "income", "loss"]
    else:  # CASH_FLOW
        markers = ["operating activities", "investing activities",
                    "financing activities", "cash and cash equivalents",
                    "net increase", "net decrease"]

    found = sum(1 for m in markers if m in text_lower)
    marker_score = min(found / max(len(markers) * 0.5, 1), 1.0) * 0.3
    confidence += marker_score

    return round(min(confidence, 1.0), 3)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _detect_variant(text: str) -> StatementVariant:
    """Detect if a section title refers to standalone or consolidated."""
    if _VARIANT_PATTERNS[StatementVariant.STANDALONE].search(text):
        return StatementVariant.STANDALONE
    if _VARIANT_PATTERNS[StatementVariant.CONSOLIDATED].search(text):
        return StatementVariant.CONSOLIDATED
    return StatementVariant.UNKNOWN


def _deduplicate_sections(
    sections: List[Tuple[SectionType, StatementVariant, int, str]],
) -> List[Tuple[SectionType, StatementVariant, int, str]]:
    """
    When both standalone and consolidated versions exist for the same
    section type, prefer standalone for corporate lending assessment.
    When only unknown-variant duplicates exist, keep the first occurrence.
    """
    by_type: Dict[SectionType, List[Tuple[SectionType, StatementVariant, int, str]]] = {}
    for s in sections:
        by_type.setdefault(s[0], []).append(s)

    result = []
    for section_type, candidates in by_type.items():
        standalone = [c for c in candidates if c[1] == StatementVariant.STANDALONE]
        consolidated = [c for c in candidates if c[1] == StatementVariant.CONSOLIDATED]
        unknown = [c for c in candidates if c[1] == StatementVariant.UNKNOWN]

        if standalone:
            result.append(standalone[0])
        elif unknown:
            result.append(unknown[0])
        elif consolidated:
            result.append(consolidated[0])

    return result


def _detect_unit(text: str) -> Optional[UnitContext]:
    """Detect the monetary unit used in the financial statements."""
    for pattern, unit, multiplier, currency in _UNIT_PATTERNS:
        m = pattern.search(text)
        if m:
            return UnitContext(
                unit=unit,
                multiplier=multiplier,
                currency=currency,
                source_text=m.group(0).strip(),
            )
    return None


def _detect_financial_year(page_texts: List[str]) -> Optional[str]:
    """Try to detect the financial year from early pages."""
    combined = " ".join(page_texts)
    for pat in _FY_PATTERNS:
        m = pat.search(combined)
        if m:
            groups = m.groups()
            if len(groups) == 2:
                return f"FY{groups[0]}-{groups[1]}"
            return f"FY{groups[0]}"
    return None


def _detect_company_name(page_texts: List[str]) -> Optional[str]:
    """
    Try to detect the company name from the cover page.
    Looks for common patterns like "XYZ Limited" or "XYZ Corporation".
    """
    if not page_texts:
        return None

    first_page = page_texts[0]
    patterns = [
        re.compile(r"^(.{5,80}(?:Limited|Ltd|Corporation|Corp|Inc|Pvt|Private|Public)\.?)\s*$",
                    re.IGNORECASE | re.MULTILINE),
        re.compile(r"^(.{5,80}(?:Company|Group|Industries|Enterprises|Holdings)\.?)\s*$",
                    re.IGNORECASE | re.MULTILINE),
    ]

    for pat in patterns:
        m = pat.search(first_page)
        if m:
            name = m.group(1).strip()
            if len(name) > 5:
                return name

    return None
