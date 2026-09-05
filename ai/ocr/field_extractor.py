"""
ai/ocr/field_extractor.py
--------------------------
Evidence-based field extraction from PaddleOCR bounding boxes.

Supports:
- Label:value fields
- Label/value in separate OCR boxes
- Unlabelled student IDs
- Unlabelled names using S/O, D/O, W/O
- Academic-year + course patterns
- "Card valid upto ..." patterns
- Institution-name cleanup

The extractor intentionally avoids arbitrary guessing.
"""

import re
import logging

from .schemas import ExtractedFields
from .normalizer import normalize_date, clean_text_field

logger = logging.getLogger(__name__)


class FieldExtractor:
    """Extract structured document fields from OCR bounding boxes."""

    STUDENT_ID_KEYWORDS = [
        "STUDENT ID",
        "STUDENT NO",
        "ID NO",
        "ROLL NO",
        "REG NO",
        "REGISTRATION NO",
        "ENROLLMENT",
        "ENROLLMENT NO",
        "ID NUMBER",
        "DOCUMENT NO",
        "DOCUMENT NUMBER",
        "CARD NO",
        "CARD NUMBER",
    ]

    NAME_KEYWORDS = [
        "STUDENT NAME",
        "FULL NAME",
        "CARDHOLDER NAME",
        "CARDHOLDER",
        "NAME",
    ]

    DOB_KEYWORDS = [
        "DATE OF BIRTH",
        "BIRTH DATE",
        "DOB",
        "D.O.B",
        "D.O.B.",
        "BORN",
    ]

    COLLEGE_KEYWORDS = [
        "COLLEGE",
        "INSTITUTE",
        "UNIVERSITY",
        "SCHOOL",
        "CAMPUS",
    ]

    COURSE_KEYWORDS = [
        "COURSE",
        "BRANCH",
        "PROGRAM",
        "PROGRAMME",
        "DEGREE",
    ]

    VALIDITY_KEYWORDS = [
        "VALID TILL",
        "VALID UNTIL",
        "VALID UPTO",
        "VALID UP TO",
        "EXPIRY DATE",
        "EXPIRY",
        "EXPIRES",
        "EXPIRATION DATE",
    ]

    PASSPORT_KEYWORDS = [
        "PASSPORT NO",
        "PASSPORT NUMBER",
        "PASSPORT",
    ]

    NATIONALITY_KEYWORDS = [
        "NATIONALITY",
        "CITIZENSHIP",
    ]

    VISA_KEYWORDS = [
        "VISA",
        "VISA NO",
        "VISA NUMBER",
        "VISA TYPE",
    ]

    def extract_fields(self, boxes, raw_text):
        extracted = ExtractedFields()
        field_scores = {}

        # =========================================================
        # STUDENT ID
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.STUDENT_ID_KEYWORDS,
            self._valid_id,
        )

        if value:
            extracted.student_id = value
            extracted.document_number = value

            field_scores["student_id"] = confidence
            field_scores["document_number"] = confidence

        # Unlabelled long numeric student ID
        if extracted.student_id is None:
            value, confidence = self._extract_unlabeled_student_id(
                boxes
            )

            if value:
                extracted.student_id = value
                extracted.document_number = value

                field_scores["student_id"] = confidence
                field_scores["document_number"] = confidence

        # =========================================================
        # NAME
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.NAME_KEYWORDS,
            self._valid_name,
        )

        if value:
            extracted.name = value.upper()
            field_scores["name"] = confidence

        # Unlabelled name before S/O, D/O, W/O or C/O
        if extracted.name is None:
            value, confidence = self._extract_name_from_relation(
                boxes
            )

            if value:
                extracted.name = value.upper()
                field_scores["name"] = confidence

        # =========================================================
        # DOB
        # =========================================================

        value, confidence = self._extract_date(
            boxes,
            self.DOB_KEYWORDS,
        )

        if value:
            extracted.dob = value
            field_scores["dob"] = confidence

        # =========================================================
        # VALID TILL / EXPIRY
        # =========================================================

        value, confidence = self._extract_validity(boxes)

        if value:
            extracted.valid_till = value
            extracted.expiry_date = value

            field_scores["valid_till"] = confidence
            field_scores["expiry_date"] = confidence

        # =========================================================
        # COLLEGE
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.COLLEGE_KEYWORDS,
            self._valid_text,
        )

        if value:
            extracted.college = value
            field_scores["college"] = confidence

        # Unlabelled institution header
        if extracted.college is None:
            value, confidence = self._extract_unlabeled_college(
                boxes
            )

            if value:
                extracted.college = value
                field_scores["college"] = confidence

        # =========================================================
        # COURSE
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.COURSE_KEYWORDS,
            self._valid_text,
        )

        if value:
            extracted.course = value
            field_scores["course"] = confidence

        # Unlabelled academic-year + course row
        if extracted.course is None:
            value, confidence = self._extract_unlabeled_course(
                boxes
            )

            if value:
                extracted.course = value
                field_scores["course"] = confidence

        # =========================================================
        # PASSPORT
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.PASSPORT_KEYWORDS,
            self._valid_passport,
        )

        if value:
            extracted.passport_number = value.upper()

            if extracted.document_number is None:
                extracted.document_number = value.upper()
                field_scores["document_number"] = confidence

            field_scores["passport_number"] = confidence

        # =========================================================
        # NATIONALITY
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.NATIONALITY_KEYWORDS,
            self._valid_text,
        )

        if value:
            extracted.nationality = value
            field_scores["nationality"] = confidence

        # =========================================================
        # VISA
        # =========================================================

        value, confidence = self._extract_labeled_value(
            boxes,
            self.VISA_KEYWORDS,
            self._valid_text,
        )

        if value:
            extracted.visa_info = value
            field_scores["visa_info"] = confidence

        return extracted, field_scores

    # =============================================================
    # LABELLED VALUE
    # =============================================================

    def _extract_labeled_value(
        self,
        boxes,
        keywords,
        validator,
    ):
        normalized_keywords = [
            self._normalize_label(keyword)
            for keyword in keywords
        ]

        for i, box in enumerate(boxes):

            text = box.text.strip()

            if not text:
                continue

            normalized_text = self._normalize_label(text)

            # -----------------------------------------------------
            # NAME: JOHN DOE
            # -----------------------------------------------------

            for keyword in normalized_keywords:

                pattern = (
                    rf"^{re.escape(keyword)}"
                    rf"\s*[:=\-]\s*(.+)$"
                )

                match = re.match(
                    pattern,
                    normalized_text,
                    re.IGNORECASE,
                )

                if match:

                    candidate = clean_text_field(
                        match.group(1)
                    )

                    if validator(candidate):
                        return (
                            candidate,
                            box.confidence,
                        )

            # -----------------------------------------------------
            # NAME JOHN DOE
            # -----------------------------------------------------

            for keyword in normalized_keywords:

                if normalized_text.startswith(keyword):

                    remainder = normalized_text[
                        len(keyword):
                    ].strip(" :-=")

                    if remainder and validator(remainder):

                        return (
                            remainder,
                            box.confidence,
                        )

            # -----------------------------------------------------
            # NAME [separate box] JOHN DOE
            # -----------------------------------------------------

            for keyword in normalized_keywords:

                if normalized_text == keyword:

                    candidate_box = (
                        self._find_nearest_value(
                            boxes,
                            i,
                            keywords,
                            validator,
                        )
                    )

                    if candidate_box:

                        return (
                            clean_text_field(
                                candidate_box.text
                            ),
                            candidate_box.confidence,
                        )

        return None, 0.0

    # =============================================================
    # SPATIAL VALUE SEARCH
    # =============================================================

    def _find_nearest_value(
        self,
        boxes,
        label_index,
        all_keywords,
        validator,
    ):
        label_box = boxes[label_index]

        lx1, ly1, lx2, ly2 = self._box_bounds(
            label_box
        )

        label_center_y = (ly1 + ly2) / 2

        candidates = []

        for i, candidate in enumerate(boxes):

            if i == label_index:
                continue

            text = candidate.text.strip()

            if not text:
                continue

            normalized = self._normalize_label(text)

            if self._is_any_known_label(normalized):
                continue

            if not validator(text):
                continue

            cx1, cy1, cx2, cy2 = self._box_bounds(
                candidate
            )

            candidate_center_y = (cy1 + cy2) / 2

            vertical_distance = abs(
                candidate_center_y - label_center_y
            )

            horizontal_distance = abs(
                cx1 - lx2
            )

            same_row = (
                vertical_distance
                <= max(
                    35,
                    (ly2 - ly1) * 1.5,
                )
            )

            if same_row and cx1 >= lx1:

                distance = (
                    horizontal_distance
                    + vertical_distance
                )

                candidates.append(
                    (distance, candidate)
                )

        if candidates:

            candidates.sort(
                key=lambda x: x[0]
            )

            return candidates[0][1]

        # Search below label
        below_candidates = []

        for i, candidate in enumerate(boxes):

            if i == label_index:
                continue

            text = candidate.text.strip()

            if not text:
                continue

            normalized = self._normalize_label(text)

            if self._is_any_known_label(normalized):
                continue

            if not validator(text):
                continue

            cx1, cy1, cx2, cy2 = self._box_bounds(
                candidate
            )

            if cy1 >= ly2:

                vertical_distance = cy1 - ly2

                horizontal_distance = abs(
                    cx1 - lx1
                )

                if vertical_distance <= 100:

                    distance = (
                        vertical_distance
                        + horizontal_distance
                    )

                    below_candidates.append(
                        (distance, candidate)
                    )

        if below_candidates:

            below_candidates.sort(
                key=lambda x: x[0]
            )

            return below_candidates[0][1]

        return None

    # =============================================================
    # UNLABELLED STUDENT ID
    # =============================================================

    def _extract_unlabeled_student_id(self, boxes):

        candidates = []

        for box in boxes:

            value = box.text.strip().replace(
                " ",
                "",
            )

            # 12-16 digits only.
            #
            # This rejects:
            # 2005
            # 841211
            # 201206
            # 8789427924
            if not re.fullmatch(
                r"\d{12,16}",
                value,
            ):
                continue

            candidates.append(
                (
                    value,
                    box.confidence,
                )
            )

        if not candidates:
            return None, 0.0

        candidates.sort(
            key=lambda item: item[1],
            reverse=True,
        )

        return candidates[0]

    # =============================================================
    # UNLABELLED NAME
    # =============================================================

    def _extract_name_from_relation(self, boxes):

        for i, box in enumerate(boxes):

            text = box.text.strip().upper()

            if re.match(
                r"^(S/O|D/O|W/O|C/O)\b",
                text,
            ):

                if i == 0:
                    continue

                previous = boxes[i - 1]

                candidate = previous.text.strip()

                if self._valid_name(candidate):

                    return (
                        candidate,
                        previous.confidence,
                    )

        return None, 0.0

    # =============================================================
    # DOB
    # =============================================================

    def _extract_date(
        self,
        boxes,
        keywords,
    ):
        normalized_keywords = [
            self._normalize_label(keyword)
            for keyword in keywords
        ]

        for i, box in enumerate(boxes):

            text = box.text.strip()

            if not text:
                continue

            normalized_text = self._normalize_label(
                text
            )

            for keyword in normalized_keywords:

                pattern = (
                    rf"^{re.escape(keyword)}"
                    rf"\s*[:=\-]?\s*(.+)$"
                )

                match = re.match(
                    pattern,
                    normalized_text,
                    re.IGNORECASE,
                )

                if match:

                    candidate = match.group(1)

                    normalized_date = (
                        normalize_date(candidate)
                    )

                    if normalized_date:

                        return (
                            normalized_date,
                            box.confidence,
                        )

                if normalized_text == keyword:

                    candidate_box = (
                        self._find_nearest_value(
                            boxes,
                            i,
                            keywords,
                            self._valid_date,
                        )
                    )

                    if candidate_box:

                        normalized_date = (
                            normalize_date(
                                candidate_box.text
                            )
                        )

                        if normalized_date:

                            return (
                                normalized_date,
                                candidate_box.confidence,
                            )

        # Never assign arbitrary dates to DOB.
        return None, 0.0

    # =============================================================
    # VALIDITY
    # =============================================================

    def _extract_validity(self, boxes):

        # First try normal labelled extraction.
        value, confidence = (
            self._extract_labeled_value(
                boxes,
                self.VALIDITY_KEYWORDS,
                self._valid_date,
            )
        )

        if value:
            # Normalize raw date string to ISO format (YYYY-MM-DD or YYYY-MM-01).
            normalized = (
                normalize_date(value)
                or self._normalize_month_year(value)
            )
            if normalized:
                return normalized, confidence

        # ---------------------------------------------------------
        # Sentence patterns:
        #   "Card valid upto July 2029"
        #   "Card valid upto 31/07/2029"
        #   "Valid TILL 30/06/2026"
        # ---------------------------------------------------------

        _VALIDITY_SENTENCE_PATTERNS = [
            r"\bCARD\s+VALID\b.*?([A-Za-z]+\s+\d{4}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4}|\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})",
            r"\bVALID\s+UPTO\b\s*(.+)$",
            r"\bVALID\s+UNTIL\b\s*(.+)$",
            r"\bVALID\s+TILL\b\s*(.+)$",
            r"\bVALID\s+UP\s+TO\b\s*(.+)$",
        ]

        for box in boxes:

            text = box.text.strip()

            for pattern in _VALIDITY_SENTENCE_PATTERNS:

                match = re.search(
                    pattern,
                    text,
                    re.IGNORECASE,
                )

                if match:

                    candidate = match.group(1).strip()

                    # Try exact date first (e.g. 31/07/2029 → 2029-07-31)
                    normalized_date = normalize_date(candidate)

                    # Then try month-year (e.g. July 2029 → 2029-07-01)
                    if not normalized_date:
                        normalized_date = self._normalize_month_year(candidate)

                    if normalized_date:
                        return (
                            normalized_date,
                            box.confidence,
                        )

        # ---------------------------------------------------------
        # Label and value are separate boxes.
        # ---------------------------------------------------------

        _SEPARATE_LABELS = {
            "VALID UPTO",
            "VALID UNTIL",
            "VALID TILL",
            "VALID UP TO",
        }

        for i, box in enumerate(boxes):

            normalized = self._normalize_label(
                box.text
            )

            if normalized in _SEPARATE_LABELS:

                if i + 1 < len(boxes):

                    candidate = boxes[
                        i + 1
                    ].text.strip()

                    # Try exact date first, then month-year
                    normalized_date = (
                        normalize_date(candidate)
                        or self._normalize_month_year(candidate)
                    )

                    if normalized_date:

                        return (
                            normalized_date,
                            boxes[
                                i + 1
                            ].confidence,
                        )

        return None, 0.0

    # =============================================================
    # UNLABELLED COLLEGE
    # =============================================================

    def _extract_unlabeled_college(self, boxes):

        for box in boxes:

            text = box.text.strip()

            upper = text.upper()

            if (
                "GROUP OF INSTITUTIONS"
                not in upper
            ):
                continue

            # -----------------------------------------------------
            # Current card:
            #
            # KIETA+
            # GROUP OF INSTITUTIONS NAAC
            #
            # The second line is the useful institution phrase.
            # Look at the previous OCR box for the institution
            # prefix.
            # -----------------------------------------------------

            current_clean = re.sub(
                r"\bNAAC\b",
                "",
                text,
                flags=re.IGNORECASE,
            )

            current_clean = re.sub(
                r"\bGRADE\b",
                "",
                current_clean,
                flags=re.IGNORECASE,
            )

            current_clean = current_clean.strip()

            # Find this box's position.
            try:
                index = boxes.index(box)
            except ValueError:
                index = -1

            prefix = ""

            if index > 0:

                previous_text = (
                    boxes[index - 1]
                    .text
                    .strip()
                )

                # KIETA+ -> KIET
                previous_clean = re.sub(
                    r"\bA\+\b",
                    "",
                    previous_text,
                    flags=re.IGNORECASE,
                )

                previous_clean = re.sub(
                    r"\+",
                    "",
                    previous_clean,
                ).strip()

                # Only use a short uppercase institution prefix.
                if re.fullmatch(
                    r"[A-Z]{2,15}",
                    previous_clean,
                ):
                    prefix = previous_clean

            if prefix:

                result = (
                    prefix
                    + " "
                    + current_clean
                )

            else:

                result = current_clean

            result = clean_text_field(result)

            if result:
                return (
                    result.upper(),
                    box.confidence,
                )

        return None, 0.0

    # =============================================================
    # UNLABELLED COURSE
    # =============================================================

    def _extract_unlabeled_course(self, boxes):

        for box in boxes:

            text = box.text.strip()

            # Example:
            #
            # 2025-2029 B TECH IT
            #
            # -> B TECH IT
            match = re.search(
                r"\b\d{4}\s*-\s*\d{4}\b\s+(.+)$",
                text,
                re.IGNORECASE,
            )

            if not match:
                continue

            candidate = match.group(1).strip()

            candidate = re.sub(
                r"\s+",
                " ",
                candidate,
            )

            if self._valid_course(candidate):

                return (
                    candidate.upper(),
                    box.confidence,
                )

        return None, 0.0

    # =============================================================
    # MONTH / YEAR
    # =============================================================

    @staticmethod
    def _normalize_month_year(value):

        value = value.strip()

        months = {
            "JANUARY": "01",
            "FEBRUARY": "02",
            "MARCH": "03",
            "APRIL": "04",
            "MAY": "05",
            "JUNE": "06",
            "JULY": "07",
            "AUGUST": "08",
            "SEPTEMBER": "09",
            "OCTOBER": "10",
            "NOVEMBER": "11",
            "DECEMBER": "12",
        }

        match = re.fullmatch(
            r"([A-Za-z]+)\s+(\d{4})",
            value,
        )

        if not match:
            return None

        month_name = match.group(1).upper()
        year = match.group(2)

        if month_name not in months:
            return None

        return f"{year}-{months[month_name]}-01"

    # =============================================================
    # VALIDATORS
    # =============================================================

    @staticmethod
    def _valid_id(value):

        value = value.strip()

        if not value:
            return False

        if not any(
            char.isdigit()
            for char in value
        ):
            return False

        # Reject standalone year.
        if re.fullmatch(
            r"(19|20)\d{2}",
            value,
        ):
            return False

        if not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9\-/]{2,20}",
            value,
        ):
            return False

        return True

    @staticmethod
    def _valid_passport(value):

        value = value.strip().replace(
            " ",
            "",
        )

        return bool(
            re.fullmatch(
                r"[A-Za-z][0-9]{7}",
                value,
            )
        )

    @staticmethod
    def _valid_date(value):

        return (
            normalize_date(value)
            is not None
        )

    @staticmethod
    def _valid_name(value):

        value = value.strip()

        if not value:
            return False

        if any(
            char.isdigit()
            for char in value
        ):
            return False

        normalized = (
            FieldExtractor._normalize_label(
                value
            )
        )

        rejected = {
            "BLOOD GROUP",
            "MOBILE",
            "MOBILE NO",
            "MOB NO",
            "MOB NO.",
            "ADDRESS",
            "DOB",
            "DATE OF BIRTH",
            "COLLEGE",
            "UNIVERSITY",
            "INSTITUTE",
            "COURSE",
            "STUDENT ID",
            "STUDENT NO",
            "ID NO",
            "REG NO",
            "CARD",
            "REGISTRAR",
        }

        if normalized in rejected:
            return False

        words = value.split()

        if len(words) < 2 or len(words) > 5:
            return False

        return all(
            re.fullmatch(
                r"[A-Za-z.'-]+",
                word,
            )
            for word in words
        )

    @staticmethod
    def _valid_text(value):

        value = value.strip()

        if not value:
            return False

        if len(value) < 2:
            return False

        normalized = (
            FieldExtractor._normalize_label(
                value
            )
        )

        labels = {
            "NAME",
            "DOB",
            "DATE OF BIRTH",
            "COLLEGE",
            "COURSE",
            "BRANCH",
            "PROGRAM",
            "PROGRAMME",
            "EXPIRY",
            "VALID TILL",
            "VALID UNTIL",
            "VALID UPTO",
            "STUDENT ID",
            "STUDENT NO",
            "ADDRESS",
            "BLOOD GROUP",
            "MOBILE",
            "MOBILE NO",
            "MOB NO",
            "REGISTRAR",
        }

        return normalized not in labels

    @staticmethod
    def _valid_course(value):

        value = value.strip()

        if not value:
            return False

        if not re.search(
            r"[A-Za-z]",
            value,
        ):
            return False

        rejected = {
            "REGISTRAR",
            "CARD",
            "VALID",
            "INSTITUTIONS",
        }

        normalized = (
            FieldExtractor._normalize_label(
                value
            )
        )

        if normalized in rejected:
            return False

        return True

    # =============================================================
    # LABEL HELPERS
    # =============================================================

    def _is_any_known_label(self, text):

        all_keywords = (
            self.STUDENT_ID_KEYWORDS
            + self.NAME_KEYWORDS
            + self.DOB_KEYWORDS
            + self.COLLEGE_KEYWORDS
            + self.COURSE_KEYWORDS
            + self.VALIDITY_KEYWORDS
            + self.PASSPORT_KEYWORDS
            + self.NATIONALITY_KEYWORDS
            + self.VISA_KEYWORDS
        )

        normalized_keywords = {
            self._normalize_label(
                keyword
            )
            for keyword in all_keywords
        }

        return text in normalized_keywords

    # =============================================================
    # NORMALIZATION
    # =============================================================

    @staticmethod
    def _normalize_label(text):

        text = text.upper().strip()

        text = re.sub(
            r"[.:]+",
            " ",
            text,
        )

        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # =============================================================
    # BOUNDING BOX
    # =============================================================

    @staticmethod
    def _box_bounds(box):

        xs = [
            point[0]
            for point in box.box
        ]

        ys = [
            point[1]
            for point in box.box
        ]

        return (
            min(xs),
            min(ys),
            max(xs),
            max(ys),
        )