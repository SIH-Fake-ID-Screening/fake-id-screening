import sys, os
sys.path.insert(0, ".")
from datetime import date
from database.connection import SessionLocal, create_tables
from database.models import Student

create_tables()

REAL_STUDENTS = [
    {
        "student_id": "202501100600212",
        "name": "Priyanshu Ranjan",
        "dob": date(2005, 12, 27),
        "college": "KIET Group of Institutions",
        "course": "B.Tech IT",
        "valid_till": date(2029, 7, 31),
        "front_image_path": "uploads/students/202501100600212/front.jpeg",
        "back_image_path": "uploads/students/202501100600212/back.jpeg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "202501100600070",
        "name": "Hemant Rao",
        "dob": date(2007, 7, 14),
        "college": "KIET Group of Institutions",
        "course": "B.Tech IT",
        "valid_till": date(2029, 7, 31),
        "front_image_path": "uploads/students/202501100600070/front.jpeg",
        "back_image_path": "uploads/students/202501100600070/back.jpeg",
        "status": "active",
        "blacklisted": False,
    },
    {
        "student_id": "202501100400016",
        "name": "Abhinay Kushwaha",
        "dob": date(2006, 9, 1),
        "college": "KIET Group of Institutions",
        "course": "B.Tech CSE(AIML)",
        "valid_till": date(2029, 7, 31),
        "front_image_path": "uploads/students/202501100400016/front.jpeg",
        "back_image_path": "uploads/students/202501100400016/back.jpeg",
        "status": "active",
        "blacklisted": False,
    },
]

db = SessionLocal()
try:
    inserted = 0
    updated = 0
    for record in REAL_STUDENTS:
        sid = record["student_id"]
        existing = db.query(Student).filter(Student.student_id == sid).first()
        if existing:
            existing.front_image_path = record["front_image_path"]
            existing.back_image_path = record["back_image_path"]
            print("Updated:", sid)
            updated += 1
        else:
            db.add(Student(**record))
            print("Inserted:", sid)
            inserted += 1
    db.commit()
    print("Done:", inserted, "inserted,", updated, "updated.")
finally:
    db.close()
