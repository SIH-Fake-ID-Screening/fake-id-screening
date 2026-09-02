"""
utils/file_handler.py
---------------------
Utility functions for receiving, validating, saving, and deleting
uploaded image files.

Security design decisions
--------------------------
- UUID-based filenames prevent path traversal and enumeration.
- Only the filename (no directory path) is ever returned to callers.
- MIME type is checked via Pillow (content-based), not just the extension.
- Files are written atomically to a dedicated sub-directory.
"""

import os
import uuid
import logging
from pathlib import Path

from fastapi import UploadFile, HTTPException
from PIL import Image, UnidentifiedImageError

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Base uploads directory — relative to this file's location (backend/utils/)
_BACKEND_DIR = Path(__file__).resolve().parent.parent
UPLOAD_DIR = _BACKEND_DIR / "uploads" / "screening"

ALLOWED_EXTENSIONS: set[str] = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES: set[str] = {"image/jpeg", "image/png"}
MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

# Pillow format → canonical extension mapping for content-based validation
_PILLOW_FORMAT_MAP: dict[str, str] = {
    "JPEG": ".jpg",
    "PNG": ".png",
}


def _ensure_upload_dir() -> None:
    """Create the upload directory if it does not already exist."""
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def validate_and_save(upload: UploadFile, field_label: str) -> str:
    """
    Validate and persist an uploaded image file.

    Checks performed (in order):
      1. File is not empty.
      2. Extension is in the allow-list.
      3. Content-type header is in the allow-list.
      4. Raw bytes do not exceed MAX_FILE_SIZE_BYTES.
      5. Pillow can decode the bytes as a known image format.

    Parameters
    ----------
    upload      : The FastAPI UploadFile object.
    field_label : Human-readable field name used in error messages only.

    Returns
    -------
    str : The saved filename (UUID-based, no directory component).

    Raises
    ------
    HTTPException 400 : Empty file, invalid extension, invalid MIME type,
                        or non-image content.
    HTTPException 413 : File exceeds 10 MB.
    """
    _ensure_upload_dir()

    # 1. Reject empty filename
    original_name = (upload.filename or "").strip()
    if not original_name:
        raise HTTPException(
            status_code=400,
            detail=f"{field_label}: filename is empty or missing.",
        )

    # 2. Extension check
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_label}: extension '{suffix}' is not allowed. "
                f"Accepted: {sorted(ALLOWED_EXTENSIONS)}"
            ),
        )

    # 3. Content-Type header check
    content_type = (upload.content_type or "").lower()
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"{field_label}: content type '{content_type}' is not allowed. "
                f"Accepted: {sorted(ALLOWED_MIME_TYPES)}"
            ),
        )

    # 4. Read bytes & size check
    raw: bytes = await upload.read()

    if not raw:
        raise HTTPException(
            status_code=400,
            detail=f"{field_label}: uploaded file is empty (0 bytes).",
        )

    if len(raw) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=(
                f"{field_label}: file size {len(raw) / (1024*1024):.1f} MB "
                f"exceeds the 10 MB limit."
            ),
        )

    # 5. Content-based image validation via Pillow
    try:
        import io
        img = Image.open(io.BytesIO(raw))
        img.verify()  # Raises if not a valid image
        detected_fmt = img.format  # e.g. "JPEG", "PNG"
    except UnidentifiedImageError:
        raise HTTPException(
            status_code=400,
            detail=f"{field_label}: file content is not a valid image.",
        )
    except Exception:
        raise HTTPException(
            status_code=400,
            detail=f"{field_label}: could not read image content.",
        )

    # Resolve final extension from Pillow's detected format
    detected_suffix = _PILLOW_FORMAT_MAP.get(detected_fmt, suffix)

    # 6. Generate UUID filename and save
    filename = f"{uuid.uuid4().hex}{detected_suffix}"
    dest = UPLOAD_DIR / filename

    # Safety: never overwrite (UUID collision is astronomically unlikely)
    if dest.exists():  # pragma: no cover
        raise HTTPException(
            status_code=500,
            detail="File naming collision. Please retry.",
        )

    dest.write_bytes(raw)
    logger.info("Saved upload [%s] -> %s (%d bytes)", field_label, filename, len(raw))

    # Return only the filename, never the full path
    return filename


def delete_file(filename: str) -> bool:
    """
    Delete a previously saved upload by filename.

    Parameters
    ----------
    filename : The bare filename returned by validate_and_save().

    Returns
    -------
    bool : True if deleted, False if the file did not exist.
    """
    if not filename:
        return False

    # Sanitise: strip any directory components to prevent path traversal
    safe_name = Path(filename).name
    target = UPLOAD_DIR / safe_name

    if target.exists() and target.is_file():
        target.unlink()
        logger.info("Deleted upload: %s", safe_name)
        return True

    return False
