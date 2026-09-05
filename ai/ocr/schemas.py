"""
ai/ocr/schemas.py
-----------------
Pydantic data schemas for OCR extraction and normalization results.
Includes dataclass fallback for minimal environments where pydantic is not yet installed.
"""

from typing import Dict, List, Optional, Any

try:
    from pydantic import BaseModel, Field
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    from dataclasses import dataclass, field, asdict


if HAS_PYDANTIC:
    class ExtractedFields(BaseModel):
        """
        Standardized key-value fields extracted from the college ID/document image.
        Matches project OCR output contract.
        """
        student_id: str = Field(default="", description="12-16 digit college-issued student ID or card identifier")
        name: str = Field(default="", description="Full name of cardholder")
        dob: str = Field(default="", description="Date of birth in YYYY-MM-DD format")
        course: str = Field(default="", description="Degree or branch of study (e.g. B TECH IT)")
        college: str = Field(default="", description="Issuing college/institution name (e.g. KIET Group of Institutions)")
        valid_till: str = Field(default="", description="Expiry/validity date in YYYY-MM-DD format")

    class ConfidenceScores(BaseModel):
        """Per-field OCR confidence metrics."""
        student_id: float = Field(default=0.0, description="Confidence score for student_id")
        name: float = Field(default=0.0, description="Confidence score for name")
        dob: float = Field(default=0.0, description="Confidence score for dob")
        course: float = Field(default=0.0, description="Confidence score for course")
        college: float = Field(default=0.0, description="Confidence score for college")
        valid_till: float = Field(default=0.0, description="Confidence score for valid_till")

    class BoundingBox(BaseModel):
        """Single OCR text bounding box detection result."""
        text: str = Field(..., description="Recognized text string")
        confidence: float = Field(..., description="Recognition confidence (0.0 to 1.0)")
        box: List[List[float]] = Field(..., description="Bounding box polygon [[x1, y1], [x2, y2], [x3, y3], [x4, y4]]")

    class OCRResult(BaseModel):
        """
        Structured output returned by the OCR / Field Extraction engine.
        Passed downstream to validation, database, face, and risk services.
        """
        student_id: str = Field(default="")
        name: str = Field(default="")
        dob: str = Field(default="")
        course: str = Field(default="")
        college: str = Field(default="")
        valid_till: str = Field(default="")
        raw_text: str = Field(default="")
        confidence: ConfidenceScores = Field(default_factory=ConfidenceScores)
        bounding_boxes: List[BoundingBox] = Field(default_factory=list)

        def to_dict(self) -> Dict[str, Any]:
            """Convert schema to exact dictionary representation required by contract."""
            d = self.model_dump()
            return {
                "student_id": d["student_id"],
                "name": d["name"],
                "dob": d["dob"],
                "course": d["course"],
                "college": d["college"],
                "valid_till": d["valid_till"],
                "raw_text": d["raw_text"],
                "confidence": d["confidence"],
                "bounding_boxes": d["bounding_boxes"]
            }

else:
    @dataclass
    class ExtractedFields:
        student_id: str = ""
        name: str = ""
        dob: str = ""
        course: str = ""
        college: str = ""
        valid_till: str = ""

    @dataclass
    class ConfidenceScores:
        student_id: float = 0.0
        name: float = 0.0
        dob: float = 0.0
        course: float = 0.0
        college: float = 0.0
        valid_till: float = 0.0

    @dataclass
    class BoundingBox:
        text: str
        confidence: float
        box: List[List[float]]

    @dataclass
    class OCRResult:
        student_id: str = ""
        name: str = ""
        dob: str = ""
        course: str = ""
        college: str = ""
        valid_till: str = ""
        raw_text: str = ""
        confidence: ConfidenceScores = field(default_factory=ConfidenceScores)
        bounding_boxes: List[BoundingBox] = field(default_factory=list)

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)
