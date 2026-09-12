"""
services/risk_service.py
------------------------
Production-grade multi-factor risk engine for the SIH fake-ID screening system.

Scoring model
-------------
Final risk  =  tampering * 0.40
             + face      * 0.30
             + identity  * 0.20
             + blacklist * 0.10

All component scores are normalised to [0, 100] before weighting.
Final score is clamped to [0, 100].

Critical override rules are applied AFTER the weighted sum to ensure
hard failures are never masked by clean scores in other components.

DO NOT use this file for forensic tampering analysis.
That logic lives entirely in tempering/scoring/risk_score.py.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Component weights (must sum to 1.0)
# ---------------------------------------------------------------------------
_W_TAMPERING = 0.40
_W_FACE      = 0.30
_W_IDENTITY  = 0.20
_W_BLACKLIST = 0.10

# ---------------------------------------------------------------------------
# Risk-level thresholds
# ---------------------------------------------------------------------------
_LEVEL_LOW_MAX    = 30
_LEVEL_MEDIUM_MAX = 60
_LEVEL_HIGH_MAX   = 80
# >= 80 -> Critical


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, value))


# ---------------------------------------------------------------------------
# Component scorers
# ---------------------------------------------------------------------------

def _score_tampering(tampering: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """
    Return (tampering_risk 0-100, reasons).

    Uses the MAXIMUM risk score across front/back -- a heavily tampered front
    must not be diluted by a clean back.
    Missing or errored tampering -> conservative 70.
    """
    reasons: List[str] = []

    if not tampering:
        reasons.append("Tampering analysis unavailable; applying conservative penalty.")
        return 70.0, reasons

    scores: List[float] = []
    for side in ("front", "back"):
        side_result = tampering.get(side)
        if side_result and isinstance(side_result, dict):
            raw = side_result.get("risk_score")
            if raw is not None:
                scores.append(float(raw))
                if side_result.get("tampered"):
                    reasons.append(
                        f"Document {side} flagged as tampered "
                        f"(risk_score={raw:.1f}, level={side_result.get('risk_level', '?')})."
                    )

    if not scores:
        reasons.append("Tampering scores missing; applying conservative penalty.")
        return 70.0, reasons

    risk = _clamp(max(scores))  # worst-case, not average
    return risk, reasons


def _score_face(face: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """
    Return (face_risk 0-100, reasons).

    match=True  -> risk = max(0, (1 - confidence) * 100)
    match=False -> risk = 100
    missing     -> risk = 80
    """
    reasons: List[str] = []

    if not face:
        reasons.append("Face verification result missing; applying conservative penalty.")
        return 80.0, reasons

    match = face.get("match")
    confidence = float(face.get("confidence", 0.0))

    if match is None:
        reasons.append("Face match result is None; applying conservative penalty.")
        return 80.0, reasons

    if not match:
        reasons.append(f"Face mismatch detected (confidence={confidence:.4f}).")
        return 100.0, reasons

    # Clamp confidence to [0,1] -- InsightFace can return slightly >1.0
    confidence = _clamp(confidence, 0.0, 1.0)
    risk = _clamp((1.0 - confidence) * 100.0)
    if risk > 0:
        reasons.append(f"Face matched with confidence={confidence:.4f} (residual risk={risk:.1f}).")
    return risk, reasons


def _score_identity(
    ocr: Optional[Dict[str, Any]],
    student: Optional[Dict[str, Any]],
) -> Tuple[float, List[str]]:
    """
    Return (identity_risk 0-100, reasons).

    Compares OCR-extracted fields against the trusted DB student record.
    """
    reasons: List[str] = []
    risk: float = 0.0

    if student is None:
        reasons.append("Student not found in database.")
        return 100.0, reasons

    if not ocr:
        reasons.append("OCR result missing; cannot validate identity fields.")
        return 50.0, reasons  # moderate penalty -- can't confirm or deny

    import re
    from datetime import date

    def _norm(s: Optional[str]) -> str:
        return (s or "").strip().lower()

    def _norm_course(s: Optional[str]) -> str:
        s = _norm(s)
        # Remove punctuation
        s = re.sub(r'[\.,\-\/\(\)]', ' ', s)
        # Collapse repeated spaces
        s = re.sub(r'\s+', ' ', s).strip()
        return s

    # OCR student_id vs DB student_id
    ocr_sid = _norm(ocr.get("student_id"))
    db_sid  = _norm(student.get("student_id"))
    if ocr_sid and db_sid and ocr_sid != db_sid:
        risk += 50
        reasons.append(
            f"Student ID mismatch: OCR='{ocr.get('student_id')}' vs DB='{student.get('student_id')}'."
        )

    # OCR name vs DB name -- simple substring/prefix heuristic (OCR is noisy)
    ocr_name = _norm(ocr.get("name"))
    db_name  = _norm(student.get("name"))
    if ocr_name and db_name:
        ocr_first = ocr_name.split()[0] if ocr_name.split() else ""
        db_first  = db_name.split()[0]  if db_name.split()  else ""
        if ocr_first and db_first and ocr_first not in db_name and db_first not in ocr_name:
            risk += 30
            reasons.append(
                f"Name mismatch: OCR='{ocr.get('name')}' vs DB='{student.get('name')}'."
            )

    # OCR DOB vs DB DOB
    ocr_dob = _norm(ocr.get("dob"))
    db_dob  = _norm(student.get("dob"))
    if ocr_dob and db_dob and ocr_dob != db_dob:
        risk += 30
        reasons.append(
            f"Date of birth mismatch: OCR='{ocr.get('dob')}' vs DB='{student.get('dob')}'."
        )

    # OCR course vs DB course
    ocr_course = _norm_course(ocr.get("course"))
    db_course  = _norm_course(student.get("course"))
    if ocr_course and db_course and ocr_course not in db_course and db_course not in ocr_course:
        risk += 20
        reasons.append(
            f"Course mismatch: OCR='{ocr.get('course')}' vs DB='{student.get('course')}'."
        )

    # OCR college vs DB college
    ocr_college = _norm_course(ocr.get("college"))
    db_college  = _norm_course(student.get("college"))
    if ocr_college and db_college and ocr_college not in db_college and db_college not in ocr_college:
        risk += 20
        reasons.append(
            f"College mismatch: OCR='{ocr.get('college')}' vs DB='{student.get('college')}'."
        )

    # Missing required OCR fields
    required_fields = ("student_id", "name", "dob")
    for field in required_fields:
        if not _norm(ocr.get(field)):
            risk += 20
            reasons.append(f"Required OCR field '{field}' is missing or empty.")

    # Expired document
    ocr_valid_till = _norm(ocr.get("valid_till"))
    if ocr_valid_till:
        today_str = date.today().isoformat()
        # Simple string compare assuming YYYY-MM-DD
        if ocr_valid_till < today_str:
            risk += 30
            reasons.append(
                f"Document is expired: OCR valid_till='{ocr.get('valid_till')}' is before today ({today_str})."
            )

    return _clamp(risk), reasons


def _score_blacklist(student: Optional[Dict[str, Any]]) -> Tuple[float, List[str]]:
    """
    Return (blacklist_risk 0-100, reasons).

    blacklisted        -> 100
    inactive/suspended -> 80
    active             -> 0
    """
    reasons: List[str] = []

    if student is None:
        return 0.0, reasons  # handled by identity score

    if student.get("blacklisted"):
        reasons.append("Student is blacklisted.")
        return 100.0, reasons

    status = (student.get("status") or "").lower()
    if status == "active":
        return 0.0, reasons

    reasons.append(f"Student account status is '{status}' (not active).")
    return 80.0, reasons


# ---------------------------------------------------------------------------
# Critical override rules
# ---------------------------------------------------------------------------

def _apply_critical_overrides(
    weighted_risk: float,
    face: Optional[Dict[str, Any]],
    student: Optional[Dict[str, Any]],
    tampering: Optional[Dict[str, Any]],
    identity_risk: float,
    blacklist_risk: float,
) -> Tuple[float, str, List[str]]:
    """
    Apply hard-floor overrides.  Returns (final_risk, final_status, critical_flags).
    A hard failure is never masked by clean scores in other components.
    """
    critical_flags: List[str] = []
    final_risk   = weighted_risk
    final_status: Optional[str] = None

    # Blacklisted
    if blacklist_risk >= 100:
        critical_flags.append("BLACKLISTED")
        final_risk   = max(final_risk, 95.0)
        final_status = "rejected"

    # Student not found
    if student is None:
        critical_flags.append("STUDENT_NOT_FOUND")
        final_risk   = max(final_risk, 90.0)
        final_status = "rejected"

    # Face mismatch
    if face is not None and not face.get("match", True):
        critical_flags.append("FACE_MISMATCH")
        final_risk   = max(final_risk, 85.0)
        final_status = final_status or "rejected"

    # Tampering detected
    if tampering:
        is_tampered = tampering.get("is_tampered", False)
        max_tamper_score = max(
            (
                float(tampering.get(side, {}).get("risk_score", 0.0))
                for side in ("front", "back")
                if isinstance(tampering.get(side), dict)
            ),
            default=0.0,
        )
        if is_tampered:
            critical_flags.append(f"TAMPERING_DETECTED (is_tampered=True, score={max_tamper_score:.1f})")
            if max_tamper_score >= 70.0:
                final_risk = max(final_risk, 80.0)
            else:
                final_risk = max(final_risk, 75.0)
            final_status = final_status or "document_tampered"

    # Identity mismatch
    if identity_risk >= 50:
        critical_flags.append(f"IDENTITY_MISMATCH (score={identity_risk:.1f})")
        final_risk   = max(final_risk, 75.0)
        final_status = final_status or "suspicious"

    # Level-based status when no critical trigger fired
    if final_status is None:
        clamped = _clamp(final_risk)
        if clamped < _LEVEL_LOW_MAX:
            final_status = "completed"
        else:
            final_status = "suspicious"

    return _clamp(final_risk), final_status, critical_flags


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_screening_risk(
    ocr_result: Optional[Dict[str, Any]],
    student: Optional[Dict[str, Any]],
    face_result: Optional[Dict[str, Any]],
    tampering_result: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Compute the final screening risk score.

    Parameters
    ----------
    ocr_result       : Flat dict from ocr_service.extract_document().
                       Keys: student_id, name, dob, course, college, valid_till.
    student          : Dict version of the DB Student record (or None if not found).
                       Keys: student_id, name, dob, course, college, valid_till,
                             status, blacklisted.
    face_result      : Dict from face_service.verify_faces().
                       Keys: match (bool), confidence (float 0-1).
    tampering_result : 'tampering' block from the ScreeningResponse, i.e.:
                       {
                           "front": {tampered, risk_score, risk_level, confidence},
                           "back":  {tampered, risk_score, risk_level, confidence},
                           "is_tampered": bool,
                       }

    Returns
    -------
    {
        "risk_score":     float,        # 0-100
        "risk_level":     str,          # Low | Medium | High | Critical
        "status":         str,          # completed | suspicious | rejected | document_tampered
        "breakdown": {
            "tampering":  float,
            "face":       float,
            "identity":   float,
            "blacklist":  float,
        },
        "reasons":        List[str],
        "critical_flags": List[str],
    }
    """
    # 1. Score each component
    tampering_risk, t_reasons = _score_tampering(tampering_result)
    face_risk,      f_reasons = _score_face(face_result)
    identity_risk,  i_reasons = _score_identity(ocr_result, student)
    blacklist_risk, b_reasons = _score_blacklist(student)

    all_reasons = t_reasons + f_reasons + i_reasons + b_reasons

    # 2. Weighted combination
    weighted = (
        tampering_risk  * _W_TAMPERING
        + face_risk     * _W_FACE
        + identity_risk * _W_IDENTITY
        + blacklist_risk * _W_BLACKLIST
    )
    weighted = _clamp(weighted)

    # 3. Critical overrides (hard floors; never let a clean score hide a failure)
    final_risk, final_status, critical_flags = _apply_critical_overrides(
        weighted_risk=weighted,
        face=face_result,
        student=student,
        tampering=tampering_result,
        identity_risk=identity_risk,
        blacklist_risk=blacklist_risk,
    )

    # 4. Risk level label
    if final_risk < _LEVEL_LOW_MAX:
        risk_level = "Low"
    elif final_risk < _LEVEL_MEDIUM_MAX:
        risk_level = "Medium"
    elif final_risk < _LEVEL_HIGH_MAX:
        risk_level = "High"
    else:
        risk_level = "Critical"

    logger.info(
        "Risk engine: tampering=%.1f face=%.1f identity=%.1f blacklist=%.1f -> "
        "weighted=%.1f final=%.1f level=%s status=%s flags=%s",
        tampering_risk, face_risk, identity_risk, blacklist_risk,
        weighted, final_risk, risk_level, final_status, critical_flags,
    )

    return {
        "risk_score":     round(final_risk, 2),
        "risk_level":     risk_level,
        "status":         final_status,
        "breakdown": {
            "tampering":  round(tampering_risk, 2),
            "face":       round(face_risk, 2),
            "identity":   round(identity_risk, 2),
            "blacklist":  round(blacklist_risk, 2),
        },
        "reasons":        all_reasons,
        "critical_flags": critical_flags,
    }
