# fake-id-screening

AI-Based Fake Identity & Document Screening System.

## Features Implemented So Far

- **Database Setup**: Configured Supabase PostgreSQL database connection using SQLAlchemy.
- **Models & Seeding**: Created the `students` table model and a seed script to populate it with dummy development data.
- **FastAPI Backend**: Set up the main application with basic CORS and a `/health` endpoint.
- **Document Upload API**: Implemented the `/api/v1/screen` endpoint that securely accepts a document image and a live photo, validates MIME types, file sizes (max 10MB), and saves them with unique UUID filenames to prevent traversal and enumeration.