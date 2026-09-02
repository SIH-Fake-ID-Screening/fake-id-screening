"""
database/__init__.py
--------------------
Public surface of the database package.
"""

from database.connection import Base, SessionLocal, engine, get_db, create_tables, verify_connection
from database.models import Student, get_student_by_id

__all__ = [
    "Base",
    "SessionLocal",
    "engine",
    "get_db",
    "create_tables",
    "verify_connection",
    "Student",
    "get_student_by_id",
]
