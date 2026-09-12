"""
tests/unit/test_ocr_contract.py
--------------------------------
Contract tests for the OCR output shape as required by SIH 2026.

Tests:
  A. DOB extraction
  B. validity extraction
  C. DOB must not become valid_till
  D. valid_till must not come from an unrelated date
  E. "Card valid upto July 2029" -> "2029-07-01"
  F. "Card valid upto 31/07/2029" -> "2029-07-31"
  G. missing validity phrase -> ""
  H. missing DOB -> ""
"""

import os
import sys
import unittest

# Add project root to Python path
PROJECT_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from ai.ocr.field_extractor import FieldExtractor
from ai.ocr.schemas import BoundingBox
from ai.ocr.ocr_pipeline import _to_contract_dict


def make_box(text, x=0, y=0, w=200, h=30, confidence=0.99):
    """Helper: create a BoundingBox at the given position."""
    return BoundingBox(
        text=text,
        confidence=confidence,
        box=[
            [x, y],
            [x + w, y],
            [x + w, y + h],
            [x, y + h],
        ],
    )


def extract(boxes):
    """Run FieldExtractor.extract_fields and return (fields, scores)."""
    extractor = FieldExtractor()
    raw_text = "\n".join(b.text for b in boxes)
    return extractor.extract_fields(boxes, raw_text)


# ===========================================================================
# A. DOB EXTRACTION
# ===========================================================================

class TestContractDOB(unittest.TestCase):
    """A. DOB extraction from various label formats."""

    def test_dob_colon_inline(self):
        """DOB: 14/05/2002 -> 2002-05-14"""
        fields, _ = extract([make_box("DOB: 14/05/2002")])
        self.assertEqual(fields.dob, "2002-05-14")

    def test_dob_period_label_separate_box(self):
        """D.O.B. label / value in next box -> 2005-12-27"""
        boxes = [
            make_box("D.O.B.", y=0),
            make_box("27/12/2005", x=250, y=0),
        ]
        fields, _ = extract(boxes)
        self.assertEqual(fields.dob, "2005-12-27")

    def test_date_of_birth_label(self):
        """Date of Birth: 30/06/1999 -> 1999-06-30"""
        fields, _ = extract([make_box("Date of Birth: 30/06/1999")])
        self.assertEqual(fields.dob, "1999-06-30")

    def test_dob_iso_input(self):
        """DOB: 2002-05-14 (already ISO) -> 2002-05-14"""
        fields, _ = extract([make_box("DOB: 2002-05-14")])
        self.assertEqual(fields.dob, "2002-05-14")


# ===========================================================================
# B. VALIDITY EXTRACTION
# ===========================================================================

class TestContractValidity(unittest.TestCase):
    """B. Validity extraction from various phrase/label formats."""

    def test_valid_till_colon_full_date(self):
        """VALID TILL: 30/06/2026 -> 2026-06-30"""
        fields, _ = extract([make_box("VALID TILL: 30/06/2026")])
        self.assertEqual(fields.valid_till, "2026-06-30")

    def test_valid_till_separate_boxes(self):
        """'VALID TILL' label + '31/07/2028' value -> 2028-07-31"""
        boxes = [
            make_box("VALID TILL", y=0),
            make_box("31/07/2028", x=250, y=0),
        ]
        fields, _ = extract(boxes)
        self.assertEqual(fields.valid_till, "2028-07-31")

    def test_expiry_date_label(self):
        """EXPIRY DATE: 30/06/2026 -> 2026-06-30"""
        fields, _ = extract([make_box("EXPIRY DATE: 30/06/2026")])
        self.assertEqual(fields.valid_till, "2026-06-30")

    def test_valid_upto_sentence_month_year(self):
        """'Valid upto July 2029' sentence -> 2029-07-01"""
        fields, _ = extract([make_box("Valid upto July 2029")])
        self.assertEqual(fields.valid_till, "2029-07-01")

    def test_valid_until_sentence_full_date(self):
        """'Valid until 30/06/2026' sentence -> 2026-06-30"""
        fields, _ = extract([make_box("Valid until 30/06/2026")])
        self.assertEqual(fields.valid_till, "2026-06-30")


# ===========================================================================
# C. DOB MUST NOT BECOME valid_till
# ===========================================================================

class TestContractDOBNotValidity(unittest.TestCase):
    """C. Strict separation: DOB must never populate valid_till."""

    def test_dob_only_card_back(self):
        """Card back: DOB only. valid_till must be None."""
        boxes = [
            make_box("D.O.B.", y=0),
            make_box("27/12/2005", x=250, y=0),
            make_box("Blood Group", y=50),
            make_box("Mob. No.", y=100),
            make_box("8789427924", x=250, y=100),
        ]
        fields, _ = extract(boxes)
        self.assertEqual(fields.dob, "2005-12-27")
        self.assertIsNone(fields.valid_till)

    def test_dob_with_address_no_validity(self):
        """DOB + address noise -> valid_till stays None."""
        boxes = [
            make_box("D.O.B.", y=0),
            make_box("15/08/2004", x=250, y=0),
            make_box("Address", y=50),
            make_box("841211", y=100),
        ]
        fields, _ = extract(boxes)
        self.assertEqual(fields.dob, "2004-08-15")
        self.assertIsNone(fields.valid_till)


# ===========================================================================
# D. valid_till MUST NOT COME FROM AN UNRELATED DATE
# ===========================================================================

class TestContractNoArbitraryDate(unittest.TestCase):
    """D. Arbitrary dates in OCR text must not populate valid_till."""

    def test_academic_year_range_not_valid_till(self):
        """'2025-2029 B TECH IT' must not make valid_till = 2029."""
        boxes = [
            make_box("2025-2029 B TECH IT", y=0),
            make_box("Registrar", y=50),
        ]
        fields, _ = extract(boxes)
        self.assertIsNone(fields.valid_till)

    def test_standalone_year_not_valid_till(self):
        """A standalone year value must not populate valid_till."""
        boxes = [make_box("2025-2029")]
        fields, _ = extract(boxes)
        self.assertIsNone(fields.valid_till)

    def test_phone_number_not_student_id(self):
        """10-digit number must not be captured as student_id."""
        boxes = [
            make_box("Mob. No.", y=0),
            make_box("8789427924", x=250, y=0),
        ]
        fields, _ = extract(boxes)
        self.assertIsNone(fields.student_id)


# ===========================================================================
# E. "Card valid upto July 2029" -> "2029-07-01"
# ===========================================================================

class TestContractMonthYearSentence(unittest.TestCase):
    """E. Month-year validity phrase maps to YYYY-MM-01."""

    def test_e_card_valid_upto_july_2029(self):
        fields, _ = extract([make_box("Card valid upto July 2029")])
        self.assertEqual(fields.valid_till, "2029-07-01")

    def test_card_valid_upto_january_2030(self):
        fields, _ = extract([make_box("Card valid upto January 2030")])
        self.assertEqual(fields.valid_till, "2030-01-01")

    def test_card_valid_upto_december_2028(self):
        fields, _ = extract([make_box("Card valid upto December 2028")])
        self.assertEqual(fields.valid_till, "2028-12-01")


# ===========================================================================
# F. "Card valid upto 31/07/2029" -> "2029-07-31"
# ===========================================================================

class TestContractExactDateSentence(unittest.TestCase):
    """F. Exact date in validity sentence maps to YYYY-MM-DD."""

    def test_f_card_valid_upto_exact_date(self):
        fields, _ = extract([make_box("Card valid upto 31/07/2029")])
        self.assertEqual(fields.valid_till, "2029-07-31")

    def test_card_valid_upto_dmy_dashes(self):
        fields, _ = extract([make_box("Card valid upto 30-06-2026")])
        self.assertEqual(fields.valid_till, "2026-06-30")


# ===========================================================================
# G. MISSING VALIDITY PHRASE -> "" in contract output
# ===========================================================================

class TestContractMissingValidity(unittest.TestCase):
    """G. When no validity phrase exists, contract dict valid_till is ''."""

    def test_g_missing_validity_internal_none(self):
        """Internal field is None when no validity phrase."""
        fields, _ = extract([make_box("DOB: 27/12/2005")])
        self.assertIsNone(fields.valid_till)

    def test_g_contract_dict_valid_till_empty_string(self):
        """Public contract dict maps None -> ''."""
        from ai.ocr.schemas import ExtractedFields
        fields = ExtractedFields(dob="2005-12-27")
        result = _to_contract_dict(fields)
        self.assertEqual(result["valid_till"], "")
        self.assertEqual(result["dob"], "2005-12-27")


# ===========================================================================
# H. MISSING DOB -> "" in contract output
# ===========================================================================

class TestContractMissingDOB(unittest.TestCase):
    """H. When no DOB label exists, contract dict dob is ''."""

    def test_h_missing_dob_internal_none(self):
        """Internal field is None when no DOB label found."""
        fields, _ = extract([make_box("VALID TILL: 30/06/2026")])
        self.assertIsNone(fields.dob)

    def test_h_contract_dict_dob_empty_string(self):
        """Public contract dict maps None dob -> ''."""
        from ai.ocr.schemas import ExtractedFields
        fields = ExtractedFields(valid_till="2026-06-30")
        result = _to_contract_dict(fields)
        self.assertEqual(result["dob"], "")
        self.assertEqual(result["valid_till"], "2026-06-30")


# ===========================================================================
# CONTRACT SHAPE INTEGRITY
# ===========================================================================

class TestContractShape(unittest.TestCase):
    """Verify the contract dict always has exactly the 5 required keys."""

    def test_contract_has_exactly_five_keys(self):
        from ai.ocr.schemas import ExtractedFields
        fields = ExtractedFields()
        result = _to_contract_dict(fields)
        self.assertEqual(
            set(result.keys()),
            {"student_id", "name", "dob", "course", "valid_till"},
        )

    def test_all_none_fields_become_empty_string(self):
        from ai.ocr.schemas import ExtractedFields
        fields = ExtractedFields()  # all None
        result = _to_contract_dict(fields)
        for key in ("student_id", "name", "dob", "course", "valid_till"):
            self.assertEqual(result[key], "", f"{key} should be '' not None")

    def test_internal_extra_fields_not_in_contract(self):
        """college, passport_number, etc. must NOT appear in contract output."""
        from ai.ocr.schemas import ExtractedFields
        fields = ExtractedFields(
            college="XYZ University",
            passport_number="A1234567",
            nationality="Indian",
        )
        result = _to_contract_dict(fields)
        self.assertNotIn("college", result)
        self.assertNotIn("passport_number", result)
        self.assertNotIn("nationality", result)


# ===========================================================================
# REAL CARD SIMULATION
# ===========================================================================

class TestContractRealCardSimulation(unittest.TestCase):
    """End-to-end simulation of the real KIET card front and back."""

    def test_front_card_full_pipeline(self):
        """Front: name, student_id, course, valid_till. No DOB on front."""
        boxes = [
            make_box("KIETA+", y=0),
            make_box("GROUP OF INSTITUTIONS NAAC", y=30),
            make_box("www.kiet.edu", y=60),
            make_box("Connecting Life with Learning GRADE", y=90),
            make_box("An Autonomous Institute", y=120),
            make_box("PRIYANSHU RANJAN", y=150),
            make_box("S/O VINOD KUMAR SINGH", y=180),
            make_box("2025-2029 B TECH IT", y=210),
            make_box("Card valid upto July 2029", y=240),
            make_box("Registrar", y=270),
            make_box("202501100600212", y=300),
        ]
        fields, _ = extract(boxes)
        result = _to_contract_dict(fields)

        self.assertEqual(result["name"], "PRIYANSHU RANJAN")
        self.assertEqual(result["student_id"], "202501100600212")
        self.assertEqual(result["course"], "B TECH IT")
        self.assertEqual(result["valid_till"], "2029-07-01")
        self.assertEqual(result["dob"], "")  # not on front side

    def test_back_card_full_pipeline(self):
        """Back: DOB only. No name/ID/course/validity on back."""
        boxes = [
            make_box("D.O.B.", y=0),
            make_box("27/12/2005", x=250, y=0),
            make_box("Blood Group", y=50),
            make_box("Mob. No.", y=100),
            make_box("8789427924", x=250, y=100),
            make_box("Address", y=150),
        ]
        fields, _ = extract(boxes)
        result = _to_contract_dict(fields)

        self.assertEqual(result["dob"], "2005-12-27")
        self.assertEqual(result["valid_till"], "")
        self.assertEqual(result["student_id"], "")
        self.assertEqual(result["name"], "")
        self.assertEqual(result["course"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
