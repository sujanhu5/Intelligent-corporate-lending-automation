"""
OCR extractor — produces raw text from uploaded financial documents.

Strategy per file type:
  PDF (digital/searchable)  → PyMuPDF text layer (fast, accurate, no image conversion)
  PDF (scanned / image-PDF) → pdf2image → OpenCV preprocess → Tesseract
  Image (PNG/JPEG/TIFF/BMP) → OpenCV preprocess → Tesseract

We try PyMuPDF first for PDFs; if the extracted text is too short (< 100 chars)
we fall back to the image-based pipeline assuming it is a scanned document.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

import pytesseract
from PIL import Image

from app.config import settings
from app.core.exceptions import OCRError
from app.core.logging import get_logger
from ocr.preprocessor import load_image_from_bytes, preprocess_image

logger = get_logger(__name__)

# Apply Tesseract executable path from .env
if settings.TESSERACT_CMD and settings.TESSERACT_CMD != "tesseract":
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

# Tesseract config: OEM 3 (LSTM neural net), PSM 6 (uniform block of text)
_TESS_CONFIG = "--oem 3 --psm 6"
# Fallback PSM modes tried when the primary config yields low-confidence
# output. PSM 4 = single column of variable-sized text (financial statements),
# PSM 11 = sparse text, no assumptions (blurry / broken layouts),
# PSM 3 = fully automatic page segmentation.
_TESS_FALLBACK_CONFIGS = (
    "--oem 3 --psm 4",
    "--oem 3 --psm 11",
    "--oem 3 --psm 3",
)
# Trigger the fallback sweep when the primary result's mean confidence is
# below this threshold OR the extracted text is suspiciously short.
_TESS_LOW_CONFIDENCE = 55.0
_TESS_MIN_CHARS_ON_PAGE = 40

# Text length threshold below which a PDF is treated as scanned
_DIGITAL_PDF_MIN_CHARS = 100


@dataclass
class PageResult:
    page_number: int
    text: str
    confidence: float               # 0.0 – 100.0


@dataclass
class ExtractionResult:
    raw_text: str
    page_results: List[PageResult] = field(default_factory=list)
    page_count: int = 0
    mean_confidence: float = 0.0
    extraction_method: str = "unknown"    # "pymupdf" | "tesseract" | "tesseract_fallback"
    duration_seconds: float = 0.0
    warnings: List[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def extract_text(file_path: str | Path) -> ExtractionResult:
    """
    Extract all text from *file_path*.  Dispatches to the correct sub-pipeline
    based on extension and content analysis.

    Raises:
        OCRError: if the file cannot be read or extraction fails entirely.
    """
    path = Path(file_path)
    if not path.exists():
        raise OCRError(message=f"File not found: {file_path}")

    start = time.perf_counter()
    ext = path.suffix.lower()

    try:
        if ext == ".pdf":
            result = _extract_pdf(path)
        elif ext in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}:
            result = _extract_image(path)
        elif ext in {".txt", ".csv"}:
            result = _extract_text_file(path)
        else:
            raise OCRError(message=f"Unsupported file type: '{ext}'")
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(message=f"Extraction failed for '{path.name}': {exc}") from exc

    result.duration_seconds = round(time.perf_counter() - start, 2)
    logger.info(
        "OCR extraction complete",
        extra={
            "file": path.name,
            "method": result.extraction_method,
            "pages": result.page_count,
            "confidence": result.mean_confidence,
            "duration_s": result.duration_seconds,
            "chars": len(result.raw_text),
        },
    )
    return result


# ---------------------------------------------------------------------------
# PDF pipeline
# ---------------------------------------------------------------------------

def _extract_pdf(path: Path) -> ExtractionResult:
    # Attempt 1 — PyMuPDF digital text layer
    digital = _pymupdf_extract(path)
    if digital and len(digital.raw_text.strip()) >= _DIGITAL_PDF_MIN_CHARS:
        return digital

    # Attempt 2 — Scanned PDF: render pages to images → Tesseract
    if digital:
        digital.warnings.append(
            "PyMuPDF extracted less than 100 characters — "
            "document appears to be scanned. Falling back to Tesseract OCR."
        )
    return _scanned_pdf_extract(path, prior_result=digital)


def _pymupdf_extract(path: Path) -> Optional[ExtractionResult]:
    """Extract text directly from a digital PDF's text layer."""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.warning("PyMuPDF not installed — skipping digital PDF extraction.")
        return None

    try:
        doc = fitz.open(str(path))
    except Exception as exc:
        logger.warning("PyMuPDF could not open PDF: %s", exc)
        return None

    pages: List[PageResult] = []
    full_text_parts: List[str] = []

    for i, page in enumerate(doc, start=1):
        try:
            text = page.get_text("text")
            if text:
                full_text_parts.append(text)
                # PyMuPDF does not provide per-word confidence; use 95.0 as proxy
                pages.append(PageResult(page_number=i, text=text, confidence=95.0))
        except Exception as exc:
            logger.warning("PyMuPDF failed on page %d: %s", i, exc)

    doc.close()
    raw = "\n".join(full_text_parts)

    return ExtractionResult(
        raw_text=raw,
        page_results=pages,
        page_count=len(pages),
        mean_confidence=95.0 if pages else 0.0,
        extraction_method="pymupdf",
    )


def _scanned_pdf_extract(
    path: Path, prior_result: Optional[ExtractionResult] = None
) -> ExtractionResult:
    """Convert each PDF page to an image and run Tesseract."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        raise OCRError(
            message="pdf2image is not installed. Cannot process scanned PDFs."
        )

    try:
        pil_images = convert_from_path(
            str(path),
            dpi=settings.OCR_DPI,
            fmt="png",
            thread_count=2,
        )
    except Exception as exc:
        raise OCRError(message=f"pdf2image conversion failed: {exc}") from exc

    pages: List[PageResult] = []
    warnings = prior_result.warnings if prior_result else []

    for i, pil_img in enumerate(pil_images, start=1):
        page_text, conf = _tesseract_on_pil(pil_img, page_num=i)
        pages.append(PageResult(page_number=i, text=page_text, confidence=conf))

    raw = "\n".join(p.text for p in pages)
    mean_conf = sum(p.confidence for p in pages) / len(pages) if pages else 0.0
    method = "tesseract_fallback" if prior_result else "tesseract"

    return ExtractionResult(
        raw_text=raw,
        page_results=pages,
        page_count=len(pages),
        mean_confidence=round(mean_conf, 2),
        extraction_method=method,
        warnings=warnings,
    )


# ---------------------------------------------------------------------------
# Plain-text file pipeline (.txt / .csv)
# ---------------------------------------------------------------------------

def _extract_text_file(path: Path) -> ExtractionResult:
    """
    Read a plain-text or CSV file directly. Skips OCR entirely — the text
    is already digital. Tries UTF-8, falls back to latin-1, then binary.
    """
    raw_bytes = path.read_bytes()
    for encoding in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw_bytes.decode("utf-8", errors="replace")

    return ExtractionResult(
        raw_text=text,
        page_results=[PageResult(page_number=1, text=text, confidence=100.0)],
        page_count=1,
        mean_confidence=100.0,
        extraction_method="text_file",
    )


# ---------------------------------------------------------------------------
# Image pipeline
# ---------------------------------------------------------------------------

def _extract_image(path: Path) -> ExtractionResult:
    try:
        raw_bytes = path.read_bytes()
        cv_img = load_image_from_bytes(raw_bytes)
        if cv_img is None:
            raise OCRError(message=f"OpenCV could not decode image: {path.name}")
        preprocessed = preprocess_image(cv_img, dpi=settings.OCR_DPI)

        # Convert back to PIL for Tesseract
        pil_img = Image.fromarray(preprocessed)
        text, conf = _tesseract_on_pil(pil_img, page_num=1)
    except OCRError:
        raise
    except Exception as exc:
        raise OCRError(message=f"Image OCR failed: {exc}") from exc

    return ExtractionResult(
        raw_text=text,
        page_results=[PageResult(page_number=1, text=text, confidence=conf)],
        page_count=1,
        mean_confidence=conf,
        extraction_method="tesseract",
    )


# ---------------------------------------------------------------------------
# Tesseract wrapper
# ---------------------------------------------------------------------------

def _tesseract_on_pil(pil_img: Image.Image, page_num: int) -> tuple[str, float]:
    """
    Run Tesseract on a PIL image (after preprocessing if it came from pdf2image).
    Returns (text, mean_confidence_0_to_100).
    """
    import numpy as np

    # Preprocess PIL → NumPy → preprocess → back to PIL
    try:
        cv_arr = np.array(pil_img.convert("RGB"))
        preprocessed = preprocess_image(cv_arr, dpi=settings.OCR_DPI)
        pil_preprocessed = Image.fromarray(preprocessed)
    except Exception as exc:
        logger.warning("Preprocessing failed for page %d: %s — using raw image", page_num, exc)
        pil_preprocessed = pil_img

    def _run(config: str) -> tuple[str, float]:
        data = pytesseract.image_to_data(
            pil_preprocessed,
            lang=settings.TESSERACT_LANG,
            config=config,
            output_type=pytesseract.Output.DICT,
        )
        text = pytesseract.image_to_string(
            pil_preprocessed,
            lang=settings.TESSERACT_LANG,
            config=config,
        )
        confs = [int(c) for c in data["conf"] if int(c) >= 0]
        mean = sum(confs) / len(confs) if confs else 0.0
        return text, round(mean, 2)

    try:
        best_text, best_conf = _run(_TESS_CONFIG)

        # If the primary pass looks weak, sweep additional PSM modes and
        # keep whichever produces the highest-confidence result. This is
        # what recovers text from blurry, low-contrast, or oddly-laid-out
        # pages that the default block-of-text segmentation misses.
        if best_conf < _TESS_LOW_CONFIDENCE or len(best_text.strip()) < _TESS_MIN_CHARS_ON_PAGE:
            for cfg in _TESS_FALLBACK_CONFIGS:
                try:
                    alt_text, alt_conf = _run(cfg)
                except Exception as exc:
                    logger.debug("Tesseract fallback %s failed: %s", cfg, exc)
                    continue
                # Prefer higher confidence; on a tie prefer the longer text.
                if (alt_conf > best_conf) or (
                    alt_conf == best_conf and len(alt_text) > len(best_text)
                ):
                    best_text, best_conf = alt_text, alt_conf

        return best_text, best_conf
    except Exception as exc:
        logger.warning("Tesseract failed on page %d: %s", page_num, exc)
        return "", 0.0
