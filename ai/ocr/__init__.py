"""
ai/ocr/__init__.py
------------------
Initialization module for the AI OCR & Field Extraction package.
"""



from .ocr_pipeline import (
    OCRProcessor,
    extract_document,
    extract_ocr_data,
)

__all__ = [
    "OCRProcessor",
    "extract_document",
    "extract_ocr_data",
]

