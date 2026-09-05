"""
services/ocr_service.py
-----------------------
OCR service interface for extracting student identity fields from ID-card images.

Architecture note
-----------------
This module owns the OCR step in the screening pipeline:

    document_front + document_back
              ↓
        extract_document()
              ↓
        { student_id, name, dob, course, ... }

The returned student_id is then used for the database lookup.
The face-verification service never calls this module directly.

Integration (PaddleOCR via ai/ocr)
------------------------------------
This service delegates to the real OCR engine at ai/ocr/ when available.
The ai/ocr module (OCRProcessor / extract_ocr_data) uses PaddleOCR 2.9.1
with PP-OCRv4 model, angle classification, and OpenCV pre-processing.

Pipeline used per call:
    front image → ai/ocr/ocr_service.extract_document(front_image_path)
                      → OCRResult.fields.student_id  (primary key)
                      → OCRResult.fields.name
                      → OCRResult.fields.dob
                      → OCRResult.fields.course
    back image  → ai/ocr/ocr_service.extract_document(back_image_path)
                      → merged only if front is missing a field

Return contract (UNCHANGED — api/screening.py uses this shape):
    {
        "student_id": str,
        "name":       str,
        "dob":        str,
        "course":     str,
    }

Fallback
--------
If the ai/ocr package is unavailable (e.g. PaddleOCR not installed), the
service automatically falls back to the mock implementation and logs a warning.
This preserves dev-mode usability while the full deps are being installed.
"""

import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve and register the ai/ package on sys.path so that `import ai.ocr`
# works regardless of how the backend server is launched (uvicorn from
# backend/ or from the repo root).
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent  # SIH-Backend/
_AI_PARENT = str(_REPO_ROOT)

if _AI_PARENT not in sys.path:
    sys.path.insert(0, _AI_PARENT)


# ---------------------------------------------------------------------------
# Try to load the real OCR engine from ai/ocr.
# ---------------------------------------------------------------------------
_ai_ocr_extract = None

try:
    from ai.ocr.ocr_service import extract_document as _ai_extract_document  # noqa: E402
    _ai_ocr_extract = _ai_extract_document
    logger.info(
        "[OCR] Real PaddleOCR engine loaded successfully from ai/ocr. "
        "Mock implementation is disabled."
    )
except ImportError as _import_err:
    logger.warning(
        "[OCR] Could not import ai/ocr module (%s). "
        "Falling back to mock implementation. "
        "Install PaddleOCR and its dependencies to enable real OCR.",
        _import_err,
    )
except Exception as _load_err:
    logger.error(
        "[OCR] Unexpected error loading ai/ocr module: %s. "
        "Falling back to mock implementation.",
        _load_err,
    )


# ---------------------------------------------------------------------------
# Internal helper: map ai/ocr OCRResult dict → pipeline-compatible flat dict
# ---------------------------------------------------------------------------

def _map_ocr_result(raw_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalise the ai/ocr OCRResult dict into the flat contract expected
    by api/screening.py.

    ai/ocr returns:
        {
            "raw_text":       str,
            "fields": {
                "student_id": str | None,
                "name":       str | None,
                "dob":        str | None,
                "course":     str | None,
                "college":    str | None,
                ...
            },
            "confidence": { "overall": float, "field_scores": {...} },
            "bounding_boxes": [...],
        }

    This function extracts and returns only:
        {
            "student_id": str,
            "name":       str,
            "dob":        str,
            "course":     str,
        }
    """
    fields = raw_result.get("fields", {})

    # Handle both Pydantic model (has .dict() / .model_dump()) and plain dict.
    if hasattr(fields, "model_dump"):
        fields = fields.model_dump()
    elif hasattr(fields, "dict"):
        fields = fields.dict()

    return {
        "student_id": fields.get("student_id") or "",
        "name":       fields.get("name")       or "",
        "dob":        fields.get("dob")        or "",
        "course":     fields.get("course")     or "",
        "valid_till": fields.get("valid_till") or "",
    }


# ---------------------------------------------------------------------------
# Internal helper: merge two OCR flat-dicts (front takes priority)
# ---------------------------------------------------------------------------

def _merge_results(front: Dict[str, Any], back: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge OCR results from front and back images.
    Front image fields take priority; missing fields fall back to back image.
    """
    merged = dict(front)
    for key in ("student_id", "name", "dob", "course", "valid_till"):
        if not merged.get(key) and back.get(key):
            merged[key] = back[key]
            logger.debug("[OCR] Field '%s' supplemented from back image: %s", key, back[key])
    return merged


# ---------------------------------------------------------------------------
# Public interface  (signature UNCHANGED from original mock)
# ---------------------------------------------------------------------------

def extract_document(front_image_path: str, back_image_path: str) -> Dict[str, Any]:
    """
    Extract student identity fields from ID-card images.

    Parameters
    ----------
    front_image_path : Absolute path to the saved front-side image.
    back_image_path  : Absolute path to the saved back-side image.

    Returns
    -------
    dict with keys:
        student_id : str   — college-issued student ID (primary lookup key)
        name       : str   — full name as printed on the card
        dob        : str   — date of birth string (YYYY-MM-DD or raw OCR text)
        course     : str   — programme / branch

    Implementation
    --------------
    Delegates to the real PaddleOCR engine (ai/ocr) when available.
    Falls back to a hard-coded mock result if the engine is unavailable.
    """
    if _ai_ocr_extract is not None:
        return _extract_with_real_ocr(front_image_path, back_image_path)
    else:
        return _extract_mock(front_image_path, back_image_path)


# ---------------------------------------------------------------------------
# Real OCR path
# ---------------------------------------------------------------------------

def _extract_with_real_ocr(
    front_image_path: str, back_image_path: str
) -> Dict[str, Any]:
    """
    Run the real PaddleOCR engine on both document images and merge results.

    The front image is processed first (it usually contains the student_id
    and name). The back image supplements any fields that the front missed.
    """
    logger.info(
        "[OCR] Processing front image: %s", front_image_path
    )

    front_result: Dict[str, Any] = {}
    back_result:  Dict[str, Any] = {}

    # --- Process front image ---
    try:
        raw_front = _ai_ocr_extract(front_image_path)
        print(f"[DEBUG OCR] Front raw text:\n{raw_front.get('raw_text', '')}")
        front_result = _map_ocr_result(raw_front)
        print(
            f"[DEBUG OCR] Front image extracted: student_id={front_result.get('student_id')!r} name={front_result.get('name')!r} dob={front_result.get('dob')!r} course={front_result.get('course')!r}"
        )
    except FileNotFoundError:
        logger.error("[OCR] Front image not found: %s", front_image_path)
    except Exception as exc:
        logger.error("[OCR] Error processing front image: %s", exc, exc_info=True)

    # --- Process back image (only if back path is present and different) ---
    if back_image_path and back_image_path != front_image_path:
        logger.info("[OCR] Processing back image: %s", back_image_path)
        try:
            raw_back = _ai_ocr_extract(back_image_path)
            print(f"[DEBUG OCR] Back raw text:\n{raw_back.get('raw_text', '')}")
            back_result = _map_ocr_result(raw_back)
            print(
                f"[DEBUG OCR] Back image extracted: student_id={back_result.get('student_id')!r} name={back_result.get('name')!r} dob={back_result.get('dob')!r} course={back_result.get('course')!r}"
            )
        except FileNotFoundError:
            logger.warning("[OCR] Back image not found: %s — skipping back OCR", back_image_path)
        except Exception as exc:
            logger.warning("[OCR] Error processing back image: %s — skipping back OCR", exc)

    # --- Merge front + back results ---
    merged = _merge_results(front_result, back_result)

    logger.info(
        "[OCR] Final merged result: student_id=%r name=%r dob=%r course=%r",
        merged.get("student_id"),
        merged.get("name"),
        merged.get("dob"),
        merged.get("course"),
    )

    return merged


# ---------------------------------------------------------------------------
# Mock fallback (development only)
# ---------------------------------------------------------------------------

def _extract_mock(front_image_path: str, back_image_path: str) -> Dict[str, Any]:
    """
    Mock implementation used when PaddleOCR is unavailable.

    !! MOCK — DO NOT USE IN PRODUCTION !!
    Returns hard-coded data for Priyanshu Ranjan to allow pipeline integration
    testing without the full OCR stack installed.
    """
    logger.warning(
        "[OCR MOCK] PaddleOCR unavailable — returning hard-coded data. "
        "front=%s back=%s",
        front_image_path,
        back_image_path,
    )

    mock_result = {
        "student_id": "202501100600212",  # Priyanshu Ranjan — real DB record
        "name":       "Priyanshu Ranjan",
        "dob":        "2005-12-27",
        "course":     "B.Tech IT",
        "valid_till": "2028-06-30",
    }

    logger.info("[OCR MOCK] Returning mock OCR result: %s", mock_result)
    return mock_result
