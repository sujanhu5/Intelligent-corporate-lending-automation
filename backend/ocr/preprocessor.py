"""
Image preprocessor — OpenCV-based pipeline that cleans and enhances images
before feeding them to Tesseract OCR.

Pipeline (in order):
  1. Convert to grayscale
  2. Upscale if resolution is too low (< 300 DPI equivalent)
  3. Denoise (Non-local means denoising)
  4. Adaptive thresholding (binarisation)
  5. Deskew (straighten rotated scans)
  6. Morphological cleanup (fill small holes, remove specks)

All steps are idempotent and degrade gracefully — if one step fails the
image is passed to the next step unchanged rather than crashing the pipeline.
"""

from __future__ import annotations

import math
from typing import Optional, Tuple

import cv2
import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

# Minimum width/height we want to work with. Images below this get upscaled.
_MIN_DIM = 1000


def preprocess_image(image: np.ndarray, dpi: int = 300) -> np.ndarray:
    """
    Full preprocessing pipeline.

    Args:
        image: BGR or grayscale uint8 NumPy array.
        dpi:   Target DPI for upscaling decisions.

    Returns:
        Preprocessed grayscale uint8 array ready for Tesseract.
    """
    img = _to_grayscale(image)
    img = _upscale_if_small(img)
    img = _denoise(img)
    img = _binarise(img)
    img = _deskew(img)
    img = _morphological_cleanup(img)
    return img


# ---------------------------------------------------------------------------
# Step helpers
# ---------------------------------------------------------------------------

def _to_grayscale(image: np.ndarray) -> np.ndarray:
    if len(image.shape) == 2:
        return image
    if image.shape[2] == 4:          # RGBA → BGR
        image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)


def _upscale_if_small(image: np.ndarray) -> np.ndarray:
    h, w = image.shape[:2]
    if h < _MIN_DIM or w < _MIN_DIM:
        scale = max(_MIN_DIM / h, _MIN_DIM / w)
        new_w = int(w * scale)
        new_h = int(h * scale)
        image = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        logger.debug("Image upscaled from %dx%d to %dx%d", w, h, new_w, new_h)
    return image


def _denoise(image: np.ndarray) -> np.ndarray:
    try:
        # h=10 is gentle enough not to blur thin characters
        return cv2.fastNlMeansDenoising(image, h=10, templateWindowSize=7, searchWindowSize=21)
    except Exception as exc:
        logger.warning("Denoising failed: %s — skipping", exc)
        return image


def _binarise(image: np.ndarray) -> np.ndarray:
    """
    Adaptive Gaussian thresholding handles uneven lighting common in scans.
    Falls back to Otsu global threshold if adaptive fails.
    """
    try:
        return cv2.adaptiveThreshold(
            image,
            maxValue=255,
            adaptiveMethod=cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            thresholdType=cv2.THRESH_BINARY,
            blockSize=31,
            C=10,
        )
    except Exception:
        try:
            _, binary = cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            return binary
        except Exception as exc:
            logger.warning("Binarisation failed: %s — skipping", exc)
            return image


def _deskew(image: np.ndarray) -> np.ndarray:
    """
    Estimate and correct skew angle using Hough line detection.
    Skips correction if the detected angle is within ±0.5° (negligible skew).
    Caps correction at ±15° to avoid false positives on legitimate diagonal content.
    """
    try:
        angle = _estimate_skew_angle(image)
        if abs(angle) < 0.5 or abs(angle) > 15:
            return image
        return _rotate_image(image, angle)
    except Exception as exc:
        logger.warning("Deskew failed: %s — skipping", exc)
        return image


def _estimate_skew_angle(image: np.ndarray) -> float:
    """Return estimated skew angle in degrees using Hough transform."""
    edges = cv2.Canny(image, 50, 150, apertureSize=3)
    lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=100)
    if lines is None:
        return 0.0

    angles = []
    for rho, theta in lines[:, 0]:
        angle = (theta * 180 / np.pi) - 90
        if -45 < angle < 45:
            angles.append(angle)

    if not angles:
        return 0.0
    return float(np.median(angles))


def _rotate_image(image: np.ndarray, angle: float) -> np.ndarray:
    h, w = image.shape[:2]
    centre = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(centre, angle, 1.0)
    return cv2.warpAffine(
        image, M, (w, h),
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_REPLICATE,
    )


def _morphological_cleanup(image: np.ndarray) -> np.ndarray:
    """
    Small morphological operations to reconnect broken character strokes
    and remove isolated noise pixels.
    """
    try:
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 2))
        # Close small gaps inside characters
        closed = cv2.morphologyEx(image, cv2.MORPH_CLOSE, kernel)
        return closed
    except Exception as exc:
        logger.warning("Morphological cleanup failed: %s — skipping", exc)
        return image


# ---------------------------------------------------------------------------
# Utility — load image from bytes (used by extractor)
# ---------------------------------------------------------------------------

def load_image_from_bytes(data: bytes) -> np.ndarray:
    """Decode raw bytes to a BGR NumPy array."""
    buf = np.frombuffer(data, dtype=np.uint8)
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)
