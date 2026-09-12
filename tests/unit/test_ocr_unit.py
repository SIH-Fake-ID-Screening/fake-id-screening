"""
tests/unit/test_ocr_unit.py
----------------------------
Fast, deterministic unit test suite for AI OCR helpers & field extraction logic.
Independent from PaddleOCR model initialization.
"""

import os
import sys
import unittest

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.ocr.normalizer import normalize_date, clean_text_field
from ai.ocr.field_extractor import FieldExtractor
from ai.ocr.schemas import OCRResult, ExtractedFields, ConfidenceScores, BoundingBox


class TestOCRUnit(unittest.TestCase):
    """Unit tests for date normalization, text cleaning, field extraction, and schemas."""

    def test_date_normalization(self):
        """Test date parsing logic across formats into YYYY-MM-DD."""
        self.assertEqual(normalize_date("14/05/2002"), "2002-05-14")
        self.assertEqual(normalize_date("2002-05-14"), "2002-05-14")
        self.assertEqual(normalize_date("30/06/2026"), "2026-06-30")
        self.assertEqual(normalize_date("30 JUN 2026"), "2026-06-30")
        self.assertEqual(normalize_date("June 30, 2026"), "2026-06-30")
        self.assertEqual(normalize_date("July 2029"), "2029-07-01")
        self.assertEqual(normalize_date("Card valid upto July 2029"), "2029-07-01")
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
            BoundingBox(text="KIET GROUP OF INSTITUTIONS", confidence=0.99, box=[[0, 0], [1, 0], [1, 1], [0, 1]]),
            BoundingBox(text="PRIYANSHU RANJAN", confidence=0.98, box=[[0, 2], [1, 2], [1, 3], [0, 3]]),
            BoundingBox(text="S/O VINOD KUMAR SINGH", confidence=0.94, box=[[0, 3], [1, 3], [1, 4], [0, 4]]),
            BoundingBox(text="2025-2029 B TECH IT", confidence=0.96, box=[[0, 5], [1, 5], [1, 6], [0, 6]]),
            BoundingBox(text="Card valid upto July 2029", confidence=0.95, box=[[0, 7], [1, 7], [1, 8], [0, 8]]),
            BoundingBox(text="202501100400016", confidence=0.99, box=[[0, 9], [1, 9], [1, 10], [0, 10]]),
        ]
        raw_text = "\n".join([b.text for b in boxes])
        extractor = FieldExtractor()
        extracted, scores = extractor.extract_fields(boxes, raw_text)

        self.assertEqual(extracted.student_id, "202501100400016")
        self.assertEqual(extracted.name, "PRIYANSHU RANJAN")
        self.assertEqual(extracted.college, "KIET Group of Institutions")
        self.assertEqual(extracted.course, "B TECH IT")
        self.assertEqual(extracted.valid_till, "2029-07-01")
        self.assertGreater(scores.student_id, 0.0)

    def test_schemas_and_dict_serialization(self):
        """Test OCRResult schema and dictionary output helper."""
        result = OCRResult(
            student_id="202501100400016",
            name="PRIYANSHU RANJAN",
            dob="2005-12-27",
            course="B TECH IT",
            college="KIET Group of Institutions",
            valid_till="2029-07-01",
            raw_text="202501100400016",
            confidence=ConfidenceScores(student_id=0.99, name=0.96, dob=0.98, course=0.95, college=0.97, valid_till=0.94)
        )
        d = result.to_dict()

        self.assertIsInstance(d, dict)
        self.assertEqual(d["student_id"], "202501100400016")
        self.assertEqual(d["name"], "PRIYANSHU RANJAN")
        self.assertEqual(d["dob"], "2005-12-27")
        self.assertEqual(d["course"], "B TECH IT")
        self.assertEqual(d["college"], "KIET Group of Institutions")
        self.assertEqual(d["valid_till"], "2029-07-01")


if __name__ == "__main__":
    unittest.main()
