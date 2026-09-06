"""
ai/ocr/ocr_pipeline.py
----------------------
Core PaddleOCR pipeline implementation for PaddleOCR 2.9.1.
Loads model lazily (singleton pattern), executes multi-pass text detection/recognition,
runs field extraction, and compiles output schema.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union
import numpy as np

from .preprocessing import preprocess_image, crop_bottom_id_roi
from .field_extractor import FieldExtractor
from .schemas import OCRResult, ExtractedFields, ConfidenceScores, BoundingBox

logger = logging.getLogger(__name__)


class OCRProcessor:
    """Singleton PaddleOCR 2.9.1 wrapper and field extraction processor."""

    _instance: Optional["OCRProcessor"] = None
    _ocr_engine = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(OCRProcessor, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        """Initialize PaddleOCR 2.9.1 engine lazily with approved parameters."""
        try:
            from paddleocr import PaddleOCR
            logger.info("Initializing PaddleOCR 2.9.1 engine (ocr_version='PP-OCRv4', lang='en', use_gpu=False)...")
            self._ocr_engine = PaddleOCR(
                ocr_version="PP-OCRv4",
                lang="en",
                use_angle_cls=True,
                show_log=False
            )
            logger.info("PaddleOCR engine initialized successfully.")
        except Exception as exc:
            logger.warning("PaddleOCR engine failed to initialize: %s", exc)
            self._ocr_engine = None

    def process_image(self, image_path: str) -> OCRResult:
        """
        Process a document image file and return structured OCR output.

        Parameters
        ----------
        image_path : str
            Path to the document image file on disk.

        Returns
        -------
        OCRResult : Model containing raw text, extracted fields, confidence, bounding boxes.
        """
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Image path does not exist: {image_path}")

        # 1. Preprocess image & ROI crop
        original_img, preprocessed_img = preprocess_image(image_path)
        roi_img = crop_bottom_id_roi(original_img)

        # 2. Execute PaddleOCR multi-pass detection
        raw_boxes: List[BoundingBox] = []
        seen_texts = set()

        if self._ocr_engine is not None:
            # Pass A: Preprocessed image
            self._run_ocr_pass(preprocessed_img, raw_boxes, seen_texts)

            # Pass B: Original image if preprocessed yields few boxes
            if len(raw_boxes) < 3:
                self._run_ocr_pass(original_img, raw_boxes, seen_texts)

            # Pass C: Bottom ROI cropped image for high-precision digit recognition
            if roi_img is not None:
                self._run_ocr_pass(roi_img, raw_boxes, seen_texts)

        # 3. Concatenate raw text
        raw_text_parts = [b.text for b in raw_boxes]
        full_raw_text = "\n".join(raw_text_parts)

        # 4. Extract structured fields
        extractor = FieldExtractor()
        extracted_fields, field_scores = extractor.extract_fields(raw_boxes, full_raw_text)

        return OCRResult(
            student_id=extracted_fields.student_id,
            name=extracted_fields.name,
            dob=extracted_fields.dob,
            course=extracted_fields.course,
            college=extracted_fields.college,
            valid_till=extracted_fields.valid_till,
            raw_text=full_raw_text,
            confidence=field_scores,
            bounding_boxes=raw_boxes
        )

    def _run_ocr_pass(self, img_np: np.ndarray, raw_boxes: List[BoundingBox], seen_texts: set):
        """Execute single OCR pass and append unique detected text blocks."""
        try:
            ocr_output = self._ocr_engine.ocr(img_np, cls=True)
            if ocr_output and ocr_output[0] is not None and isinstance(ocr_output[0], list):
                for line in ocr_output[0]:
                    if not line or len(line) < 2:
                        continue
                    box_coords = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                    text_val, conf_val = line[1]  # ("TEXT", 0.98)
                    clean_text = str(text_val).strip()

                    if clean_text and clean_text not in seen_texts:
                        seen_texts.add(clean_text)
                        raw_boxes.append(BoundingBox(
                            text=clean_text,
                            confidence=float(conf_val),
                            box=[[float(pt[0]), float(pt[1])] for pt in box_coords]
                        ))
        except Exception as exc:
            logger.error("Error during OCR pass: %s", exc)


def _to_contract_dict(fields) -> Dict[str, str]:
    """
    Map ExtractedFields to the public OCR output contract.

    Contract:
      { student_id, name, dob, course, valid_till }

    All missing values are returned as "" (empty string), never None.
    """
    def _str(val) -> str:
        return val if val is not None else ""

    return {
        "student_id": _str(fields.student_id),
        "name":       _str(fields.name),
        "dob":        _str(fields.dob),
        "course":     _str(fields.course),
        "valid_till": _str(fields.valid_till),
    }


def extract_document(image_path: Union[str, List[str]]) -> Dict[str, str]:
    """
    Public OCR interface.

    Accepts a single image path or a list of paths (e.g. front and back sides of an ID card).
    Processes image(s) and returns strictly the OCR contract dictionary:

    {
        "student_id": "...",   # "" if not found
        "name":       "...",   # "" if not found
        "dob":        "...",   # YYYY-MM-DD or "" if not found
        "course":     "...",   # "" if not found
        "valid_till": "...",   # YYYY-MM-DD / YYYY-MM-01 or "" if not found
    }

    DOB and valid_till are always strictly independent fields.
    """
    if isinstance(image_path, (list, tuple)):
        combined = {
            "student_id": "",
            "name": "",
            "dob": "",
            "course": "",
            "valid_till": "",
        }
        for path in image_path:
            res = extract_document(path)
            for k in combined:
                if not combined[k] and res.get(k):
                    combined[k] = res[k]
        return combined

    processor = OCRProcessor()
    result = processor.process_image(image_path)
    return _to_contract_dict(result.fields)


# Backward-compatible alias
extract_ocr_data = extract_document

