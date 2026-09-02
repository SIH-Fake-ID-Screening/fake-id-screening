"""
schemas/screening.py
--------------------
Pydantic response schemas for the document screening API.
"""

from pydantic import BaseModel, Field


class ScreeningUploadResponse(BaseModel):
    """
    Returned by POST /api/v1/screen after successful file upload.

    Fields
    ------
    screening_id     : UUID string uniquely identifying this screening session.
    status           : Current pipeline status. "uploaded" at this stage.
    document_front_file: Saved filename of the document's front image.
    document_back_file : Saved filename of the document's back image.
    live_photo_file    : Saved filename of the live/person photo.
    message            : Human-readable result message.
    face_verification: Result of the face verification check (match, confidence).
    """

    screening_id: str = Field(
        ...,
        description="UUID identifying this screening session.",
        examples=["3fa85f64-5717-4562-b3fc-2c963f66afa6"],
    )
    status: str = Field(
        default="uploaded",
        description="Pipeline status at this stage.",
        examples=["uploaded"],
    )
    document_front_file: str = Field(
        ...,
        description="Stored filename (no path) of the document front image.",
        examples=["a1b2c3d4e5f6_front.jpg"],
    )
    document_back_file: str = Field(
        ...,
        description="Stored filename (no path) of the document back image.",
        examples=["a1b2c3d4e5f6_back.jpg"],
    )
    live_photo_file: str = Field(
        ...,
        description="Stored filename (no path) of the live photo.",
        examples=["9f8e7d6c5b4a.jpg"],
    )
    message: str = Field(
        default="Files uploaded successfully",
        description="Human-readable status message.",
    )
    face_verification: dict | None = Field(
        default=None,
        description="Face verification result containing match status and confidence.",
        examples=[{"match": True, "confidence": 0.85}],
    )

    model_config = {"json_schema_extra": {
        "example": {
            "screening_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "uploaded",
            "document_front_file": "a1b2c3d4e5f6_front.jpg",
            "document_back_file": "a1b2c3d4e5f6_back.jpg",
            "live_photo_file": "9f8e7d6c5b4a.jpg",
            "message": "Files uploaded successfully",
            "face_verification": {"match": True, "confidence": 0.85},
        }
    }}


class ErrorResponse(BaseModel):
    """Generic error response body."""

    detail: str = Field(..., description="Error description.")


from datetime import date

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
