"""
ai/ocr/ocr_pipeline.py
----------------------
Core PaddleOCR pipeline implementation for PaddleOCR 2.9.1.
Loads model lazily (singleton pattern), executes text detection/recognition,
runs field extraction, and compiles output schema.
"""

import os
import logging
from typing import Optional, Dict, Any, List, Union
import numpy as np

from .preprocessing import preprocess_image
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
                use_gpu=False,
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

        # 1. Preprocess image
        original_img, preprocessed_img = preprocess_image(image_path)

        # 2. Execute PaddleOCR with defensive result parsing
        raw_boxes: List[BoundingBox] = []
        if self._ocr_engine is not None:
            try:
                # Run OCR on preprocessed image
                ocr_output = self._ocr_engine.ocr(preprocessed_img, cls=True)

                # Fallback to original image if preprocessed yields no text
                if not ocr_output or ocr_output[0] is None:
                    ocr_output = self._ocr_engine.ocr(original_img, cls=True)

                # Defensive check: verify ocr_output and ocr_output[0] are non-empty
                if ocr_output and ocr_output[0] is not None and isinstance(ocr_output[0], list):
                    for line in ocr_output[0]:
                        if not line or len(line) < 2:
                            continue
                        box_coords = line[0]  # [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]
                        text_val, conf_val = line[1]  # ("TEXT", 0.98)

                        raw_boxes.append(BoundingBox(
                            text=str(text_val).strip(),
                            confidence=float(conf_val),
                            box=[[float(pt[0]), float(pt[1])] for pt in box_coords]
                        ))
            except Exception as exc:
                logger.error("Error during PaddleOCR inference on image '%s': %s", image_path, exc)

        # 3. Concatenate raw text
        raw_text_parts = [b.text for b in raw_boxes]
        full_raw_text = "\n".join(raw_text_parts)

        # 4. Extract structured fields
        extractor = FieldExtractor()
        extracted_fields, field_scores = extractor.extract_fields(raw_boxes, full_raw_text)

        # 5. Compute overall confidence score
        overall_confidence = 0.0
        if raw_boxes:
            overall_confidence = float(np.mean([b.confidence for b in raw_boxes]))

        confidence_obj = ConfidenceScores(
            overall=round(overall_confidence, 4),
            field_scores={k: round(v, 4) for k, v in field_scores.items()}
        )

        return OCRResult(
            raw_text=full_raw_text,
            fields=extracted_fields,
            confidence=confidence_obj,
            bounding_boxes=raw_boxes
        )


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

