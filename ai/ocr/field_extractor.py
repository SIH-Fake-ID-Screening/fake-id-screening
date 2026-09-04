"""
ai/ocr/field_extractor.py
--------------------------
Hybrid field extraction module using regex pattern matching, keyword detection,
and spatial/bounding box heuristics.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from .schemas import ExtractedFields, BoundingBox
from .normalizer import normalize_date, clean_text_field

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extracts structured document/ID fields from OCR bounding box results."""

    STUDENT_ID_KEYWORDS = ["STUDENT ID", "STUDENT NO", "ID NO", "ROLL NO", "REG NO", "ENROLLMENT", "ID NUMBER", "DOCUMENT NO", "CARD NO"]
    NAME_KEYWORDS = ["NAME", "STUDENT NAME", "FULL NAME", "CARDHOLDER"]
    DOB_KEYWORDS = ["DOB", "DATE OF BIRTH", "BIRTH DATE", "BORN"]
    COLLEGE_KEYWORDS = ["COLLEGE", "INSTITUTE", "UNIVERSITY", "SCHOOL", "CAMPUS"]
    COURSE_KEYWORDS = ["COURSE", "BRANCH", "PROGRAM", "PROGRAMME", "CLASS", "DEGREE"]
    VALIDITY_KEYWORDS = ["VALID TILL", "EXPIRY", "EXPIRY DATE", "VALID UNTIL", "EXPIRES"]

    def extract_fields(self, boxes: List[BoundingBox], raw_text: str) -> Tuple[ExtractedFields, Dict[str, float]]:
        """
        Perform hybrid field extraction across bounding box text blocks.

        Returns
        -------
        Tuple[ExtractedFields, Dict[str, float]]:
            (Extracted fields object, per-field confidence scores)
        """
        extracted = ExtractedFields()
        field_scores: Dict[str, float] = {}

        lines = [b.text.strip() for b in boxes if b.text.strip()]
        full_text_upper = raw_text.upper()

        # 1. Extract Student ID / Document Number
        id_val, id_conf = self._extract_student_id(boxes, lines)
        if id_val:
            extracted.student_id = id_val
            extracted.document_number = id_val
            field_scores["student_id"] = id_conf
            field_scores["document_number"] = id_conf

        # 2. Extract Name
        name_val, name_conf = self._extract_name(boxes, lines)
        if name_val:
            extracted.name = name_val
            field_scores["name"] = name_conf

        # 3. Extract DOB
        dob_val, dob_conf = self._extract_date(boxes, self.DOB_KEYWORDS, full_text_upper)
        if dob_val:
            extracted.dob = dob_val
            field_scores["dob"] = dob_conf

        # 4. Extract Validity / Expiry Date
        valid_val, valid_conf = self._extract_date(boxes, self.VALIDITY_KEYWORDS, full_text_upper)
        if valid_val:
            extracted.valid_till = valid_val
            extracted.expiry_date = valid_val
            field_scores["valid_till"] = valid_conf
            field_scores["expiry_date"] = valid_conf

        # 5. Extract College
        college_val, college_conf = self._extract_keyword_value(boxes, self.COLLEGE_KEYWORDS)
        if college_val:
            extracted.college = college_val
            field_scores["college"] = college_conf

        # 6. Extract Course
        course_val, course_conf = self._extract_keyword_value(boxes, self.COURSE_KEYWORDS)
        if course_val:
            extracted.course = course_val
            field_scores["course"] = course_conf

        return extracted, field_scores

    def _extract_student_id(self, boxes: List[BoundingBox], lines: List[str]) -> Tuple[Optional[str], float]:
        """Extract student ID using label match or alphanumeric pattern regex."""
        # Method A: Match near keyword
        val, conf = self._extract_keyword_value(boxes, self.STUDENT_ID_KEYWORDS)
        if val:
            cleaned_id = re.sub(r'[^\w\-]', '', val)
            if len(cleaned_id) >= 3:
                return cleaned_id, conf

        # Method B: Standalone long numeric/alphanumeric string (e.g. 202501100600212)
        # First scan for 8-16 digit pure numbers
        for b in boxes:
            text = b.text.strip()
            if re.match(r'^\d{8,16}$', text):
                return text, b.confidence

        # Next scan for alphanumeric pattern
        id_pattern = re.compile(r'\b([A-Z0-9]{5,16})\b', re.IGNORECASE)
        for b in boxes:
            text = b.text.strip()
            if any(kw in text.upper() for kw in ["COLLEGE", "UNIVERSITY", "STUDENT", "VALID", "NAME", "EXPIRY", "AUTONOMOUS", "INSTITUTE"]):
                continue
            matches = id_pattern.findall(text)
            for m in matches:
                # Avoid matching isolated 4-digit years like 2025 or 2029
                if len(m) == 4 and m.isdigit() and (1990 <= int(m) <= 2035):
                    continue
                if any(c.isdigit() for c in m) and len(m) >= 5:
                    return m.upper(), b.confidence

        return None, 0.0

    def _extract_name(self, boxes: List[BoundingBox], lines: List[str]) -> Tuple[Optional[str], float]:
        """Extract cardholder full name using keyword association or line heuristics."""
        ignore_words = ["COLLEGE", "UNIVERSITY", "ENGINEERING", "STUDENT", "IDENTITY", "CARD", "AUTONOMOUS", "INSTITUTE", "GRADE", "LEARNING", "REGISTRAR", "BLOOD", "GROUP", "ADDRESS"]

        # Method A: Keyword match (e.g. "NAME: ALEX MORGAN")
        val, conf = self._extract_keyword_value(boxes, self.NAME_KEYWORDS)
        if val:
            cleaned = clean_text_field(val)
            if cleaned and len(cleaned) >= 2 and not any(c.isdigit() for c in cleaned):
                if not any(kw in cleaned.upper() for kw in ignore_words):
                    return cleaned.upper(), conf

        # Method B: Heuristic scan for ALL CAPS full name (e.g. PRIYANSHU RANJAN)
        for b in boxes:
            text = b.text.strip()
            if text.isupper() and len(text.split()) in [2, 3] and not any(c.isdigit() for c in text):
                if not any(kw in text.upper() for kw in ignore_words):
                    return text, b.confidence

        # Method C: Title case name
        name_regex = re.compile(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}$')
        for b in boxes:
            text = b.text.strip()
            if name_regex.match(text) and not any(kw in text.upper() for kw in ignore_words):
                return text.upper(), b.confidence

        return None, 0.0

    def _extract_date(self, boxes: List[BoundingBox], keywords: List[str], full_text: str) -> Tuple[Optional[str], float]:
        """Extract and normalize date associated with target keywords."""
        for b in boxes:
            upper = b.text.upper()
            if any(kw in upper for kw in keywords):
                norm = normalize_date(b.text)
                if norm:
                    return norm, b.confidence

        val, conf = self._extract_keyword_value(boxes, keywords)
        if val:
            norm = normalize_date(val)
            if norm:
                return norm, conf

        date_pattern = re.compile(r'\b(\d{1,4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{2,4})\b', re.IGNORECASE)
        for b in boxes:
            matches = date_pattern.findall(b.text)
            for m in matches:
                norm = normalize_date(m)
                if norm:
                    return norm, b.confidence

        return None, 0.0

    def _extract_keyword_value(self, boxes: List[BoundingBox], keywords: List[str]) -> Tuple[Optional[str], float]:
        """Find value trailing or on the line following a keyword box."""
        for i, b in enumerate(boxes):
            text_upper = b.text.upper().strip()
            for kw in keywords:
                if kw in text_upper:
                    if ":" in b.text or "-" in b.text or "=" in b.text:
                        parts = re.split(r'[:=-]', b.text, maxsplit=1)
                        if len(parts) > 1 and parts[1].strip():
                            return clean_text_field(parts[1]), b.confidence

                    if i + 1 < len(boxes):
                        next_box = boxes[i + 1]
                        if not any(k in next_box.text.upper() for k in ["NAME", "DOB", "ID", "VALID", "COLLEGE", "COURSE"]):
                            return clean_text_field(next_box.text), next_box.confidence

        return None, 0.0
