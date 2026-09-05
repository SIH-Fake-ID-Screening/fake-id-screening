"""
api/screening.py
----------------
POST /api/v1/screen

Full screening pipeline:

    Upload (document_front + document_back + live_photo)
                    ↓
            Validate & save files
                    ↓
            OCR placeholder (ocr_service.extract_document)
                    ↓
            Extract student_id
                    ↓
            Database lookup (database_service.get_student_by_id)
                    ↓
        ┌── student_not_found ──────────────────────────────────────┐
        │   student_blacklisted                                     │
        │   student_inactive                                        │
        │   reference_image_missing                                 │
        └───────────────────────────────────────────────────────────┘
                    ↓ (all checks passed)
            Resolve trusted front_image_path from database
                    ↓
            Face verification
              TRUSTED: database.front_image_path
              UNTRUSTED: uploaded live_photo
                    ↓
            Return ScreeningResponse

SECURITY CONTRACT
-----------------
  UNTRUSTED inputs  : document_front, document_back, live_photo
  TRUSTED reference : database.Student.front_image_path

  The uploaded document images are NEVER passed to verify_faces().
  Only the database-sourced reference image is used as the face reference.
"""

import uuid
import logging
from pathlib import Path
from datetime import datetime, timedelta

from sqlalchemy import cast, Date, func

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database.connection import get_db
from schemas.screening import (
    ErrorResponse, ScreeningResponse,
    PaginatedScreeningResponse, ScreeningRecordSchema,
    StatsSummaryResponse, StatsTrendResponse
)
from utils.file_handler import validate_and_save, UPLOAD_DIR, delete_file
from services import ocr_service, database_service, face_service
from database.models import Screening

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["Screening"])

def _save_and_return(db: Session, response: ScreeningResponse, ocr_result: dict = None) -> ScreeningResponse:
    try:
        risk_score = 10.0 if response.status == "completed" else 85.0
        risk_level = "Low" if response.status == "completed" else "High"
        
        db_rec = Screening(
            screening_id=response.screening_id,
            student_id=response.student.student_id if response.student else None,
            status=response.status,
            risk_score=risk_score,
            risk_level=risk_level,
            ocr_result=ocr_result,
            db_verification_result=response.student.model_dump() if response.student else None,
            face_result=response.face_verification.model_dump() if response.face_verification else None,
            tampering_result=None,
            validation_issues={"message": response.message}
        )
        db.add(db_rec)
        db.commit()
    except Exception as e:
        logger.error(f"Failed to save screening result: {e}")
        db.rollback()
    return response

# ---------------------------------------------------------------------------

# Helper: resolve an absolute path for a DB-stored image path
# ---------------------------------------------------------------------------

def _resolve_db_image_path(db_path: str) -> str:
    """
    Convert a database-stored image path to an absolute filesystem path.

    The database stores paths relative to the backend/ directory
    (e.g. "uploads/students/202501100600212/front.jpeg").
    We resolve them against the backend root.
    """
    _BACKEND_DIR = Path(__file__).resolve().parent.parent
    resolved = (_BACKEND_DIR / db_path).resolve()
    return str(resolved)


# ---------------------------------------------------------------------------
# POST /api/v1/screen
# ---------------------------------------------------------------------------

@router.post(
    "/screen",
    response_model=ScreeningResponse,
    status_code=status.HTTP_200_OK,
    summary="Screen an ID card against the database",
    description=(
        "Accepts a document/ID card front image (`document_front`), "
        "a document/ID card back image (`document_back`), and a "
        "live/person photo (`live_photo`) as multipart/form-data. "
        "Runs the full screening pipeline: file validation → OCR → database "
        "lookup → status checks → face verification using the TRUSTED database "
        "reference image (never the uploaded document). "
        "Returns a structured result with student info and face match outcome."
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
    db: Session = Depends(get_db),
):
    """
    Full screening pipeline.

    Steps
    -----
    1.  Validate document_front (extension, MIME type, size, image content).
    2.  Validate document_back  (same checks).
    3.  Validate live_photo     (same checks).
    4.  Save all three files with UUID-based filenames.
    5.  OCR placeholder: extract student_id from document images.
    6.  Database lookup by student_id.
    7.  Reject if student not found.
    8.  Reject if student is blacklisted.
    9.  Reject if student status is not "active".
    10. Resolve trusted front_image_path from the database record.
    11. Reject if reference image file does not exist on disk.
    12. Face verification: database reference ↔ live photo.
    13. Return structured ScreeningResponse.
    14. Cleanup temporary upload files.

    SECURITY: document_front is NEVER passed to verify_faces().
    """
    screening_id = str(uuid.uuid4())
    logger.info("Screening session started [id=%s]", screening_id)

    # Track saved filenames for cleanup on failure.
    document_front_filename = None
    document_back_filename = None
    live_photo_filename = None

    try:
        # ------------------------------------------------------------------
        # STEP 1–4: Validate & save all three uploads
        # ------------------------------------------------------------------
        document_front_filename = await validate_and_save(
            document_front, field_label="document_front"
        )
        document_back_filename = await validate_and_save(
            document_back, field_label="document_back"
        )
        live_photo_filename = await validate_and_save(
            live_photo, field_label="live_photo"
        )

        # Absolute paths to the saved temporary files.
        # document_front_path and document_back_path are UNTRUSTED —
        # they are only passed to OCR, never to face verification.
        document_front_path = str(UPLOAD_DIR / document_front_filename)
        document_back_path  = str(UPLOAD_DIR / document_back_filename)
        live_photo_path     = str(UPLOAD_DIR / live_photo_filename)

        logger.info(
            "Files saved [id=%s] front=%s back=%s live=%s",
            screening_id,
            document_front_filename,
            document_back_filename,
            live_photo_filename,
        )

        # ------------------------------------------------------------------
        # STEP 5: OCR — extract student_id from the uploaded document.
        # document_front_path / document_back_path are UNTRUSTED here.
        # The OCR service reads text only; it does NOT produce a face reference.
        # ------------------------------------------------------------------
        ocr_result = ocr_service.extract_document(
            front_image_path=document_front_path,
            back_image_path=document_back_path,
        )
        student_id = ocr_result.get("student_id", "").strip()

        if not student_id:
            logger.warning("[id=%s] OCR returned no student_id", screening_id)
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="student_not_found",
                student=None,
                face_verification=None,
                message="OCR could not extract a student ID from the document.",
            ), ocr_result)

        # ------------------------------------------------------------------
        # STEP 6: Database lookup
        # ------------------------------------------------------------------
        student = database_service.get_student_by_id(db, student_id)

        # ------------------------------------------------------------------
        # STEP 7: Student existence check
        # ------------------------------------------------------------------
        if student is None:
            logger.warning(
                "[id=%s] student_id=%r not found in database", screening_id, student_id
            )
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="student_not_found",
                student=None,
                face_verification=None,
                message=f"No student record found for ID: {student_id}",
            ), ocr_result)

        student_summary = {
            "student_id": student.student_id,
            "name": student.name,
            "course": student.course,
            "college": student.college,
            "dob": str(student.dob) if student.dob else None,
            "valid_till": str(student.valid_till) if student.valid_till else None,
            "status": student.status,
            "blacklisted": student.blacklisted,
        }

        # ------------------------------------------------------------------
        # STEP 8: Blacklist check — face verification must NOT run
        # ------------------------------------------------------------------
        if student.blacklisted:
            logger.warning(
                "[id=%s] student_id=%r is BLACKLISTED", screening_id, student_id
            )
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="student_blacklisted",
                student=student_summary,
                face_verification=None,
                message=(
                    f"Student {student.name} ({student_id}) is blacklisted. "
                    "Access denied."
                ),
            ), ocr_result)

        # ------------------------------------------------------------------
        # STEP 9: Active status check — face verification must NOT run
        # ------------------------------------------------------------------
        if student.status != "active":
            logger.warning(
                "[id=%s] student_id=%r has status=%r (not active)",
                screening_id, student_id, student.status,
            )
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="student_inactive",
                student=student_summary,
                face_verification=None,
                message=(
                    f"Student account is not active (status: {student.status}). "
                    "Access denied."
                ),
            ), ocr_result)

        # ------------------------------------------------------------------
        # STEP 9a: DB Expiry check
        # ------------------------------------------------------------------
        if student.valid_till and student.valid_till < datetime.utcnow().date():
            logger.warning("[id=%s] student_id=%r account expired on %s", screening_id, student_id, student.valid_till)
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="expired",
                student=student_summary,
                face_verification=None,
                message="Student account has expired. Access denied."
            ), ocr_result)

        # ------------------------------------------------------------------
        # STEP 9b: OCR Expiry validation against DB
        # ------------------------------------------------------------------
        ocr_valid_till_str = ocr_result.get("valid_till")
        if not ocr_valid_till_str:
            logger.warning("[id=%s] OCR could not extract validity date", screening_id)
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="document_validation_failed",
                student=student_summary,
                face_verification=None,
                message="Could not extract validity date from the document."
            ), ocr_result)

        if student.valid_till:
            db_valid_till_str = str(student.valid_till)
            # If the normalizer resolved a month-year like "July 2029", it defaults the day to "01".
            # We compare just the YYYY-MM parts if OCR ends with "-01", otherwise exact match.
            is_match = False
            if ocr_valid_till_str.endswith("-01"):
                is_match = (ocr_valid_till_str[:7] == db_valid_till_str[:7])
            else:
                is_match = (ocr_valid_till_str == db_valid_till_str)

            if not is_match:
                logger.warning(
                    "[id=%s] Validity mismatch: OCR=%s, DB=%s",
                    screening_id, ocr_valid_till_str, db_valid_till_str
                )
                return _save_and_return(db, ScreeningResponse(
                    screening_id=screening_id,
                    status="document_validation_failed",
                    student=student_summary,
                    face_verification=None,
                    message=f"Document validity date mismatch (OCR: {ocr_valid_till_str}, DB: {db_valid_till_str})."
                ), ocr_result)

        # ------------------------------------------------------------------
        # STEP 10–11: Resolve TRUSTED reference image from the database.
        # This is the ONLY path that may be passed to verify_faces().
        # document_front_path is NEVER used as a face reference.
        # ------------------------------------------------------------------
        if not student.front_image_path:
            logger.error(
                "[id=%s] student_id=%r has no front_image_path in DB",
                screening_id, student_id,
            )
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="reference_image_missing",
                student=student_summary,
                face_verification=None,
                message=(
                    "No reference image found in the database for this student. "
                    "Cannot perform face verification."
                ),
            ), ocr_result)

        # Resolve the trusted reference path to an absolute path.
        trusted_reference_path = _resolve_db_image_path(student.front_image_path)

        if not Path(trusted_reference_path).exists():
            logger.error(
                "[id=%s] Trusted reference file not found on disk: %s",
                screening_id, trusted_reference_path,
            )
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="reference_image_missing",
                student=student_summary,
                face_verification=None,
                message=(
                    "Database reference image file is missing from the filesystem. "
                    "Cannot perform face verification."
                ),
            ), ocr_result)

        # ------------------------------------------------------------------
        # STEP 12: Face verification
        #
        #   TRUSTED  : trusted_reference_path  ← from database.front_image_path
        #   UNTRUSTED: live_photo_path          ← from user upload
        #
        #   document_front_path is NOT passed here.
        # ------------------------------------------------------------------
        logger.info(
            "[id=%s] Face verification: reference=%s  live=%s",
            screening_id, trusted_reference_path, live_photo_path,
        )

        try:
            face_result = face_service.verify_faces(
                reference_image_path=trusted_reference_path,
                live_image_path=live_photo_path,
            )
        except FileNotFoundError as exc:
            logger.error("[id=%s] Face verification image not found: %s", screening_id, exc)
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="reference_image_missing",
                student=student_summary,
                face_verification=None,
                message=str(exc),
            ), ocr_result)
        except ValueError as exc:
            # No face or multiple faces detected
            logger.warning("[id=%s] Face detection failed: %s", screening_id, exc)
            return _save_and_return(db, ScreeningResponse(
                screening_id=screening_id,
                status="face_not_detected",
                student=student_summary,
                face_verification=None,
                message=str(exc),
            ), ocr_result)
        except RuntimeError as exc:
            logger.error("[id=%s] Face service unavailable: %s", screening_id, exc)
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Face verification service is unavailable.",
            ) from exc

        # ------------------------------------------------------------------
        # STEP 13: Build final response
        # ------------------------------------------------------------------
        outcome_status = "completed" if face_result["match"] else "face_mismatch"

        logger.info(
            "Screening complete [id=%s] status=%s match=%s confidence=%.4f",
            screening_id,
            outcome_status,
            face_result["match"],
            face_result.get("confidence", 0.0),
        )

        return _save_and_return(db, ScreeningResponse(
            screening_id=screening_id,
            status=outcome_status,
            student=student_summary,
            face_verification={
                "match": face_result["match"],
                "confidence": face_result.get("confidence", 0.0),
            },
            message=(
                "Face verification completed. Identity confirmed."
                if face_result["match"]
                else "Face verification completed. Identity NOT confirmed (mismatch)."
            ),
        ), ocr_result)

    except HTTPException:
        # Re-raise validation errors (already have correct status codes).
        if document_front_filename:
            delete_file(document_front_filename)
        if document_back_filename:
            delete_file(document_back_filename)
        if live_photo_filename:
            delete_file(live_photo_filename)
        raise

    except Exception as exc:
        # Catch unexpected errors to avoid leaking internal details.
        if document_front_filename:
            delete_file(document_front_filename)
        if document_back_filename:
            delete_file(document_back_filename)
        if live_photo_filename:
            delete_file(live_photo_filename)
        logger.error(
            "Unexpected error [id=%s]: %s", screening_id, exc, exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        ) from exc

    finally:
        # ------------------------------------------------------------------
        # STEP 14: Always clean up temporary upload files.
        # These are the UNTRUSTED user-submitted images.
        # ------------------------------------------------------------------
        if document_front_filename:
            delete_file(document_front_filename)
        if document_back_filename:
            delete_file(document_back_filename)
        if live_photo_filename:
            delete_file(live_photo_filename)

# ---------------------------------------------------------------------------
# GET /api/v1/screenings
# ---------------------------------------------------------------------------

@router.get(
    "/screenings",
    response_model=PaginatedScreeningResponse,
    status_code=status.HTTP_200_OK,
    summary="Get all screenings",
)
def get_screenings(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    total = db.query(Screening).count()
    items = (
        db.query(Screening)
        .order_by(Screening.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


# ---------------------------------------------------------------------------
# GET /api/v1/screenings/{screening_id}
# ---------------------------------------------------------------------------

@router.get(
    "/screenings/{screening_id}",
    response_model=ScreeningRecordSchema,
    status_code=status.HTTP_200_OK,
    summary="Get a screening by ID",
)
def get_screening(
    screening_id: str,
    db: Session = Depends(get_db)
):
    try:
        uuid.UUID(screening_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid screening ID format")

    item = db.query(Screening).filter(Screening.screening_id == screening_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Screening not found")
    return item


# ---------------------------------------------------------------------------
# GET /api/v1/stats/summary
# ---------------------------------------------------------------------------

@router.get(
    "/stats/summary",
    response_model=StatsSummaryResponse,
    status_code=status.HTTP_200_OK,
    summary="Get summary statistics of screenings",
)
def get_stats_summary(db: Session = Depends(get_db)):
    try:
        total = db.query(Screening).count()
        if total == 0:
            return {"total": 0, "verified": 0, "suspicious": 0, "rejected": 0}

        # Status 'completed' means fully verified.
        verified = db.query(Screening).filter(Screening.status == "completed").count()

        # Statuses related to mismatch or undetected face represent suspicious attempts.
        suspicious = db.query(Screening).filter(
            Screening.status.in_(["face_mismatch", "face_not_detected"])
        ).count()

        # Anything else (student_not_found, student_blacklisted, student_inactive, reference_image_missing) is rejected.
        rejected = db.query(Screening).filter(
            Screening.status.notin_(["completed", "face_mismatch", "face_not_detected"])
        ).count()

        return {
            "total": total,
            "verified": verified,
            "suspicious": suspicious,
            "rejected": rejected
        }
    except Exception as exc:
        logger.error(f"Failed to fetch stats summary: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request."
        )


# ---------------------------------------------------------------------------
# GET /api/v1/stats/trend
# ---------------------------------------------------------------------------

@router.get(
    "/stats/trend",
    response_model=StatsTrendResponse,
    status_code=status.HTTP_200_OK,
    summary="Get 7-day screening trend",
)
def get_stats_trend(db: Session = Depends(get_db)):
    try:
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=6)

        results = (
            db.query(
                cast(Screening.created_at, Date).label("date"),
                func.count(Screening.id).label("count")
            )
            .filter(cast(Screening.created_at, Date) >= start_date)
            .filter(cast(Screening.created_at, Date) <= end_date)
            .group_by(cast(Screening.created_at, Date))
            .all()
        )

        counts_by_date = {str(r.date): r.count for r in results}

        trend_data = []
        for i in range(7):
            current_date = start_date + timedelta(days=i)
            date_str = current_date.strftime("%Y-%m-%d")
            trend_data.append({
                "date": date_str,
                "count": counts_by_date.get(date_str, 0)
            })

        return {"data": trend_data}
    except Exception as exc:
        logger.error(f"Failed to fetch stats trend: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request."
        )
