"""
database/connection.py
----------------------
Sets up the SQLAlchemy engine, session factory, and a Base class
for all ORM models. DATABASE_URL is read from the .env file —
no credentials are hard-coded here.
"""

import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

# Load .env from the backend directory (one level up from this file)
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

DATABASE_URL: str = os.getenv("DATABASE_URL", "")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is not set. "
        "Copy .env.example to .env and fill in your credentials."
    )

# connect_args is only required for SQLite; left empty for PostgreSQL.
engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


# ---------------------------------------------------------------------------
# FastAPI dependency — yields a DB session and closes it after the request.
# ---------------------------------------------------------------------------
def get_db():
    """Yield a SQLAlchemy session; always closes on exit."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------
def create_tables() -> None:
    """Create all tables that are registered on Base.metadata."""
    # Import models so they register themselves on Base before create_all runs.
    from database import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    print("[OK] All tables created successfully.")


def verify_connection() -> bool:
    """Return True if the database is reachable, False otherwise."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print("[OK] Database connection verified.")
        return True
    except Exception as exc:  # pragma: no cover
        print("[FAIL] Database connection failed.")
        return False
