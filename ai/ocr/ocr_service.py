"""
ai/ocr/ocr_service.py
---------------------
Service wrapper exposing the primary extract_document function contract for the AI OCR engine.
Supports dual-image document processing (front_image_path, back_image_path).

Contract (SIH 2026 Team Guide)
-------------------------------
def extract_document(front_image_path: str, back_image_path: Optional[str] = None) -> dict
"""

import os
import logging
from typing import Dict, Any, Optional

from .ocr_pipeline import extract_ocr_data

logger = logging.getLogger(__name__)


def extract_document(front_image_path: str, back_image_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract structured text, key document fields, and OCR confidence scores
    from uploaded front (and optionally back) document image files.

    Parameters
    ----------
    front_image_path : str
        Absolute or relative filesystem path to the document front image.
    back_image_path : Optional[str]
        Absolute or relative filesystem path to the document back image.

    Returns
    -------
    dict
        Structured output containing:
        - student_id (str)
        - name (str)
        - dob (str)
        - course (str)
        - college (str)
        - valid_till (str)
        - raw_text (str)
        - confidence (dict)
        - bounding_boxes (list)
    """
    logger.info("Executing OCR service on front image: %s (back: %s)", front_image_path, back_image_path)

    if not front_image_path or not os.path.exists(front_image_path):
        logger.error("OCR service error: front_image_path '%s' does not exist.", front_image_path)
        raise FileNotFoundError(f"Document front image file not found at path: {front_image_path}")

    # 1. Process FRONT image
    front_res = extract_ocr_data(front_image_path)

    # 2. Process BACK image if provided
    back_res = None
    if back_image_path and os.path.exists(back_image_path):
        try:
            back_res = extract_ocr_data(back_image_path)
        except Exception as exc:
            logger.warning("Error processing back image '%s': %s", back_image_path, exc)

    # If no back image provided or back processing failed, return front_res directly
    if not back_res:
        return front_res

    # 3. Merge FRONT + BACK results intelligently
    raw_text = front_res.get("raw_text", "")
    if back_res.get("raw_text"):
        raw_text = f"{raw_text}\n---\n{back_res['raw_text']}".strip()

    # Front priority fields
    student_id = front_res.get("student_id") or back_res.get("student_id") or ""
    name = front_res.get("name") or back_res.get("name") or ""
    college = front_res.get("college") or back_res.get("college") or ""
    course = front_res.get("course") or back_res.get("course") or ""

    # Back priority for DOB if present, or Front
    dob = back_res.get("dob") or front_res.get("dob") or ""

    # Front priority for Validity if present, or Back
    valid_till = front_res.get("valid_till") or back_res.get("valid_till") or ""

    # Merge confidence scores
    front_conf = front_res.get("confidence", {})
    back_conf = back_res.get("confidence", {})

    merged_confidence = {
        "student_id": front_conf.get("student_id") if front_res.get("student_id") else back_conf.get("student_id", 0.0),
        "name": front_conf.get("name") if front_res.get("name") else back_conf.get("name", 0.0),
        "dob": back_conf.get("dob") if back_res.get("dob") else front_conf.get("dob", 0.0),
        "course": front_conf.get("course") if front_res.get("course") else back_conf.get("course", 0.0),
        "college": front_conf.get("college") if front_res.get("college") else back_conf.get("college", 0.0),
        "valid_till": front_conf.get("valid_till") if front_res.get("valid_till") else back_conf.get("valid_till", 0.0),
    }

    merged_boxes = front_res.get("bounding_boxes", []) + back_res.get("bounding_boxes", [])

    return {
        "student_id": student_id,
        "name": name,
        "dob": dob,
        "course": course,
        "college": college,
        "valid_till": valid_till,
        "raw_text": raw_text,
        "confidence": merged_confidence,
        "bounding_boxes": merged_boxes
    }


# Alias for backward compatibility
extract_document_data = extract_document
