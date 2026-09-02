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
    document_file    : Saved filename of the document/ID card image.
    live_photo_file  : Saved filename of the live/person photo.
    message          : Human-readable result message.
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
    document_file: str = Field(
        ...,
        description="Stored filename (no path) of the document image.",
        examples=["a1b2c3d4e5f6.jpg"],
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

    model_config = {"json_schema_extra": {
        "example": {
            "screening_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
            "status": "uploaded",
            "document_file": "a1b2c3d4e5f6.jpg",
            "live_photo_file": "9f8e7d6c5b4a.jpg",
            "message": "Files uploaded successfully",
        }
    }}


class ErrorResponse(BaseModel):
    """Generic error response body."""

    detail: str = Field(..., description="Error description.")
