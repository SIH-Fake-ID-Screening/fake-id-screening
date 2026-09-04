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
        Matches backend/database models (Student model fields) and downstream pipelines.
        """
        student_id: Optional[str] = Field(default=None, description="College-issued student ID or card identifier")
        name: Optional[str] = Field(default=None, description="Full name of cardholder")
        dob: Optional[str] = Field(default=None, description="Date of birth in YYYY-MM-DD format")
        college: Optional[str] = Field(default=None, description="Issuing college/institution name")
        course: Optional[str] = Field(default=None, description="Degree or branch of study")
        valid_till: Optional[str] = Field(default=None, description="Expiry/validity date in YYYY-MM-DD format")
        document_number: Optional[str] = Field(default=None, description="Generic document or card number")
        expiry_date: Optional[str] = Field(default=None, description="Same as valid_till in YYYY-MM-DD format")

    class ConfidenceScores(BaseModel):
        """Overall and per-field OCR confidence metrics."""
        overall: float = Field(default=0.0, description="Average OCR confidence across all detected text regions")
        field_scores: Dict[str, float] = Field(default_factory=dict, description="Confidence per extracted field")

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
        raw_text: str = Field(default="", description="Complete concatenated raw text extracted from image")
        fields: ExtractedFields = Field(default_factory=ExtractedFields, description="Extracted & normalized document fields")
        confidence: ConfidenceScores = Field(default_factory=ConfidenceScores, description="OCR confidence metrics")
        bounding_boxes: List[BoundingBox] = Field(default_factory=list, description="All detected text bounding boxes")

        def to_dict(self) -> Dict[str, Any]:
            """Convert schema to dictionary representation."""
            return self.model_dump()

else:
    @dataclass
    class ExtractedFields:
        student_id: Optional[str] = None
        name: Optional[str] = None
        dob: Optional[str] = None
        college: Optional[str] = None
        course: Optional[str] = None
        valid_till: Optional[str] = None
        document_number: Optional[str] = None
        expiry_date: Optional[str] = None

    @dataclass
    class ConfidenceScores:
        overall: float = 0.0
        field_scores: Dict[str, float] = field(default_factory=dict)

    @dataclass
    class BoundingBox:
        text: str
        confidence: float
        box: List[List[float]]

    @dataclass
    class OCRResult:
        raw_text: str = ""
        fields: ExtractedFields = field(default_factory=ExtractedFields)
        confidence: ConfidenceScores = field(default_factory=ConfidenceScores)
        bounding_boxes: List[BoundingBox] = field(default_factory=list)

        def to_dict(self) -> Dict[str, Any]:
            return asdict(self)
