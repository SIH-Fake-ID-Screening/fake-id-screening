"""
services/ocr_service.py

Backend OCR adapter.

Flow:
    document_front + document_back
            ↓
    real ai/ocr OCR engine
            ↓
    normalized flat dictionary
            ↓
    screening pipeline
"""

import logging
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Resolve repository root so `ai.ocr` can be imported when backend is started
# from either backend/ or repository root.
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_REPO_ROOT_STR = str(_REPO_ROOT)

if _REPO_ROOT_STR not in sys.path:
    sys.path.insert(0, _REPO_ROOT_STR)


# ---------------------------------------------------------------------------
# Load REAL OCR engine only.
# Mock fallback is intentionally disabled.
# ---------------------------------------------------------------------------

_ai_ocr_extract = None

try:
    from ai.ocr.ocr_service import extract_document as _ai_extract_document

    _ai_ocr_extract = _ai_extract_document

    logger.info(
        "[OCR] Real OCR engine loaded successfully from ai/ocr."
    )

except ImportError as exc:
    logger.error(
        "[OCR] Could not import ai/ocr OCR engine: %s",
        exc,
    )

except Exception as exc:
    logger.exception(
        "[OCR] Unexpected error loading ai/ocr OCR engine: %s",
        exc,
    )


# ---------------------------------------------------------------------------
# Empty OCR result
# ---------------------------------------------------------------------------

def _empty_result() -> Dict[str, Any]:
    return {
        "student_id": "",
        "name": "",
        "dob": "",
        "course": "",
        "college": "",
        "valid_till": "",
    }


# ---------------------------------------------------------------------------
# Convert OCRResult → backend dictionary
# ---------------------------------------------------------------------------

def _map_ocr_result(raw_result: Any) -> Dict[str, Any]:
    """
    Convert the current ai/ocr OCRResult into the backend flat contract.

    Supports:

    1. New OCRResult model:
       result.student_id
       result.name
       result.dob
       result.course
       result.college
       result.valid_till

    2. Pydantic model_dump()

    3. Dataclass to_dict()

    4. Old nested format:
       {
           "fields": {
               "student_id": "...",
               ...
           }
       }

    5. Normal dictionary.
    """

    if raw_result is None:
        return _empty_result()

    # ---------------------------------------------------------------
    # Convert object → dictionary where possible
    # ---------------------------------------------------------------

    if hasattr(raw_result, "model_dump"):
        data = raw_result.model_dump()

    elif hasattr(raw_result, "to_dict"):
        data = raw_result.to_dict()

    elif hasattr(raw_result, "dict"):
        data = raw_result.dict()

    elif isinstance(raw_result, dict):
        data = dict(raw_result)

    else:
        data = {}

    # ---------------------------------------------------------------
    # Support OLD OCRResult format:
    #
    # {
    #     "fields": {
    #         "student_id": "...",
    #         ...
    #     }
    # }
    # ---------------------------------------------------------------

    fields = data.get("fields")

    if fields is not None:

        if hasattr(fields, "model_dump"):
            fields = fields.model_dump()

        elif hasattr(fields, "to_dict"):
            fields = fields.to_dict()

        elif hasattr(fields, "dict"):
            fields = fields.dict()

        elif not isinstance(fields, dict):
            fields = {}

        if isinstance(fields, dict):
            data.update(fields)

    # ---------------------------------------------------------------
    # Support NEW OCRResult direct attributes.
    #
    # This is important because current ai/ocr returns:
    #
    # result.student_id
    # result.name
    # result.dob
    # result.course
    # result.college
    # result.valid_till
    # ---------------------------------------------------------------

    keys = (
        "student_id",
        "name",
        "dob",
        "course",
        "college",
        "valid_till",
    )

    for key in keys:

        current_value = data.get(key)

        if not current_value and hasattr(raw_result, key):

            value = getattr(raw_result, key)

            if value is not None:
                data[key] = value

    # ---------------------------------------------------------------
    # Final flat backend contract
    # ---------------------------------------------------------------

    return {
        "student_id": str(data.get("student_id") or ""),
        "name": str(data.get("name") or ""),
        "dob": str(data.get("dob") or ""),
        "course": str(data.get("course") or ""),
        "college": str(data.get("college") or ""),
        "valid_till": str(data.get("valid_till") or ""),
    }


# ---------------------------------------------------------------------------
# Merge FRONT + BACK
# ---------------------------------------------------------------------------

def _merge_results(
    front: Dict[str, Any],
    back: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Merge front and back OCR results.

    Front has priority.

    Back is used only when front did not extract a field.

    Important:
        Back-side mobile number must NEVER replace student_id.
        Only fields explicitly returned by OCR are merged.
    """

    merged = _empty_result()

    # First take front values
    for key in merged.keys():

        if front.get(key):
            merged[key] = front[key]

    # Then supplement missing fields from back
    for key in merged.keys():

        if not merged.get(key) and back.get(key):

            merged[key] = back[key]

            logger.debug(
                "[OCR] Field '%s' supplemented from back image.",
                key,
            )

    return merged


# ---------------------------------------------------------------------------
# PUBLIC API
# ---------------------------------------------------------------------------

def extract_document(
    front_image_path: str,
    back_image_path: str,
) -> Dict[str, Any]:
    """
    Extract structured identity information from ID-card front and back.

    Returns:

    {
        "student_id": "...",
        "name": "...",
        "dob": "...",
        "course": "...",
        "college": "...",
        "valid_till": "..."
    }

    No mock data is returned.
    """

    if _ai_ocr_extract is None:

        logger.error(
            "[OCR] Real OCR engine is unavailable. "
            "Mock fallback is disabled."
        )

        return _empty_result()

    return _extract_with_real_ocr(
        front_image_path,
        back_image_path,
    )


# ---------------------------------------------------------------------------
# REAL OCR
# ---------------------------------------------------------------------------

def _extract_with_real_ocr(
    front_image_path: str,
    back_image_path: str,
) -> Dict[str, Any]:

    logger.info(
        "[OCR] Processing front image: %s",
        front_image_path,
    )

    front_result = _empty_result()
    back_result = _empty_result()

    # ===============================================================
    # FRONT
    # ===============================================================

    try:

        raw_front = _ai_ocr_extract(front_image_path)

        front_raw_text = (
            raw_front.get("raw_text", "")
            if isinstance(raw_front, dict)
            else getattr(raw_front, "raw_text", "")
        )

        print(
            f"[DEBUG OCR] Front raw text:\n{front_raw_text}"
        )

        front_result = _map_ocr_result(raw_front)

        print(
            "[DEBUG OCR] Front image extracted: "
            f"student_id={front_result.get('student_id')!r} "
            f"name={front_result.get('name')!r} "
            f"dob={front_result.get('dob')!r} "
            f"course={front_result.get('course')!r} "
            f"college={front_result.get('college')!r} "
            f"valid_till={front_result.get('valid_till')!r}"
        )

    except FileNotFoundError:

        logger.error(
            "[OCR] Front image not found: %s",
            front_image_path,
        )

    except Exception as exc:

        logger.exception(
            "[OCR] Error processing front image: %s",
            exc,
        )

    # ===============================================================
    # BACK
    # ===============================================================

    if (
        back_image_path
        and back_image_path != front_image_path
    ):

        logger.info(
            "[OCR] Processing back image: %s",
            back_image_path,
        )

        try:

            raw_back = _ai_ocr_extract(back_image_path)

            back_raw_text = (
                raw_back.get("raw_text", "")
                if isinstance(raw_back, dict)
                else getattr(raw_back, "raw_text", "")
            )

            print(
                f"[DEBUG OCR] Back raw text:\n{back_raw_text}"
            )

            back_result = _map_ocr_result(raw_back)

            print(
                "[DEBUG OCR] Back image extracted: "
                f"student_id={back_result.get('student_id')!r} "
                f"name={back_result.get('name')!r} "
                f"dob={back_result.get('dob')!r} "
                f"course={back_result.get('course')!r} "
                f"college={back_result.get('college')!r} "
                f"valid_till={back_result.get('valid_till')!r}"
            )

        except FileNotFoundError:

            logger.warning(
                "[OCR] Back image not found: %s",
                back_image_path,
            )

        except Exception as exc:

            logger.warning(
                "[OCR] Error processing back image: %s",
                exc,
            )

    # ===============================================================
    # MERGE
    # ===============================================================

    merged = _merge_results(
        front_result,
        back_result,
    )

    logger.info(
        "[OCR] Final merged result: "
        "student_id=%r name=%r dob=%r course=%r "
        "college=%r valid_till=%r",
        merged.get("student_id"),
        merged.get("name"),
        merged.get("dob"),
        merged.get("course"),
        merged.get("college"),
        merged.get("valid_till"),
    )

    return merged