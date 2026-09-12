"""
services/face_service.py
-------------------------
Adapter between the screening pipeline and the AI face module.

Responsibilities
----------------
This service is the ONLY layer that calls FaceVerifier. It:
  - Receives two image paths from the screening pipeline.
  - Calls FaceVerifier.verify_faces() with those paths.
  - Returns the match result.

It does NOT know about:
  - the database schema
  - student records
  - OCR results
  - the meaning of "trusted" vs "untrusted"

That business logic lives in api/screening.py, which is responsible for
ensuring only database.Student.front_image_path is passed as reference_image_path.

Security contract (enforced by api/screening.py, not here)
-----------------------------------------------------------
  reference_image_path  <- must be database.Student.front_image_path
  live_image_path       <- the user-uploaded live photo

  The uploaded document_front is NEVER passed as reference_image_path.
  This service trusts its callers to honour that contract.

Separation of responsibilities
-------------------------------
  OCR service      -> extract_document()        (not called here)
  Database service -> get_student_by_id()       (not called here)
  Face service     -> verify_faces()            <- you are here
"""

import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Import FaceVerifier from ai/face — add project root to sys.path if needed.
# ---------------------------------------------------------------------------
_ROOT_DIR = Path(__file__).resolve().parent.parent.parent  # SIH-Backend/
if str(_ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(_ROOT_DIR))

try:
    from ai.face.face_verification import FaceVerifier
    _verifier = FaceVerifier()
    logger.info("FaceVerifier initialised successfully.")
except Exception as _exc:
    _verifier = None
    logger.error("Failed to initialise FaceVerifier: %s", _exc)


# ---------------------------------------------------------------------------
# Public interface
# ---------------------------------------------------------------------------

def verify_faces(reference_image_path: str, live_image_path: str) -> dict:
    """
    Compare a reference face image against a live photo.

    This is the adapter boundary between the screening pipeline and the
    underlying AI model (FaceVerifier). The service maps the pipeline's
    named arguments to FaceVerifier's positional interface.

    Parameters
    ----------
    reference_image_path : Absolute path to the reference image.
                           The caller (api/screening.py) MUST ensure this
                           comes from database.Student.front_image_path.

    live_image_path      : Absolute path to the user-uploaded live photo.

    Returns
    -------
    dict with keys:
        match      : bool  -- True if faces are the same person.
        confidence : float -- Cosine similarity score (0.0-1.0).

    Raises
    ------
    RuntimeError      : If FaceVerifier failed to initialise.
    FileNotFoundError : If either image path does not exist.
    ValueError        : If no face (or multiple faces) detected.
    """
    if _verifier is None:
        raise RuntimeError(
            "FaceVerifier is not available. Check InsightFace installation."
        )

    logger.info(
        "verify_faces called: reference=%s  live=%s",
        reference_image_path,
        live_image_path,
    )

    # Delegate to the underlying AI module.
    # FaceVerifier.verify_faces(document_image_path, live_image_path) is its
    # original interface — we pass reference_image_path as document_image_path.
    # The AI module has no knowledge of this mapping or of the business rules.
    result = _verifier.verify_faces(
        reference_image_path,   # -> FaceVerifier's document_image_path
        live_image_path,        # -> FaceVerifier's live_image_path
    )

    logger.info(
        "verify_faces result: match=%s confidence=%.4f",
        result.get("match"),
        result.get("confidence", 0.0),
    )

    return result
