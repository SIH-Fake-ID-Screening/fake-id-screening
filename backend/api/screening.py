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
from utils.file_handler import validate_and_save, UPLOAD_DIR, delete_file

logger = logging.getLogger(__name__)

import sys
from pathlib import Path

# Add project root to sys.path to import from ai/
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

try:
    from ai.face.face_verification import FaceVerifier
    face_verifier = FaceVerifier()
except Exception as e:
    logger.error("Failed to initialize FaceVerifier: %s", e)
    face_verifier = None

router = APIRouter(prefix="/api/v1", tags=["Screening"])


@router.post(
    "/screen",
    response_model=ScreeningUploadResponse,
    status_code=status.HTTP_200_OK,
    summary="Upload document and live photo for screening",
    description=(
        "Accepts a document/ID card front image (`document_front`), "
        "a document/ID card back image (`document_back`), and a "
        "live/person photo (`live_photo`) as multipart/form-data. "
        "All files must be JPG or PNG and must not exceed 10 MB each. "
        "Returns a `screening_id` to track this session through the pipeline."
    ),
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or empty file"},
        413: {"model": ErrorResponse, "description": "File exceeds 10 MB"},
        500: {"model": ErrorResponse, "description": "Unexpected server error"},
    },
)
async def screen_document(
    document_front: UploadFile = File(
        ...,
        description="ID card / document front image. JPG or PNG, max 10 MB.",
    ),
    document_back: UploadFile = File(
        ...,
        description="ID card / document back image. JPG or PNG, max 10 MB.",
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
    1. Validate document_front (extension, MIME type, size, image content).
    2. Validate document_back (same checks).
    3. Validate live_photo (same checks).
    4. Save all files with UUID-based filenames.
    5. Return a screening_id and the saved filenames.

    8. CLEANUP
    If any step fails, we delete any files saved during this request.
    """
    screening_id = str(uuid.uuid4())
    
    document_front_filename = None
    document_back_filename = None
    live_photo_filename = None

    try:
        # --- Validate & save document front image ---
        document_front_filename = await validate_and_save(
            document_front, field_label="document_front"
        )

        # --- Validate & save document back image ---
        document_back_filename = await validate_and_save(
            document_back, field_label="document_back"
        )

        # --- Validate & save live photo ---
        live_photo_filename = await validate_and_save(
            live_photo, field_label="live_photo"
        )
        
        # --- Face Verification ---
        face_verification_result = None
        if face_verifier:
            try:
                doc_path = str(UPLOAD_DIR / document_front_filename)
                live_path = str(UPLOAD_DIR / live_photo_filename)
                face_verification_result = face_verifier.verify_faces(doc_path, live_path)
            except Exception as e:
                logger.error("Face verification failed: %s", e)
                face_verification_result = {"match": False, "confidence": 0.0, "error": str(e)}

    except HTTPException:
        # Cleanup files on validation failure
        if document_front_filename: delete_file(document_front_filename)
        if document_back_filename: delete_file(document_back_filename)
        if live_photo_filename: delete_file(live_photo_filename)
        # Re-raise validation errors directly (already have correct status codes)
        raise

    except Exception as exc:
        # Cleanup files on unexpected failure
        if document_front_filename: delete_file(document_front_filename)
        if document_back_filename: delete_file(document_back_filename)
        if live_photo_filename: delete_file(live_photo_filename)
        # Catch any unexpected error to avoid leaking internal details
        logger.error("Unexpected error during file upload [screening_id=%s]", screening_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the files.",
        ) from exc

    logger.info(
        "Screening upload OK [id=%s] doc_front=%s doc_back=%s live=%s",
        screening_id,
        document_front_filename,
        document_back_filename,
        live_photo_filename,
    )

    return ScreeningUploadResponse(
        screening_id=screening_id,
        status="uploaded",
        document_front_file=document_front_filename,
        document_back_file=document_back_filename,
        live_photo_file=live_photo_filename,
        message="Files uploaded successfully",
        face_verification=face_verification_result,
    )
