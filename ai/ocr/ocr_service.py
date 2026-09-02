"""
ai/ocr/ocr_service.py
---------------------
Service wrapper exposing the primary extract_document function contract for the AI OCR engine.

Contract (SIH 2026 Team Guide)
-------------------------------
def extract_document(image_path: str) -> dict
"""

import os
import logging
from typing import Dict, Any

from .ocr_pipeline import extract_ocr_data

logger = logging.getLogger(__name__)


def extract_document(image_path: str) -> Dict[str, Any]:
    """
    Extract structured text, key document fields, and OCR confidence scores
    from an uploaded document image file.

    Parameters
    ----------
    image_path : str
        Absolute or relative filesystem path to the uploaded document image.

    Returns
    -------
    dict
        Structured output matching the project OCR output contract.
    """
    logger.info("Executing OCR service on image: %s", image_path)

    if not image_path or not os.path.exists(image_path):
        logger.error("OCR service error: image_path '%s' does not exist.", image_path)
        raise FileNotFoundError(f"Document image file not found at path: {image_path}")

    try:
        ocr_result = extract_ocr_data(image_path)
        logger.info("OCR service successfully processed image: %s", image_path)
        return ocr_result
    except Exception as exc:
        logger.exception("Unexpected error in OCR service processing '%s': %s", image_path, exc)
        raise


# Alias for backward compatibility
extract_document_data = extract_document
