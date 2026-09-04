"""
ai/ocr/__init__.py
------------------
Initialization module for the AI OCR & Field Extraction package.
"""

from .ocr_pipeline import OCRProcessor, extract_ocr_data
from .ocr_service import extract_document, extract_document_data

__all__ = ["OCRProcessor", "extract_ocr_data", "extract_document", "extract_document_data"]
