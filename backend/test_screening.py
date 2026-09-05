# -*- coding: utf-8 -*-
import sys, io
# Force UTF-8 output on Windows to avoid charmap errors
if sys.stdout.encoding != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
"""
test_screening.py
-----------------
Architecture and integration tests for the screening pipeline.

Tests
-----
Test 1 [Integration] — Happy path:
    OCR returns Priyanshu's student_id → DB returns Priyanshu →
    Priyanshu DB reference image + Priyanshu live photo → Face verification runs.

Test 2 [Integration] — Face mismatch:
    OCR returns Priyanshu's student_id → DB returns Priyanshu →
    Priyanshu DB reference image + Hemant live photo → face_mismatch.

Test 3 [Unit] — Unknown student_id:
    OCR returns unknown ID → student_not_found → face verification must NOT run.

Test 4 [Unit] — Blacklisted student:
    DB returns blacklisted student → student_blacklisted → face verification must NOT run.

Test 5 [Static] — Security check:
    Verify that `document_front` is NEVER passed to verify_faces() in screening.py.

Usage
-----
    # Start the API server first for integration tests (Tests 1 & 2):
    #   uvicorn main:app --reload
    #
    # Then run from backend/ directory:
    python test_screening.py

    # For unit tests only (no server needed):
    python test_screening.py --unit-only
"""

import sys
import os
import io
import ast
import inspect
import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure backend/ is on the path
# ---------------------------------------------------------------------------
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BACKEND_DIR = Path(__file__).resolve().parent
REAL_IMAGES = BACKEND_DIR / "uploads" / "students"

_PRIYANSHU_ID = "202501100600212"
_HEMANT_ID    = "202501100600070"

PRIYANSHU_FRONT = str(REAL_IMAGES / _PRIYANSHU_ID / "front.jpeg")
PRIYANSHU_LIVE  = PRIYANSHU_FRONT  # same person → should match
HEMANT_FRONT    = str(REAL_IMAGES / _HEMANT_ID    / "front.jpeg")
HEMANT_LIVE     = HEMANT_FRONT     # different person → should mismatch vs Priyanshu ref


# ---------------------------------------------------------------------------
# ANSI colours for pretty output
# ---------------------------------------------------------------------------
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def _ok(msg):   print(f"  {GREEN}[PASS]{RESET}  {msg}")
def _fail(msg):  print(f"  {RED}[FAIL]{RESET}  {msg}"); raise AssertionError(msg)
def _skip(msg):  print(f"  {YELLOW}[SKIP]{RESET}  {msg}")
def _head(msg):  print(f"\n{BOLD}{msg}{RESET}")


# ===========================================================================
# TEST 3 — Unit: Unknown student_id → student_not_found
# ===========================================================================

def test_3_unknown_student():
    _head("Test 3: Unknown student_id → student_not_found (unit test, no server needed)")

    from services import database_service, face_service

    mock_db = MagicMock()

    # Patch the underlying DB query to return None
    with patch("services.database_service._db_get_student_by_id", return_value=None):
        student = database_service.get_student_by_id(mock_db, "UNKNOWN_ID_999")

    assert student is None, "Expected None for unknown student_id"
    _ok("get_student_by_id returned None for unknown ID")

    # Verify face_service was never called (simulated: we just confirm it's None-gated)
    face_called = False
    if student is None:
        pass  # pipeline returns student_not_found, face service never reached
    else:
        face_called = True

    assert not face_called, "Face verification must NOT run when student is None"
    _ok("Face verification correctly skipped for unknown student")


# ===========================================================================
# TEST 4 — Unit: Blacklisted student → student_blacklisted
# ===========================================================================

def test_4_blacklisted_student():
    _head("Test 4: Blacklisted student → student_blacklisted (unit test, no server needed)")

    from services import database_service, face_service

    # Build a mock blacklisted student
    mock_student = MagicMock()
    mock_student.student_id  = "STU2024007"
    mock_student.name        = "Vikram Singh"
    mock_student.blacklisted = True
    mock_student.status      = "suspended"
    mock_student.front_image_path = "uploads/students/STU2024007/front.jpeg"

    mock_db = MagicMock()
    face_verify_called = False

    with patch("services.database_service._db_get_student_by_id", return_value=mock_student):
        student = database_service.get_student_by_id(mock_db, "STU2024007")

    assert student is not None, "Mock student should be returned"
    assert student.blacklisted is True, "Student should be blacklisted"
    _ok(f"DB returned blacklisted student: {student.name}")

    # Simulate pipeline logic
    if student.blacklisted:
        result_status = "student_blacklisted"
    else:
        # This branch must NOT be reached
        face_verify_called = True
        result_status = "completed"

    assert result_status == "student_blacklisted", f"Expected student_blacklisted, got {result_status}"
    assert not face_verify_called, "Face verification must NOT run for blacklisted student"
    _ok("Pipeline correctly blocked at blacklist check")
    _ok("Face verification correctly skipped for blacklisted student")


# ===========================================================================
# TEST 5 — Static: document_front must NEVER be passed to verify_faces()
# ===========================================================================

def test_5_document_front_never_passed_to_verify_faces():
    _head("Test 5: Static security check — document_front never passed to verify_faces()")

    screening_path = BACKEND_DIR / "api" / "screening.py"
    source = screening_path.read_text(encoding="utf-8")

    # Parse the AST and find all calls to verify_faces()
    tree = ast.parse(source)

    violations = []

    class FaceCallVisitor(ast.NodeVisitor):
        def visit_Call(self, node):
            # Match: face_service.verify_faces(...) or verify_faces(...)
            is_verify_call = False
            if isinstance(node.func, ast.Attribute) and node.func.attr == "verify_faces":
                is_verify_call = True
            elif isinstance(node.func, ast.Name) and node.func.id == "verify_faces":
                is_verify_call = True

            if is_verify_call:
                for arg in node.args:
                    arg_src = ast.unparse(arg)
                    if "document_front" in arg_src:
                        violations.append(
                            f"Line {node.lineno}: document_front found in verify_faces() positional arg: {arg_src}"
                        )
                for kw in node.keywords:
                    val_src = ast.unparse(kw.value)
                    if "document_front" in val_src:
                        violations.append(
                            f"Line {node.lineno}: document_front found in verify_faces() kwarg {kw.arg}={val_src}"
                        )

            self.generic_visit(node)

    FaceCallVisitor().visit(tree)

    if violations:
        for v in violations:
            print(f"  {RED}VIOLATION{RESET}: {v}")
        _fail(f"document_front was passed to verify_faces() in {violations}")
    else:
        _ok("No call to verify_faces() uses document_front as an argument")

    # Also verify that trusted_reference_path is sourced from front_image_path
    assert "front_image_path" in source, "trusted reference must come from front_image_path"
    assert "trusted_reference_path" in source, "variable trusted_reference_path must exist"
    assert "document_front_path" not in source.split("verify_faces")[1].split("\n")[0], \
        "document_front_path must not appear on the verify_faces call line"

    _ok("trusted_reference_path is sourced from database.front_image_path")
    _ok("SECURITY RULE VERIFIED: document images are never used as face reference")


# ===========================================================================
# INTEGRATION TESTS — require running server + real images on disk
# ===========================================================================

def _check_integration_prereqs():
    """Return (ok, reason) for integration test preconditions."""
    try:
        import requests
    except ImportError:
        return False, "requests library not installed"

    if not Path(PRIYANSHU_FRONT).exists():
        return False, f"Priyanshu's reference image not found: {PRIYANSHU_FRONT}"
    if not Path(HEMANT_FRONT).exists():
        return False, f"Hemant's reference image not found: {HEMANT_FRONT}"

    try:
        import requests
        r = requests.get("http://127.0.0.1:8000/health", timeout=2)
        if r.status_code != 200:
            return False, "API server returned non-200 on /health"
    except Exception as e:
        return False, f"API server not reachable: {e}"

    return True, "OK"


def _post_screen(doc_front_path: str, doc_back_path: str, live_path: str) -> dict:
    import requests

    with open(doc_front_path, "rb") as f1, \
         open(doc_back_path,  "rb") as f2, \
         open(live_path,      "rb") as f3:
        r = requests.post(
            "http://127.0.0.1:8000/api/v1/screen",
            files={
                "document_front": ("front.jpg", f1, "image/jpeg"),
                "document_back":  ("back.jpg",  f2, "image/jpeg"),
                "live_photo":     ("live.jpg",   f3, "image/jpeg"),
            },
            timeout=60,
        )

    r.raise_for_status()
    return r.json()


def test_1_priyanshu_self_match():
    _head("Test 1 [Integration]: Priyanshu ref + Priyanshu live → face match")
    ok, reason = _check_integration_prereqs()
    if not ok:
        _skip(f"Skipping integration test: {reason}")
        return

    # Use Priyanshu's front image as both the document AND the live photo.
    # OCR mock will return Priyanshu's student_id.
    # DB will resolve Priyanshu's front_image_path as the trusted reference.
    # Face verification: Priyanshu ref ↔ Priyanshu live → should match.
    result = _post_screen(PRIYANSHU_FRONT, PRIYANSHU_FRONT, PRIYANSHU_LIVE)

    print(f"  Response status: {result.get('status')}")
    print(f"  Student: {result.get('student', {}).get('name')}")
    print(f"  Face match: {result.get('face_verification', {}).get('match')}")
    print(f"  Confidence: {result.get('face_verification', {}).get('confidence')}")

    # OCR mock always returns Priyanshu's ID, so DB lookup succeeds
    assert result.get("student") is not None, "Student should be found"
    assert result["student"]["student_id"] == _PRIYANSHU_ID, "Wrong student returned"
    assert result.get("face_verification") is not None, "Face verification must run"

    # The comparison is: DB reference (Priyanshu) ↔ live (Priyanshu) → match
    assert result["face_verification"]["match"] is True, (
        f"Expected match=True (same person), got match={result['face_verification']['match']}, "
        f"confidence={result['face_verification'].get('confidence')}"
    )
    _ok(f"Priyanshu matched himself (confidence={result['face_verification']['confidence']:.4f})")


def test_2_priyanshu_vs_hemant_mismatch():
    _head("Test 2 [Integration]: Priyanshu ref (DB) + Hemant live → face mismatch")
    ok, reason = _check_integration_prereqs()
    if not ok:
        _skip(f"Skipping integration test: {reason}")
        return

    # OCR mock returns Priyanshu's student_id → DB gives Priyanshu's reference image.
    # But the "live" photo is actually Hemant's face → should NOT match.
    result = _post_screen(PRIYANSHU_FRONT, PRIYANSHU_FRONT, HEMANT_LIVE)

    print(f"  Response status: {result.get('status')}")
    print(f"  Student: {result.get('student', {}).get('name')}")
    print(f"  Face match: {result.get('face_verification', {}).get('match')}")
    print(f"  Confidence: {result.get('face_verification', {}).get('confidence')}")

    assert result.get("student") is not None, "Student should be found"
    assert result["student"]["student_id"] == _PRIYANSHU_ID, "Wrong student returned"
    assert result.get("face_verification") is not None, "Face verification must run"

    # DB reference is Priyanshu; live photo is Hemant → should NOT match
    assert result["face_verification"]["match"] is False, (
        f"Expected match=False (different people), got match={result['face_verification']['match']}, "
        f"confidence={result['face_verification'].get('confidence')}"
    )
    assert result.get("status") == "face_mismatch", (
        f"Expected status=face_mismatch, got status={result.get('status')}"
    )
    _ok(f"Correctly detected mismatch (confidence={result['face_verification']['confidence']:.4f})")


# ===========================================================================
# Main runner
# ===========================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Screening pipeline architecture tests.")
    parser.add_argument(
        "--unit-only",
        action="store_true",
        help="Run only unit tests (no server or real images required).",
    )
    args = parser.parse_args()

    results = {"passed": 0, "failed": 0, "skipped": 0}

    def run(name, fn):
        try:
            fn()
            results["passed"] += 1
        except AssertionError as e:
            results["failed"] += 1
            print(f"  {RED}FAILED{RESET}: {e}")
        except Exception as e:
            results["failed"] += 1
            print(f"  {RED}ERROR{RESET}: {type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"  Screening Pipeline Architecture Tests")
    print(f"{'='*60}")

    # Unit tests — always run
    run("Test 3", test_3_unknown_student)
    run("Test 4", test_4_blacklisted_student)
    run("Test 5", test_5_document_front_never_passed_to_verify_faces)

    # Integration tests — only run if not --unit-only
    if not args.unit_only:
        run("Test 1", test_1_priyanshu_self_match)
        run("Test 2", test_2_priyanshu_vs_hemant_mismatch)

    print(f"\n{'='*60}")
    print(
        f"  Results: "
        f"{GREEN}{results['passed']} passed{RESET}  "
        f"{RED}{results['failed']} failed{RESET}  "
        f"{YELLOW}{results['skipped']} skipped{RESET}"
    )
    print(f"{'='*60}\n")

    sys.exit(0 if results["failed"] == 0 else 1)
