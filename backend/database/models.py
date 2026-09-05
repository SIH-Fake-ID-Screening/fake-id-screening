"""
database/models.py
------------------
SQLAlchemy ORM model for the `students` table.

Each row represents one authorized / genuine college ID card.
front_image_path and back_image_path store only the filesystem path to the student's photo;
no binary image data is kept in the database.
"""

from datetime import date, datetime
from sqlalchemy import Boolean, Column, Date, DateTime, String, Text, Float as db_Float
from sqlalchemy.dialects.postgresql import UUID, JSONB as db_JSONB
import uuid

from database.connection import Base


class Student(Base):
    """
    Represents a trusted / reference student ID card record.

    Fields
    ------
    id          : Internal UUID primary key (auto-generated).
    student_id  : Official college-issued ID (must be unique).
    name        : Full name as printed on the ID card.
    dob         : Date of birth.
    college     : Name of the issuing college / institution.
    course      : Programme / branch of study.
    valid_till  : Expiry date printed on the ID card.
    front_image_path: Relative or absolute path to the student's front ID photo on disk.
    back_image_path : Relative or absolute path to the student's back ID photo on disk.
    status      : Current status, e.g. "active", "expired", "suspended".
    blacklisted : True if the student has been blacklisted.
    created_at  : Row creation timestamp (set automatically).
    updated_at  : Row last-updated timestamp (updated automatically).
    """

    __tablename__ = "students"

    # Primary key — UUID keeps IDs opaque and collision-safe across environments.
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
    )

    # Unique college-issued identifier (the value printed on the physical card).
    student_id = Column(String(100), unique=True, nullable=False, index=True)

    # Personal / card details
    name = Column(String(255), nullable=False)
    dob = Column(Date, nullable=True)
    college = Column(String(255), nullable=True)
    course = Column(String(255), nullable=True)
    valid_till = Column(Date, nullable=True)

    # Paths to the reference photos stored on the filesystem (not inside the DB).
    front_image_path = Column(Text, nullable=True)
    back_image_path = Column(Text, nullable=True)

    # Operational fields
    status = Column(String(50), nullable=False, default="active")
    blacklisted = Column(Boolean, nullable=False, default=False)

    # Audit timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
    )

    def __repr__(self) -> str:
        return (
            f"<Student id={self.student_id!r} name={self.name!r} "
            f"status={self.status!r} blacklisted={self.blacklisted}>"
        )


# ---------------------------------------------------------------------------
# Query helpers — import and call these from your API layer or services.
# ---------------------------------------------------------------------------

def get_student_by_id(db, student_id: str):
    """
    Return the Student record whose student_id matches the given value,
    or None if no match is found.

    Parameters
    ----------
    db         : An active SQLAlchemy Session (injected via FastAPI's Depends).
    student_id : The college-issued student ID string to look up.
    """
    return (
        db.query(Student)
        .filter(Student.student_id == student_id)
        .first()
    )


class Screening(Base):
    """
    Represents a screening session result.
    """
    __tablename__ = "screenings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)
    screening_id = Column(String(36), unique=True, nullable=False, index=True)
    student_id = Column(String(100), nullable=True, index=True)
    status = Column(String(50), nullable=False)
    risk_score = Column(db_Float, nullable=True)
    risk_level = Column(String(50), nullable=True)
    ocr_result = Column(db_JSONB, nullable=True)
    db_verification_result = Column(db_JSONB, nullable=True)
    face_result = Column(db_JSONB, nullable=True)
    tampering_result = Column(db_JSONB, nullable=True)
    validation_issues = Column(db_JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)

    def __repr__(self) -> str:
        return f"<Screening screening_id={self.screening_id!r} status={self.status!r}>"
