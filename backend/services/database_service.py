"""
services/database_service.py
-----------------------------
Database service layer for student record lookups.

Architecture note
-----------------
This module is the single point of contact between the screening pipeline
and the students table. OCR and face-verification services must never
import from database.models directly.

Separation of responsibilities
-------------------------------
  OCR service      → extract_document()        (this module is NOT called here)
  Database service → get_student_by_id()       ← you are here
  Face service     → verify_faces()            (this module is NOT called here)

The pipeline in api/screening.py orchestrates all three in sequence.
"""

import logging
from sqlalchemy.orm import Session

from database.models import Student
from database.models import get_student_by_id as _db_get_student_by_id

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def get_student_by_id(db: Session, student_id: str) -> Student | None:
    """
    Look up a student record by their college-issued ID.

    Parameters
    ----------
    db         : Active SQLAlchemy session (injected via FastAPI's Depends(get_db)).
    student_id : The college-issued student ID string extracted by OCR.

    Returns
    -------
    Student ORM object if found, None otherwise.

    The caller (screening pipeline) is responsible for checking:
        • student is not None          → student_not_found
        • student.blacklisted is False → student_blacklisted
        • student.status == "active"   → student_inactive
        • student.front_image_path     → reference_image_missing
    """
    logger.info("DB lookup: student_id=%r", student_id)

    student = _db_get_student_by_id(db, student_id)

    if student is None:
        logger.warning("DB lookup: student_id=%r NOT FOUND", student_id)
    else:
        logger.info(
            "DB lookup: found student name=%r status=%r blacklisted=%s",
            student.name,
            student.status,
            student.blacklisted,
        )

    return student
