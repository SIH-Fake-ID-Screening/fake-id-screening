"""
schemas/screening.py
--------------------
Pydantic response schemas for the document screening API.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Sub-schemas used in the main ScreeningResponse
# ---------------------------------------------------------------------------

class StudentSummary(BaseModel):
    """Subset of student fields returned in a screening response."""

    student_id: str = Field(..., description="College-issued student ID.")
    name: str = Field(..., description="Full name as stored in the database.")
    course: Optional[str] = Field(None, description="Programme / branch of study.")
    college: Optional[str] = Field(None, description="Issuing institution.")
    dob: Optional[str] = Field(None, description="Date of birth from the database.")
    valid_till: Optional[str] = Field(None, description="Expiry date from the database.")
    status: str = Field(..., description="Account status: active | expired | suspended.")
    blacklisted: bool = Field(..., description="True if the student is blacklisted.")


class FaceVerificationResult(BaseModel):
    """Result of the face comparison step."""

    match: bool = Field(..., description="True if reference face matches live photo.")
    confidence: float = Field(
        ...,
        description="Cosine similarity score between embeddings (0.0–1.0).",
        examples=[0.85],
    )


# ---------------------------------------------------------------------------
# Primary response schema for POST /api/v1/screen
# ---------------------------------------------------------------------------

class ScreeningResponse(BaseModel):
    """
    Returned by POST /api/v1/screen after the full screening pipeline completes.

    Status values
    -------------
    completed              : All checks passed and face verification ran.
    student_not_found      : OCR returned an ID not present in the database.
    student_blacklisted    : Student is blacklisted — face check skipped.
    student_inactive       : Student status is not "active" — face check skipped.
    reference_image_missing: DB record has no front_image_path — face check skipped.
    face_not_detected      : InsightFace could not find a face in one of the images.
    face_mismatch          : Face verification ran but match is False.
    error                  : Unexpected internal error.
    """

    screening_id: str = Field(
        ...,
        description="UUID identifying this screening session.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    status: str = Field(
        ...,
        description="Pipeline outcome status.",
        examples=["completed", "student_not_found", "student_blacklisted"],
    )
    student: Optional[StudentSummary] = Field(
        default=None,
        description="Student record from the database (None if not found).",
    )
    face_verification: Optional[FaceVerificationResult] = Field(
        default=None,
        description="Face verification result (None if check was skipped or failed).",
    )
    message: str = Field(
        ...,
        description="Human-readable description of the outcome.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "screening_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
                "status": "completed",
                "student": {
                    "student_id": "202501100600212",
                    "name": "Priyanshu Ranjan",
                    "course": "B.Tech IT",
                    "college": "KIET Group of Institutions",
                    "status": "active",
                    "blacklisted": False,
                },
                "face_verification": {"match": True, "confidence": 0.87},
                "message": "Face verification completed.",
            }
        }
    }


# ---------------------------------------------------------------------------
# Error response (unchanged)
# ---------------------------------------------------------------------------

class ErrorResponse(BaseModel):
    """Generic error response body."""

    detail: str = Field(..., description="Error description.")


# ---------------------------------------------------------------------------
# Legacy upload-only response — kept for backward compatibility
# ---------------------------------------------------------------------------

class ScreeningUploadResponse(BaseModel):
    """
    Legacy schema — kept for backward compatibility.
    New code should use ScreeningResponse instead.
    """

    screening_id: str = Field(..., description="UUID identifying this screening session.")
    status: str = Field(default="uploaded", description="Pipeline status at this stage.")
    document_front_file: str = Field(..., description="Stored filename of the document front image.")
    document_back_file: str = Field(..., description="Stored filename of the document back image.")
    live_photo_file: str = Field(..., description="Stored filename of the live photo.")
    message: str = Field(default="Files uploaded successfully", description="Human-readable status message.")
    face_verification: dict | None = Field(
        default=None,
        description="Face verification result containing match status and confidence.",
    )

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Full student record schema (used elsewhere)
# ---------------------------------------------------------------------------

class StudentResponse(BaseModel):
    """Student data response model."""

    student_id: str
    name: str
    dob: date | None
    college: str | None
    course: str | None
    valid_till: date | None
    front_image_path: str | None
    back_image_path: str | None
    status: str
    blacklisted: bool

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Database record schemas (GET /api/v1/screenings)
# ---------------------------------------------------------------------------

from datetime import datetime

class ScreeningRecordSchema(BaseModel):
    """Full screening record from the database."""
    screening_id: str
    student_id: Optional[str] = None
    status: str
    risk_score: Optional[float] = None
    risk_level: Optional[str] = None
    ocr_result: Optional[dict] = None
    db_verification_result: Optional[dict] = None
    face_result: Optional[dict] = None
    tampering_result: Optional[dict] = None
    validation_issues: Optional[dict] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class PaginatedScreeningResponse(BaseModel):
    """Paginated list of screenings."""
    items: list[ScreeningRecordSchema]
    total: int
    limit: int
    offset: int


class StatsSummaryResponse(BaseModel):
    """Summary of screening statistics."""
    total: int
    verified: int
    suspicious: int
    rejected: int


class TrendDataPoint(BaseModel):
    date: str
    count: int

class StatsTrendResponse(BaseModel):
    """7-day trend of screenings."""
    data: list[TrendDataPoint]
