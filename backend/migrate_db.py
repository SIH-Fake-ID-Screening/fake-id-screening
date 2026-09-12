import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import text
from database.connection import engine

def migrate():
    with engine.begin() as conn:
        # Check if columns exist
        result = conn.execute(text("SELECT column_name FROM information_schema.columns WHERE table_name='students'"))
        columns = [row[0] for row in result]
        
        if 'front_image_path' not in columns:
            print("Adding front_image_path column...")
            conn.execute(text("ALTER TABLE students ADD COLUMN front_image_path TEXT"))
            
        if 'back_image_path' not in columns:
            print("Adding back_image_path column...")
            conn.execute(text("ALTER TABLE students ADD COLUMN back_image_path TEXT"))
            
        if 'photo_path' in columns:
            print("Migrating data from photo_path to front_image_path...")
            conn.execute(text("UPDATE students SET front_image_path = photo_path WHERE photo_path IS NOT NULL"))
            print("Dropping photo_path column...")
            conn.execute(text("ALTER TABLE students DROP COLUMN photo_path"))
            
    print("Migration complete.")

if __name__ == "__main__":
    migrate()
