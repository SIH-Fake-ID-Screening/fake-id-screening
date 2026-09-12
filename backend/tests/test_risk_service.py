"""
tests/test_risk_service.py
--------------------------
Unit tests for backend/services/risk_service.py

Run from backend/ directory:
    python -m pytest tests/test_risk_service.py -v
"""

import sys
import os

# Ensure backend/ is on sys.path when run from backend/
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from services.risk_service import compute_screening_risk

# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------

GENUINE_STUDENT = {
    "student_id": "202501100400016",
    "name": "Abhinay Kushwaha",
    "dob": "2006-09-01",
    "course": "B.Tech CSE(AIML)",
    "college": "KIET Group of Institutions",
    "valid_till": "2029-07-31",
    "status": "active",
    "blacklisted": False,
}

GENUINE_OCR = {
    "student_id": "202501100400016",
    "name": "Abhinay Kushwaha",
    "dob": "2006-09-01",
    "course": "B.Tech CSE(AIML)",
    "college": "KIET Group of Institutions",
    "valid_till": "2029-07-31",
}

FACE_MATCH = {"match": True, "confidence": 0.98}
FACE_MISMATCH = {"match": False, "confidence": 0.12}

TAMPERING_CLEAN = {
    "front": {"tampered": False, "risk_score": 6.9,  "risk_level": "LOW", "confidence": 0.66},
    "back":  {"tampered": False, "risk_score": 10.0, "risk_level": "LOW", "confidence": 0.60},
    "is_tampered": False,
}

TAMPERING_SEVERE = {
    "front": {"tampered": True,  "risk_score": 78.0, "risk_level": "HIGH",   "confidence": 0.61},
    "back":  {"tampered": False, "risk_score": 15.0, "risk_level": "LOW",    "confidence": 0.65},
    "is_tampered": True,
}

TAMPERING_MODERATE = {
    "front": {"tampered": True,  "risk_score": 49.0, "risk_level": "HIGH",   "confidence": 0.55},
    "back":  {"tampered": False, "risk_score": 12.0, "risk_level": "LOW",    "confidence": 0.60},
    "is_tampered": True,
}


# ---------------------------------------------------------------------------
# 1. Genuine document + matching face + active student
# ---------------------------------------------------------------------------
def test_genuine_clean():
    """Lowest possible risk: clean doc, matched face, active student, good OCR."""
    result = compute_screening_risk(GENUINE_OCR, GENUINE_STUDENT, FACE_MATCH, TAMPERING_CLEAN)

    print(f"\n[genuine] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["status"] == "completed", f"Expected completed, got {result['status']}"
    assert result["risk_score"] < 30, f"Genuine case risk too high: {result['risk_score']}"
    assert result["risk_level"] == "Low"
    assert result["critical_flags"] == []


# ---------------------------------------------------------------------------
# 2. Tampered document (severe)
# ---------------------------------------------------------------------------
def test_tampered_document():
    """Severe tampering on front: must trigger SEVERE_TAMPERING override."""
    result = compute_screening_risk(GENUINE_OCR, GENUINE_STUDENT, FACE_MATCH, TAMPERING_SEVERE)

    print(f"\n[tampered] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["status"] == "document_tampered", f"Expected document_tampered, got {result['status']}"
    assert result["risk_score"] >= 80.0
    assert any("TAMPERING_DETECTED" in f for f in result["critical_flags"])


# ---------------------------------------------------------------------------
# 3. Face mismatch
# ---------------------------------------------------------------------------
def test_face_mismatch():
    """Face mismatch: must override status to rejected with risk >= 85."""
    result = compute_screening_risk(GENUINE_OCR, GENUINE_STUDENT, FACE_MISMATCH, TAMPERING_CLEAN)

    print(f"\n[face_mismatch] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["status"] == "rejected", f"Expected rejected, got {result['status']}"
    assert result["risk_score"] >= 85.0
    assert "FACE_MISMATCH" in result["critical_flags"]
    assert result["breakdown"]["face"] == 100.0


# ---------------------------------------------------------------------------
# 4. Blacklisted student
# ---------------------------------------------------------------------------
def test_blacklisted():
    """Blacklisted student: must hard-reject with risk >= 95."""
    blacklisted = dict(GENUINE_STUDENT, blacklisted=True)
    result = compute_screening_risk(GENUINE_OCR, blacklisted, FACE_MATCH, TAMPERING_CLEAN)

    print(f"\n[blacklisted] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["status"] == "rejected"
    assert result["risk_score"] >= 95.0
    assert "BLACKLISTED" in result["critical_flags"]
    assert result["breakdown"]["blacklist"] == 100.0


# ---------------------------------------------------------------------------
# 5. Student not found
# ---------------------------------------------------------------------------
def test_student_not_found():
    """No DB record: must reject with risk >= 90."""
    result = compute_screening_risk(GENUINE_OCR, None, None, None)

    print(f"\n[not_found] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["status"] == "rejected"
    assert result["risk_score"] >= 90.0
    assert "STUDENT_NOT_FOUND" in result["critical_flags"]
    assert result["breakdown"]["identity"] == 100.0


# ---------------------------------------------------------------------------
# 6. OCR identity mismatch (student_id differs)
# ---------------------------------------------------------------------------
def test_ocr_identity_mismatch():
    """OCR student_id differs from DB: identity risk >= 50, suspicious."""
    bad_ocr = dict(GENUINE_OCR, student_id="FAKE_ID_999")
    result = compute_screening_risk(bad_ocr, GENUINE_STUDENT, FACE_MATCH, TAMPERING_CLEAN)

    print(f"\n[id_mismatch] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["breakdown"]["identity"] >= 50.0
    assert any("IDENTITY_MISMATCH" in f for f in result["critical_flags"])
    assert result["risk_score"] >= 75.0


# ---------------------------------------------------------------------------
# 7. Combined multiple-risk case
# ---------------------------------------------------------------------------
def test_combined_risks():
    """Tampered doc + face mismatch: highest override wins (rejected >= 85)."""
    result = compute_screening_risk(GENUINE_OCR, GENUINE_STUDENT, FACE_MISMATCH, TAMPERING_SEVERE)

    print(f"\n[combined] risk_score={result['risk_score']} level={result['risk_level']} status={result['status']}")
    assert result["status"] == "rejected"           # face mismatch takes precedence
    assert result["risk_score"] >= 85.0
    assert "FACE_MISMATCH" in result["critical_flags"]
    assert any("TAMPERING_DETECTED" in f for f in result["critical_flags"])


# ---------------------------------------------------------------------------
# 8. Formatting fixes: valid_till, course, dob
# ---------------------------------------------------------------------------
def test_valid_till_future():
    """valid_till in future must not trigger expiry risk."""
    future_ocr = dict(GENUINE_OCR, valid_till="2029-07-01")
    result = compute_screening_risk(future_ocr, GENUINE_STUDENT, FACE_MATCH, TAMPERING_CLEAN)
    assert result["status"] == "completed"
    assert result["breakdown"]["identity"] == 0.0

def test_course_normalization_exact():
    """'B TECH' vs 'B.Tech' should match."""
    course_ocr = dict(GENUINE_OCR, course="B TECH")
    course_db = dict(GENUINE_STUDENT, course="B.Tech")
    result = compute_screening_risk(course_ocr, course_db, FACE_MATCH, TAMPERING_CLEAN)
    assert result["breakdown"]["identity"] == 0.0

def test_course_normalization_partial():
    """'B TECH' vs 'B.Tech CSE(AIML)' should match as partial string."""
    course_ocr = dict(GENUINE_OCR, course="B TECH")
    course_db = dict(GENUINE_STUDENT, course="B.Tech CSE(AIML)")
    result = compute_screening_risk(course_ocr, course_db, FACE_MATCH, TAMPERING_CLEAN)
    assert result["breakdown"]["identity"] == 0.0

def test_course_mismatch_genuine():
    """Genuinely different courses should mismatch."""
    course_ocr = dict(GENUINE_OCR, course="B.A. English")
    course_db = dict(GENUINE_STUDENT, course="B.Tech CSE")
    result = compute_screening_risk(course_ocr, course_db, FACE_MATCH, TAMPERING_CLEAN)
    assert result["breakdown"]["identity"] >= 20.0

def test_dob_mismatch():
    """Different DOB must mismatch."""
    dob_ocr = dict(GENUINE_OCR, dob="2007-07-14")
    dob_db = dict(GENUINE_STUDENT, dob="2006-09-01")
    result = compute_screening_risk(dob_ocr, dob_db, FACE_MATCH, TAMPERING_CLEAN)
    assert result["breakdown"]["identity"] >= 30.0

def test_tampering_is_tampered_status():
    """tampering + matching face => document_tampered"""
    result = compute_screening_risk(GENUINE_OCR, GENUINE_STUDENT, FACE_MATCH, TAMPERING_MODERATE)
    assert result["status"] == "document_tampered"
    assert result["risk_score"] >= 75.0
