"""
database/seed.py
----------------
Inserts sample / development records into the `students` table.

Usage
-----
    # From the backend/ directory:
    python -m database.seed

When to use
-----------
* Development & testing only — do NOT run against production.
* Replace the SAMPLE_STUDENTS list below with your 20–30 real authorized
  ID card records when you are ready to populate the production database.

Guidelines for real data
------------------------
* Keep one dict per physical ID card.
* Set photo_path to the relative path of the scanned / cropped reference photo,
  e.g.  "uploads/reference_photos/STU2024001.jpg"
* Do NOT store the actual image bytes in the database.
* Set status to "active" for valid cards and "expired" / "suspended" as needed.
* Set blacklisted=True only for cards that must be flagged immediately.
"""

import sys
import os
from datetime import date

# ---------------------------------------------------------------------------
# Make sure the backend/ package root is on sys.path when running directly.
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from database.connection import SessionLocal, create_tables
from database.models import Student

# ---------------------------------------------------------------------------
# SAMPLE DATA — replace these dicts with your real authorized records.
# ---------------------------------------------------------------------------
SAMPLE_STUDENTS = [
    {
        "student_id": "STU2024001",
        "name": "Aarav Sharma",
        "dob": date(2002, 3, 15),
        "college": "IIT Bombay",
        "course": "B.Tech Computer Science",
        "valid_till": date(2026, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024001.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024002",
        "name": "Priya Nair",
        "dob": date(2001, 7, 22),
        "college": "NIT Trichy",
        "course": "B.Tech Electronics",
        "valid_till": date(2025, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024002.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024003",
        "name": "Rohan Verma",
        "dob": date(2003, 11, 5),
        "college": "BITS Pilani",
        "course": "B.E. Mechanical",
        "valid_till": date(2027, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024003.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024004",
        "name": "Sneha Patel",
        "dob": date(2002, 6, 18),
        "college": "DTU Delhi",
        "course": "B.Tech Civil",
        "valid_till": date(2026, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024004.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024005",
        "name": "Karan Mehta",
        "dob": date(2000, 1, 30),
        "college": "VIT Vellore",
        "course": "B.Tech Information Technology",
        "valid_till": date(2024, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024005.jpg",
        "status": "expired",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024006",
        "name": "Ananya Rao",
        "dob": date(2001, 9, 12),
        "college": "SRM Chennai",
        "course": "B.Tech Biotechnology",
        "valid_till": date(2025, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024006.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024007",
        "name": "Vikram Singh",
        "dob": date(1999, 4, 8),
        "college": "JNTU Hyderabad",
        "course": "M.Tech Data Science",
        "valid_till": date(2025, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024007.jpg",
        "status": "suspended",
        "blacklisted": True,          # flagged as blacklisted for demo purposes
    },
    {
        "student_id": "STU2024008",
        "name": "Meera Krishnan",
        "dob": date(2003, 2, 25),
        "college": "Anna University",
        "course": "B.E. Electrical",
        "valid_till": date(2027, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024008.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024009",
        "name": "Arjun Desai",
        "dob": date(2002, 8, 14),
        "college": "Pune University",
        "course": "B.Tech Chemical",
        "valid_till": date(2026, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024009.jpg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "STU2024010",
        "name": "Divya Menon",
        "dob": date(2001, 12, 3),
        "college": "Manipal University",
        "course": "B.Pharm",
        "valid_till": date(2025, 5, 31),
        "photo_path": "uploads/reference_photos/STU2024010.jpg",
        "status": "active",
        "blacklisted": False,
    },
]

# ---------------------------------------------------------------------------
# Seeding logic
# ---------------------------------------------------------------------------

def seed_database(clear_existing: bool = False) -> None:
    """
    Insert SAMPLE_STUDENTS into the database.

    Parameters
    ----------
    clear_existing : If True, deletes all existing rows before inserting.
                     Useful for a clean reset during development.
                     NEVER set this to True in production.
    """
    create_tables()          # Ensure tables exist before inserting rows.

    db = SessionLocal()
    try:
        if clear_existing:
            deleted = db.query(Student).delete()
            db.commit()
            print(f"🗑️   Cleared {deleted} existing record(s).")

        inserted = 0
        skipped = 0

        for record in SAMPLE_STUDENTS:
            # Skip records whose student_id already exists.
            existing = (
                db.query(Student)
                .filter(Student.student_id == record["student_id"])
                .first()
            )
            if existing:
                print(f"⏭️   Skipping {record['student_id']} — already exists.")
                skipped += 1
                continue

            student = Student(**record)
            db.add(student)
            inserted += 1

        db.commit()
        print(
            f"\n✅  Seed complete: {inserted} inserted, {skipped} skipped "
            f"(total records in SAMPLE_STUDENTS: {len(SAMPLE_STUDENTS)})."
        )

    except Exception as exc:
        db.rollback()
        print(f"❌  Seed failed: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed the students table.")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete all existing rows before inserting sample data.",
    )
    args = parser.parse_args()

    seed_database(clear_existing=args.clear)
