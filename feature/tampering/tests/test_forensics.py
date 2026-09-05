import os
import pytest
import numpy as np
import cv2

from preprocessing.document import load_image
from forensic.ela import analyze_ela
from forensic.srm import analyze_srm
from forensic.metadata import analyze_metadata
from forensic.copy_move import analyze_copy_move
from forensic.reference_matching import compare_with_reference
from scoring.risk_score import compute_risk_score
from models.inference import ELASRMModel, TruForModel, TamperingPrediction, detect_tampering
from localization.overlay import generate_overlay

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REFERENCE_DIR = os.path.join(BASE_DIR, "reference")


@pytest.fixture
def dummy_image():
    """Create a 400x600 synthetic BGR test image."""
    img = np.full((400, 600, 3), 230, dtype=np.uint8)
    cv2.rectangle(img, (50, 50), (150, 200), (50, 100, 200), -1)
    cv2.putText(img, "TEST DOCUMENT", (180, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 0), 2)
    return img


def test_ela(dummy_image):
    ela_map, score = analyze_ela(dummy_image, quality=90)
    assert ela_map.shape == (400, 600)
    assert 0.0 <= score <= 100.0
    assert ela_map.dtype == np.float32


def test_srm(dummy_image):
    srm_map, score = analyze_srm(dummy_image)
    assert srm_map.shape == (400, 600)
    assert 0.0 <= score <= 100.0
    assert srm_map.dtype == np.float32


def test_metadata(tmp_path):
    # Test metadata on non-existant file
    dict_res, anomalies, score = analyze_metadata(str(tmp_path / "non_existent.jpg"))
    assert score == 0.0
    assert len(anomalies) > 0

    # Test metadata capped at 15 max
    from PIL import Image
    test_img = Image.new('RGB', (100, 100), color = 'red')
    img_path = str(tmp_path / "test.jpg")
    test_img.save(img_path, "JPEG")
    
    dict_res, anomalies, score = analyze_metadata(img_path)
    assert 0.0 <= score <= 15.0


def test_copy_move(dummy_image):
    cm_map, score, matches_count = analyze_copy_move(dummy_image)
    assert cm_map.shape == (400, 600)
    assert 0.0 <= score <= 100.0
    assert isinstance(matches_count, int)


def test_risk_score_fusion():
    res = compute_risk_score(
        ela_score=40.0,
        srm_score=50.0,
        copy_move_score=0.0,
        metadata_score=10.0,
        suspicious_regions=[{"peak_score": 75.0, "bbox": [10, 10, 50, 50]}]
    )
    assert isinstance(res["tampered"], bool)
    assert 0.0 <= res["risk_score"] <= 100.0
    assert res["risk_level"] in ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    assert res["metadata_score"] <= 15.0


def test_false_positive_guard_for_clean_documents():
    suspicious = [{"peak_score": 100.0, "bbox": [10, 10, 50, 50]} for _ in range(46)]
    res = compute_risk_score(
        ela_score=32.0,
        srm_score=44.0,
        copy_move_score=5.0,
        metadata_score=2.0,
        suspicious_regions=suspicious,
    )
    assert res["risk_score"] < 60.0
    assert res["tampered"] is False


def test_tampered_document_with_several_hotspots_is_detected():
    res = compute_risk_score(
        ela_score=50.0,
        srm_score=55.0,
        copy_move_score=20.0,
        metadata_score=0.0,
        suspicious_regions=[
            {"peak_score": 100.0, "mean_score": 95.0, "bbox": [10, 10, 50, 50]},
            {"peak_score": 92.0, "mean_score": 87.0, "bbox": [100, 100, 40, 60]},
            {"peak_score": 81.0, "mean_score": 76.0, "bbox": [150, 150, 60, 60]},
            {"peak_score": 74.0, "mean_score": 69.0, "bbox": [200, 200, 50, 50]},
            {"peak_score": 68.0, "mean_score": 63.0, "bbox": [250, 250, 50, 50]},
        ],
    )
    assert res["risk_score"] >= 45.0
    assert res["tampered"] is True


def test_high_risk_structured_document_is_flagged_when_hotspots_cluster():
    res = compute_risk_score(
        ela_score=55.0,
        srm_score=60.0,
        copy_move_score=10.0,
        metadata_score=0.0,
        suspicious_regions=[
            {"peak_score": 100.0, "mean_score": 95.0, "bbox": [10, 10, 40, 40]},
            {"peak_score": 100.0, "mean_score": 95.0, "bbox": [20, 50, 70, 50]},
            {"peak_score": 86.0, "mean_score": 81.0, "bbox": [100, 100, 50, 40]},
            {"peak_score": 82.0, "mean_score": 77.0, "bbox": [140, 100, 60, 50]},
            {"peak_score": 75.0, "mean_score": 70.0, "bbox": [180, 150, 50, 30]},
        ],
    )
    assert res["risk_score"] >= 45.0
    assert res["tampered"] is True


def test_scattered_text_like_regions_do_not_trigger_tamper():
    suspicious = [
        {"peak_score": 100.0, "mean_score": 90.0, "bbox": [176, 875, 573, 85]},
        {"peak_score": 100.0, "mean_score": 90.0, "bbox": [1216, 917, 259, 41]},
        {"peak_score": 100.0, "mean_score": 90.0, "bbox": [1237, 836, 330, 73]},
        {"peak_score": 100.0, "mean_score": 90.0, "bbox": [84, 835, 73, 95]},
        {"peak_score": 100.0, "mean_score": 90.0, "bbox": [174, 834, 212, 40]},
    ]
    res = compute_risk_score(
        ela_score=0.0,
        srm_score=86.97,
        copy_move_score=0.0,
        metadata_score=0.0,
        suspicious_regions=suspicious,
    )
    assert res["tampered"] is False


def test_overlay_emphasis_on_hotspots(dummy_image):
    heatmap = np.zeros((400, 600), dtype=np.float32)
    heatmap[100:180, 150:250] = 0.32
    regions = [{"bbox": [150, 100, 100, 80], "peak_score": 63.0, "region_id": 1}]

    overlay = generate_overlay(
        dummy_image,
        heatmap,
        regions,
        alpha=0.85,
        glow_strength=1.5,
        preserve_detail=True,
    )

    assert overlay.shape[0] >= dummy_image.shape[0] + 30
    assert overlay.shape[1] == dummy_image.shape[1]
    assert overlay.shape[2] == 3
    assert np.mean(overlay) > 20


def test_model_protocol_compliance(dummy_image):
    baseline_model = ELASRMModel()
    pred = baseline_model.predict(dummy_image)
    assert pred.overlay_image.shape[1] == 600
    assert pred.overlay_image.shape[2] == 3
    assert pred.overlay_image.shape[0] >= 400

    trufor_model = TruForModel()
    pred_trufor = trufor_model.predict(dummy_image)
    assert isinstance(pred_trufor, TamperingPrediction)


def test_detect_tampering_contract(dummy_image):
    result = detect_tampering(dummy_image)
    assert isinstance(result, dict)
    assert "tampered" in result
    assert "confidence" in result
    assert "tampering_probability" in result
    assert "risk_score" in result
    assert 0.0 <= result["confidence"] <= 1.0
    assert 0.0 <= result["tampering_probability"] <= 1.0


@pytest.fixture(scope="module")
def genuine_front():
    img = cv2.imread(os.path.join(REFERENCE_DIR, "kiet_id_front.png"))
    if img is None:
        pytest.skip("Canonical genuine front reference image not found")
    return img


def test_reference_self_match_scores_low(genuine_front):
    """The genuine card must match its own reference standard with low deviation."""
    diff_map, score, anomalies, details = compare_with_reference(genuine_front, ref_type="front")
    assert 0.0 <= score <= 100.0
    assert score < 25.0, f"Genuine self-match scored {score:.1f}, expected < 25"
    assert details["matched_reference_side"] == "front"
    assert diff_map.shape == genuine_front.shape[:2]


def test_reference_exposure_variation_scores_low(genuine_front):
    """Lighting/exposure changes on a genuine card must not be flagged."""
    bright = cv2.convertScaleAbs(genuine_front, alpha=1.12, beta=8)
    _, score, _, _ = compare_with_reference(bright, ref_type="front")
    assert score < 25.0, f"Exposure variant scored {score:.1f}, expected < 25"


def test_reference_photo_tamper_scores_high(genuine_front):
    """A replaced/re-printed photo must be flagged in the photo zone."""
    h, w = genuine_front.shape[:2]
    tampered = genuine_front.copy()
    px, py = int(0.27 * w), int(0.225 * h)
    pw, ph = int(0.37 * w), int(0.26 * h)
    region = tampered[py:py + ph, px:px + pw]
    region = cv2.convertScaleAbs(cv2.GaussianBlur(region, (9, 9), 0), alpha=1.15, beta=12)
    tampered[py:py + ph, px:px + pw] = region

    _, score, anomalies, details = compare_with_reference(tampered, ref_type="front")
    assert score > 40.0, f"Photo tamper scored {score:.1f}, expected > 40"
    assert anomalies, "Photo tamper produced no anomalies"
    assert details["zone_deviation_scores"]["photo"] > 15.0


def test_reference_name_text_tamper_scores_high(genuine_front):
    """A rewritten name line must be flagged in the name_line zone."""
    h, w = genuine_front.shape[:2]
    tampered = genuine_front.copy()
    nx, ny = int(0.15 * w), int(0.505 * h)
    nw, nh = int(0.70 * w), int(0.045 * h)
    tampered[ny:ny + nh, nx:nx + nw] = np.full((nh, nw, 3), 205, np.uint8)
    cv2.putText(tampered, "RAHUL KUMAR VERMA", (nx, ny + nh - 6),
                cv2.FONT_HERSHEY_DUPLEX, 1.1, (30, 30, 30), 2)

    _, score, anomalies, details = compare_with_reference(tampered, ref_type="front")
    assert score > 40.0, f"Name tamper scored {score:.1f}, expected > 40"
    assert details["zone_deviation_scores"]["name_line"] > 15.0


def test_reference_report_is_json_serializable(genuine_front):
    """match_details and anomalies must contain plain JSON-serializable types."""
    import json
    _, score, anomalies, details = compare_with_reference(genuine_front, ref_type="auto")
    json.dumps({"score": score, "anomalies": anomalies, "details": details})
