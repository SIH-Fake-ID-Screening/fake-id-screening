"""
ai/ocr/field_extractor.py
--------------------------
Hybrid field extraction module using regex pattern matching, keyword detection,
and spatial/bounding box heuristics.
"""

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from .schemas import ExtractedFields, ConfidenceScores, BoundingBox
from .normalizer import normalize_date, clean_text_field

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extracts structured document/ID fields from OCR bounding box results."""

    STUDENT_ID_KEYWORDS = ["STUDENT ID", "STUDENT NO", "ID NO", "ROLL NO", "REG NO", "ENROLLMENT", "ID NUMBER", "DOCUMENT NO", "CARD NO"]
    NAME_KEYWORDS = ["NAME", "STUDENT NAME", "FULL NAME", "CARDHOLDER"]
    DOB_KEYWORDS = ["DOB", "D.O.B", "DATE OF BIRTH", "BIRTH DATE", "BORN"]
    COLLEGE_KEYWORDS = ["COLLEGE", "INSTITUTE", "UNIVERSITY", "SCHOOL", "CAMPUS", "GROUP OF INSTITUTIONS"]
    COURSE_KEYWORDS = ["COURSE", "BRANCH", "PROGRAM", "PROGRAMME", "CLASS", "DEGREE"]
    VALIDITY_KEYWORDS = ["VALID UPTO", "VALID UP TO", "VALID TILL", "VALID UNTIL", "CARD VALID UPTO", "EXPIRY", "EXPIRY DATE", "EXPIRES"]

    IGNORE_NAME_WORDS = [
        "COLLEGE", "UNIVERSITY", "ENGINEERING", "STUDENT", "IDENTITY", "CARD", "AUTONOMOUS",
        "INSTITUTE", "INSTITUTIONS", "GRADE", "LEARNING", "REGISTRAR", "BLOOD", "GROUP", "ADDRESS",
        "DUPLICATE", "ROAD", "INDIA", "VALID", "UPTO", "TILL", "PAYMENT", "ISSUED", "CONNECTING", "NAAC"
    ]

    def extract_fields(self, boxes: List[BoundingBox], raw_text: str) -> Tuple[ExtractedFields, ConfidenceScores]:
        """
        Perform hybrid field extraction across bounding box text blocks.

        Returns
        -------
        Tuple[ExtractedFields, ConfidenceScores]:
            (Extracted fields object, per-field confidence scores)
        """
        extracted = ExtractedFields()
        scores = ConfidenceScores()

        lines = [b.text.strip() for b in boxes if b.text.strip()]
        full_text_upper = raw_text.upper()

        # 1. Extract Student ID / Document Number
        id_val, id_conf = self._extract_student_id(boxes, lines)
        if id_val:
            extracted.student_id = id_val
            scores.student_id = id_conf

        # 2. Extract Name
        name_val, name_conf = self._extract_name(boxes, lines)
        if name_val:
            extracted.name = name_val
            scores.name = name_conf

        # 3. Extract DOB
        dob_val, dob_conf = self._extract_dob(boxes, full_text_upper)
        if dob_val:
            extracted.dob = dob_val
            scores.dob = dob_conf

        # 4. Extract Validity / Expiry Date
        valid_val, valid_conf = self._extract_validity(boxes, full_text_upper)
        if valid_val:
            extracted.valid_till = valid_val
            scores.valid_till = valid_conf

        # 5. Extract College
        college_val, college_conf = self._extract_college(boxes)
        if college_val:
            extracted.college = college_val
            scores.college = college_conf

        # 6. Extract Course
        course_val, course_conf = self._extract_course(boxes)
        if course_val:
            extracted.course = course_val
            scores.course = course_conf

        return extracted, scores

    def _extract_student_id(self, boxes: List[BoundingBox], lines: List[str]) -> Tuple[str, float]:
        """Extract 12-16 digit student ID number. Returns "" if not reliably found."""
        # Method A: Match near keyword (e.g., "STUDENT ID: 202501100400016")
        val, conf = self._extract_keyword_value(boxes, self.STUDENT_ID_KEYWORDS)
        if val:
            cleaned_id = re.sub(r'[^\d]', '', val)
            if 8 <= len(cleaned_id) <= 18:
                return cleaned_id, conf

        # Method B: Pure 10-16 digit string in standalone box (e.g. 202501100400016)
        for b in boxes:
            text_digits = re.sub(r'[^\d]', '', b.text.strip())
            if 10 <= len(text_digits) <= 18:
                # Avoid matching phone numbers starting with 7/8/9 if 10 digits
                if len(text_digits) == 10 and text_digits[0] in '789':
                    continue
                return text_digits, b.confidence

        # Method C: Regex pattern scan
        for b in boxes:
            text = b.text.strip()
            if any(kw in text.upper() for kw in ["COLLEGE", "UNIVERSITY", "STUDENT", "VALID", "NAME", "EXPIRY", "AUTONOMOUS", "INSTITUTE", "ROAD"]):
                continue
            matches = re.findall(r'\b\d{10,18}\b', text)
            for m in matches:
                if len(m) == 10 and m[0] in '789':
                    continue
                return m, b.confidence

        return "", 0.0

    def _extract_name(self, boxes: List[BoundingBox], lines: List[str]) -> Tuple[str, float]:
        """Extract cardholder full name. Excludes institution headers."""
        # Method A: Keyword match (e.g. "NAME: PRIYANSHU RANJAN")
        val, conf = self._extract_keyword_value(boxes, self.NAME_KEYWORDS)
        if val:
            cleaned = clean_text_field(val)
            if cleaned and len(cleaned) >= 2 and not any(c.isdigit() for c in cleaned):
                if not any(kw in cleaned.upper() for kw in self.IGNORE_NAME_WORDS):
                    return cleaned.upper(), conf

        # Method B: Line preceding S/O or D/O or W/O (e.g., line above "S/O VINOD KUMAR SINGH")
        for i, b in enumerate(boxes):
            text_upper = b.text.upper().strip()
            if text_upper.startswith("S/O") or text_upper.startswith("D/O") or text_upper.startswith("W/O") or "SON OF" in text_upper:
                if i > 0:
                    prev_box = boxes[i - 1]
                    prev_text = prev_box.text.strip()
                    if prev_text.isupper() and len(prev_text.split()) in [2, 3] and not any(c.isdigit() for c in prev_text):
                        if not any(kw in prev_text.upper() for kw in self.IGNORE_NAME_WORDS):
                            return prev_text, prev_box.confidence

        # Method C: ALL CAPS 2-3 word string situated in middle of card
        for b in boxes:
            text = b.text.strip()
            if text.isupper() and len(text.split()) in [2, 3] and not any(c.isdigit() for c in text):
                if not any(kw in text.upper() for kw in self.IGNORE_NAME_WORDS):
                    return text, b.confidence

        return "", 0.0

    def _extract_college(self, boxes: List[BoundingBox]) -> Tuple[str, float]:
        """Extract institute/college name and format in proper Title Case."""
        for b in boxes:
            text_upper = b.text.upper().strip()
            # Avoid websites or URLs
            if "WWW." in text_upper or "HTTP" in text_upper or "@" in text_upper:
                continue

            if "KIET" in text_upper or "GROUP OF INSTITUTIONS" in text_upper:
                return "KIET Group of Institutions", b.confidence
            if "COLLEGE OF" in text_upper or "INSTITUTE OF" in text_upper or "UNIVERSITY" in text_upper:
                # Format to Title Case
                words = [w.capitalize() for w in b.text.strip().split()]
                return " ".join(words), b.confidence

        return "", 0.0

    def _extract_course(self, boxes: List[BoundingBox]) -> Tuple[str, float]:
        """Extract degree/branch (e.g. B TECH IT) without session years."""
        course_pattern = re.compile(r'\b(B\s*\.?\s*TECH(?:\s*I\s*T|\s*C\s*S\s*E|\s+[A-Z]{2,4})?|M\s*\.?\s*TECH(?:\s+[A-Z]{2,4})?|BCA|MCA|MBA|BBA|B\s*\.?\s*SC|B\s*\.?\s*COM|DIPLOMA)\b', re.IGNORECASE)

        for b in boxes:
            text = b.text.strip()
            # Separate degree letter from attached session years e.g. "2025-2029B" -> "B"
            text_fixed = re.sub(r'20\d{2}\s*[\-\/]\s*20\d{2}\s*([A-Z])', r' \1', text, flags=re.IGNORECASE)
            text_no_years = re.sub(r'\b20\d{2}\s*[\-\/]\s*20\d{2}\b', '', text_fixed).strip()
            # Insert space before IT/CSE if attached to TECH e.g. TECHIT -> TECH IT
            text_fixed_tech = re.sub(r'(TECH)(IT|CSE|ECE|ME|CE|EE)', r'\1 \2', text_no_years, flags=re.IGNORECASE)
            match = course_pattern.search(text_fixed_tech)
            if match:
                matched_str = match.group(0).strip().upper()
                matched_str = re.sub(r'\s+', ' ', matched_str)
                return matched_str, b.confidence

        return "", 0.0

    def _extract_dob(self, boxes: List[BoundingBox], full_text: str) -> Tuple[str, float]:
        """Extract Date of Birth strictly when explicit DOB context is present."""
        for b in boxes:
            upper = b.text.upper()
            if any(kw in upper for kw in self.DOB_KEYWORDS):
                norm = normalize_date(b.text)
                if norm:
                    return norm, b.confidence

        val, conf = self._extract_keyword_value(boxes, self.DOB_KEYWORDS)
        if val:
            norm = normalize_date(val)
            if norm:
                return norm, conf

        return "", 0.0

    def _extract_validity(self, boxes: List[BoundingBox], full_text: str) -> Tuple[str, float]:
        """Extract validity/expiry date strictly when explicit validity context is present."""
        for b in boxes:
            upper = b.text.upper()
            if any(kw in upper for kw in self.VALIDITY_KEYWORDS):
                norm = normalize_date(b.text)
                if norm:
                    return norm, b.confidence

        val, conf = self._extract_keyword_value(boxes, self.VALIDITY_KEYWORDS)
        if val:
            norm = normalize_date(val)
            if norm:
                return norm, conf

        return "", 0.0

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
