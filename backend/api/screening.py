"""
api/screening.py
----------------
POST /api/v1/screen

Accepts a document/ID card image and a live/person photo via
multipart/form-data, validates and saves them, then returns a
screening session ID for use in subsequent pipeline stages.

What this endpoint does NOT do (future phases):
  - OCR / text extraction
  - Face verification
  - Tampering detection
  - Risk scoring
  - Blockchain anchoring
"""

import uuid
import logging

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from schemas.screening import ErrorResponse, ScreeningUploadResponse
from utils.file_handler import validate_and_save

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Screening"])


@router.post(
    "/screen",
    response_model=ScreeningUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload document and live photo for screening",
    description=(
        "Accepts a document/ID card image (`document_image`) and a "
        "live/person photo (`live_photo`) as multipart/form-data. "
        "Both files must be JPG or PNG and must not exceed 10 MB each. "
        "Returns a `screening_id` to track this session through the pipeline."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or empty file"},
        413: {"model": ErrorResponse, "description": "File exceeds 10 MB"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
async def screen_document(
    document_image: UploadFile = File(
        ...,
        description="ID card / document image. JPG or PNG, max 10 MB.",
    ),
    live_photo: UploadFile = File(
        ...,
        description="Live photo of the person. JPG or PNG, max 10 MB.",
    ),
):
    """
    Upload and validate the two images required for a screening session.

    Steps
    -----
    1. Validate document_image (extension, MIME type, size, image content).
    2. Validate live_photo (same checks).
    3. Save both files with UUID-based filenames.
    4. Return a screening_id and the saved filenames.

    If either file is invalid, no file is saved and the appropriate
    4xx error is returned immediately.
    """
    screening_id = str(uuid.uuid4())

    try:
        # --- Validate & save document image ---
        document_filename = await validate_and_save(
            document_image, field_label="document_image"
        )

        # --- Validate & save live photo ---
        live_photo_filename = await validate_and_save(
            live_photo, field_label="live_photo"
        )

    except HTTPException:
        # Re-raise validation errors directly (already have correct status codes)
        raise

    except Exception as exc:
        # Catch any unexpected error to avoid leaking internal details
        logger.error("Unexpected error during file upload [screening_id=%s]", screening_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the files.",
        ) from exc

    logger.info(
        "Screening upload OK [id=%s] doc=%s live=%s",
        screening_id,
        document_filename,
        live_photo_filename,
    )

    return ScreeningUploadResponse(
        screening_id=screening_id,
        status="uploaded",
        document_file=document_filename,
        live_photo_file=live_photo_filename,
        message="Files uploaded successfully",
    )
