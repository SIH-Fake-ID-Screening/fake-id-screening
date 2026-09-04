"""
tests/unit/test_ocr_unit.py
----------------------------
Fast, deterministic unit test suite for AI OCR helpers & field extraction logic.
Independent from PaddleOCR model initialization.
"""

import os
import sys
import unittest

# Add project root and backend to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
BACKEND_DIR = os.path.join(PROJECT_ROOT, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from ai.ocr.normalizer import normalize_date, clean_text_field
from ai.ocr.field_extractor import FieldExtractor
from ai.ocr.schemas import OCRResult, ExtractedFields, ConfidenceScores, BoundingBox
from ai.ocr.preprocessing import preprocess_image


class TestOCRUnit(unittest.TestCase):
    """Unit tests for date normalization, text cleaning, field extraction, and schemas."""

    def test_date_normalization(self):
        """Test date parsing logic across formats into YYYY-MM-DD."""
        self.assertEqual(normalize_date("14/05/2002"), "2002-05-14")
        self.assertEqual(normalize_date("2002-05-14"), "2002-05-14")
        self.assertEqual(normalize_date("30/06/2026"), "2026-06-30")
        self.assertEqual(normalize_date("30 JUN 2026"), "2026-06-30")
        self.assertEqual(normalize_date("June 30, 2026"), "2026-06-30")
        self.assertIsNone(normalize_date("INVALID_DATE"))
        self.assertIsNone(normalize_date(None))

    def test_clean_text_field(self):
        """Test text field cleaning function."""
        self.assertEqual(clean_text_field("  ALEX MORGAN : "), "ALEX MORGAN")
        self.assertEqual(clean_text_field("= 10948271 \n"), "10948271")
        self.assertIsNone(clean_text_field(""))
        self.assertIsNone(clean_text_field(None))

    def test_field_extractor_logic(self):
        """Test hybrid field extraction on mock bounding boxes."""
        boxes = [
            BoundingBox(text="COLLEGE OF ENGINEERING", confidence=0.99, box=[[0, 0], [1, 0], [1, 1], [0, 1]]),
            BoundingBox(text="NAME: ALEX MORGAN", confidence=0.98, box=[[0, 2], [1, 2], [1, 3], [0, 3]]),
            BoundingBox(text="STUDENT ID: 10948271", confidence=0.97, box=[[0, 4], [1, 4], [1, 5], [0, 5]]),
            BoundingBox(text="DOB: 14/05/2002", confidence=0.95, box=[[0, 6], [1, 6], [1, 7], [0, 7]]),
            BoundingBox(text="VALID TILL: 30/06/2026", confidence=0.96, box=[[0, 8], [1, 8], [1, 9], [0, 9]]),
        ]
        raw_text = "\n".join([b.text for b in boxes])
        extractor = FieldExtractor()
        extracted, scores = extractor.extract_fields(boxes, raw_text)

        self.assertEqual(extracted.student_id, "10948271")
        self.assertEqual(extracted.name, "ALEX MORGAN")
        self.assertEqual(extracted.dob, "2002-05-14")
        self.assertEqual(extracted.valid_till, "2026-06-30")
        self.assertIn("student_id", scores)

    def test_schemas_and_dict_serialization(self):
        """Test OCRResult schema and dictionary output helper."""
        fields = ExtractedFields(student_id="10948271", name="ALEX MORGAN")
        conf = ConfidenceScores(overall=0.95, field_scores={"student_id": 0.97})
        box = BoundingBox(text="10948271", confidence=0.97, box=[[0, 0], [1, 0], [1, 1], [0, 1]])

        result = OCRResult(raw_text="10948271", fields=fields, confidence=conf, bounding_boxes=[box])
        d = result.to_dict()

        self.assertIsInstance(d, dict)
        self.assertEqual(d["fields"]["student_id"], "10948271")
        self.assertEqual(d["fields"]["name"], "ALEX MORGAN")
        self.assertEqual(d["confidence"]["overall"], 0.95)


if __name__ == "__main__":
    unittest.main()
