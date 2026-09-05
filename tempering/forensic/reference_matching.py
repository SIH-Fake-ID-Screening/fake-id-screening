import os
import cv2
import numpy as np
from typing import Tuple, List, Dict, Any, Optional
import logging

from preprocessing.document_crop import detect_document

logger = logging.getLogger(__name__)

# Canonical genuine reference standard lives in its own dedicated folder.
_MODULE_DIR = os.path.dirname(os.path.abspath(__file__))
PACKAGE_DIR = os.path.dirname(_MODULE_DIR)
REFERENCE_DIR = os.path.join(PACKAGE_DIR, "reference")

# Canonical genuine card standard: KIET Group of Institutions student ID.
REFERENCE_TEMPLATE_FILES = {
    "front": "kiet_id_front.png",
    "back": "kiet_id_back.jpg",
}

# ---------------------------------------------------------------------------
# Alignment configuration
# ---------------------------------------------------------------------------
ORB_ALIGN_FEATURES = 4000
LOWES_RATIO_THRESHOLD = 0.75
MIN_HOMOGRAPHY_MATCHES = 12
MAX_GOOD_MATCHES = 120
MAGSAC_REPROJECTION_THRESHOLD = 3.0

ECC_REFINEMENT_MAX_DIM = 480
ECC_MAX_ITERS = 80
ECC_EPSILON = 1e-6

# ---------------------------------------------------------------------------
# Illumination & diff configuration
# ---------------------------------------------------------------------------
CLAHE_CLIP_LIMIT = 2.0
CLAHE_TILE_GRID_SIZE = (8, 8)
DIFF_BLUR_KERNEL = (13, 13)
DIFF_BACKGROUND_DIVISOR = 0.28

# ---------------------------------------------------------------------------
# Deviation scoring. Genuine capture variations (exposure, perspective,
# resolution) spread deviation uniformly across all card zones, while content
# tampering concentrates in one zone — so the score combines the global mean,
# the hottest zone, and a boost that fires only when that zone dominates.
# ---------------------------------------------------------------------------
SCORE_WEIGHT_GLOBAL_MEAN = 150.0
SCORE_WEIGHT_ZONE_PEAK = 0.9
CONCENTRATION_MEDIAN_SMOOTHING = 2.0
CONCENTRATION_RATIO_THRESHOLD = 2.5
CONCENTRATION_BOOST_FACTOR = 1.6
CRITICAL_ZONE_BOOST = 12.0
CRITICAL_ZONE_SCORE_THRESHOLD = 22.0
ZONE_ALERT_MEAN_THRESHOLD = 16.0
REFERENCE_ANOMALY_SCORE_THRESHOLD = 32.0
MAX_REPORTED_ZONES = 4

# Security-critical zones trigger a stronger tampering interpretation.
CRITICAL_ZONES = {
    "photo", "qr_code", "signature", "roll_number", "personal_fields",
    "name_line", "father_line", "course_line", "validity_line",
    "dob_line", "mobile_line", "address_block",
}

# ---------------------------------------------------------------------------
# Standard card layout zones (fractions of the rectified card: x, y, w, h),
# measured from the canonical genuine reference templates.
# ---------------------------------------------------------------------------
CARD_LAYOUT_ZONES: Dict[str, Dict[str, Tuple[float, float, float, float]]] = {
    "front": {
        "header_brand":  (0.00, 0.000, 1.00, 0.190),
        "photo":         (0.25, 0.200, 0.42, 0.300),
        "name_line":     (0.04, 0.495, 0.92, 0.065),
        "father_line":   (0.04, 0.560, 0.92, 0.060),
        "course_line":   (0.04, 0.620, 0.92, 0.060),
        "validity_line": (0.04, 0.675, 0.92, 0.050),
        "qr_code":       (0.09, 0.700, 0.31, 0.200),
        "signature":     (0.60, 0.670, 0.30, 0.220),
        "roll_number":   (0.03, 0.880, 0.94, 0.110),
    },
    "back": {
        "dob_line":        (0.02, 0.040, 0.96, 0.060),
        "blood_group_line": (0.02, 0.100, 0.96, 0.050),
        "mobile_line":     (0.02, 0.145, 0.96, 0.050),
        "address_block":   (0.02, 0.190, 0.96, 0.380),
        "notice_text":     (0.00, 0.610, 1.00, 0.130),
        "address_footer":  (0.01, 0.750, 0.98, 0.210),
    },
}

# Module-level cache: rectified reference templates keyed by path+mtime.
_RECTIFIED_REF_CACHE: Dict[str, np.ndarray] = {}


def _load_reference_templates() -> Dict[str, np.ndarray]:
    templates: Dict[str, np.ndarray] = {}
    for side, filename in REFERENCE_TEMPLATE_FILES.items():
        path = os.path.join(REFERENCE_DIR, filename)
        img = cv2.imread(path)
        if img is not None:
            templates[side] = img
    return templates


def _rectify_card(image: np.ndarray, return_transform: bool = False):
    """Perspective-rectify a card photo; falls back to the input when the
    detected quad would unexpectedly crop away part of the card.

    When return_transform is True, also returns the 3x3 matrix mapping input
    coordinates to rectified coordinates (None when no warp was applied)."""
    detection = detect_document(image)
    warped = detection.warped_image
    if not detection.success:
        return (image, None) if return_transform else image
    if warped.shape[0] < image.shape[0] * 0.85 or warped.shape[1] < image.shape[1] * 0.85:
        # Quad collapsed onto an inner structure (e.g. photo box) — unsafe.
        return (image, None) if return_transform else image
    if return_transform:
        return warped, detection.transform_matrix
    return warped


def _get_rectified_reference(path: str) -> Optional[np.ndarray]:
    mtime = os.path.getmtime(path)
    cache_key = f"{path}:{mtime}"
    cached = _RECTIFIED_REF_CACHE.get(cache_key)
    if cached is not None:
        return cached
    raw = cv2.imread(path)
    if raw is None:
        return None
    rectified = _rectify_card(raw)
    _RECTIFIED_REF_CACHE[cache_key] = rectified
    return rectified


def _normalize_illumination(image_bgr: np.ndarray) -> np.ndarray:
    """CLAHE local contrast normalization to suppress lighting/shadow deltas.
    Returns a float32 grayscale in [0, 1]."""
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=CLAHE_CLIP_LIMIT, tileGridSize=CLAHE_TILE_GRID_SIZE)
    equalized = clahe.apply(gray)
    return equalized.astype(np.float32) / 255.0


def _orb_keypoints(gray: np.ndarray):
    orb = cv2.ORB_create(nfeatures=ORB_ALIGN_FEATURES, scaleFactor=1.2, nlevels=8)
    return orb.detectAndCompute(gray, None)


def _align_query_to_reference(
    query_image: np.ndarray,
    ref_image: np.ndarray,
) -> Tuple[np.ndarray, str, Optional[np.ndarray]]:
    """Align the query card onto the reference frame.

    Pipeline: ORB ratio-test matching -> MAGSAC homography -> ECC affine
    refinement. Falls back to a plain resize when feature alignment fails.

    Returns:
        (aligned_bgr, alignment_status, forward_transform)

        forward_transform is the 3x3 matrix mapping query-frame coordinates to
        reference-frame coordinates (homography composed with the ECC affine
        refinement), or None when alignment fell back to a plain resize. It is
        used to warp localization maps back onto the uploaded image geometry.
    """
    h_ref, w_ref = ref_image.shape[:2]
    q_gray = cv2.cvtColor(query_image, cv2.COLOR_BGR2GRAY)
    r_gray = cv2.cvtColor(ref_image, cv2.COLOR_BGR2GRAY)

    kp_q, des_q = _orb_keypoints(q_gray)
    kp_r, des_r = _orb_keypoints(r_gray)

    aligned = None
    status = "resize_fallback"
    forward_transform: Optional[np.ndarray] = None

    if des_q is not None and des_r is not None and len(des_q) >= 10 and len(des_r) >= 10:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
        knn = bf.knnMatch(des_q, des_r, k=2)
        good = [m for m, n in (pair for pair in knn if len(pair) == 2)
                if m.distance < LOWES_RATIO_THRESHOLD * n.distance]
        good = sorted(good, key=lambda m: m.distance)[:MAX_GOOD_MATCHES]

        if len(good) >= MIN_HOMOGRAPHY_MATCHES:
            src_pts = np.float32([kp_q[m.queryIdx].pt for m in good]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp_r[m.trainIdx].pt for m in good]).reshape(-1, 1, 2)
            try:
                H, _ = cv2.findHomography(
                    src_pts, dst_pts,
                    cv2.USAC_MAGSAC, MAGSAC_REPROJECTION_THRESHOLD,
                    maxIters=5000, confidence=0.995,
                )
            except Exception:
                H, _ = cv2.findHomography(src_pts, dst_pts, cv2.RANSAC, MAGSAC_REPROJECTION_THRESHOLD)
            if H is not None:
                aligned = cv2.warpPerspective(query_image, H, (w_ref, h_ref))
                status = "homography_magsac"
                forward_transform = H.copy()

    if aligned is None:
        aligned = cv2.resize(query_image, (w_ref, h_ref))

    # ECC affine refinement (sub-pixel alignment of text/geometry).
    ecc_warp = _ecc_refine_warp(aligned, ref_image)
    if ecc_warp is not None:
        aligned = cv2.warpAffine(
            aligned, ecc_warp, (w_ref, h_ref),
            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        )
        status += "+ecc"
        if forward_transform is not None:
            # ECC uses inverse-map conventions: refined(x) = aligned(ecc_warp @ x).
            # Forward map query -> reference frame = ecc_warp^-1 ∘ H.
            ecc_3x3 = np.vstack([ecc_warp, [0.0, 0.0, 1.0]])
            forward_transform = np.linalg.inv(ecc_3x3) @ forward_transform

    return aligned, status, forward_transform


def _ecc_refine_warp(aligned: np.ndarray, ref_image: np.ndarray) -> Optional[np.ndarray]:
    """Compute an ECC affine refinement warp (2x3, inverse-map convention) on a
    downscaled pair. Returned only if it strictly reduces the mean absolute
    difference; translation components are scaled back to full resolution."""
    h_ref, w_ref = ref_image.shape[:2]
    aligned_gray = cv2.cvtColor(aligned, cv2.COLOR_BGR2GRAY)
    ref_gray = cv2.cvtColor(ref_image, cv2.COLOR_BGR2GRAY)

    scale = min(1.0, ECC_REFINEMENT_MAX_DIM / max(h_ref, w_ref))
    if scale < 1.0:
        small_a = cv2.resize(aligned_gray, None, fx=scale, fy=scale)
        small_r = cv2.resize(ref_gray, None, fx=scale, fy=scale)
    else:
        small_a, small_r = aligned_gray, ref_gray

    warp = np.eye(2, 3, dtype=np.float32)
    criteria = (cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, ECC_MAX_ITERS, ECC_EPSILON)
    try:
        _, warp = cv2.findTransformECC(small_r, small_a, warp, cv2.MOTION_AFFINE, criteria)
    except Exception:
        return None

    warp_full = warp.copy()
    warp_full[0, 2] /= scale
    warp_full[1, 2] /= scale

    diff_before = float(np.mean(cv2.absdiff(aligned_gray, ref_gray)))
    try:
        warped_gray = cv2.warpAffine(
            aligned_gray, warp_full, (w_ref, h_ref),
            flags=cv2.INTER_LINEAR | cv2.WARP_INVERSE_MAP,
        )
    except Exception:
        return None
    diff_after = float(np.mean(cv2.absdiff(warped_gray, ref_gray)))

    if diff_after < diff_before:
        return warp_full
    return None


def _select_reference_side(
    query_image: np.ndarray,
    templates: Dict[str, np.ndarray],
    ref_type: str,
) -> str:
    if ref_type in templates:
        return ref_type

    # Auto: pick the side sharing the most ORB features with the query.
    orb = cv2.ORB_create(nfeatures=1500)
    q_gray = cv2.cvtColor(query_image, cv2.COLOR_BGR2GRAY)
    _, des_q = orb.detectAndCompute(q_gray, None)

    best_side, best_matches = "front", -1
    if des_q is not None:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        for side, r_img in templates.items():
            r_gray = cv2.cvtColor(r_img, cv2.COLOR_BGR2GRAY)
            _, des_r = orb.detectAndCompute(r_gray, None)
            if des_r is None:
                continue
            matches = bf.match(des_q, des_r)
            if len(matches) > best_matches:
                best_matches = len(matches)
                best_side = side
    return best_side


def _zone_mean_diffs(
    diff_norm: np.ndarray,
    side: str,
) -> Dict[str, float]:
    """Mean deviation inside each standard card layout zone."""
    h, w = diff_norm.shape[:2]
    zones = CARD_LAYOUT_ZONES.get(side, {})
    scores: Dict[str, float] = {}
    for zone_name, (fx, fy, fw, fh) in zones.items():
        x1 = int(np.clip(fx * w, 0, w - 1))
        y1 = int(np.clip(fy * h, 0, h - 1))
        x2 = int(np.clip((fx + fw) * w, x1 + 2, w))
        y2 = int(np.clip((fy + fh) * h, y1 + 2, h))
        scores[zone_name] = float(np.mean(diff_norm[y1:y2, x1:x2])) * 100.0
    return scores


def compare_with_reference(
    query_image: np.ndarray,
    ref_type: str = "auto"
) -> Tuple[np.ndarray, float, List[str], Dict[str, Any]]:
    """
    Compare a query ID card against the canonical genuine reference standard
    (front/back KIET ID templates) using rectified templates, illumination-
    normalized structural diffing, and card-layout zone deviation analysis.

    Args:
        query_image: BGR uint8 NumPy array of the query card.
        ref_type: "front", "back", or "auto" (selects the best matching side).

    Returns:
        diff_map: 2D float32 array normalized to [0.0, 1.0] in the query frame.
        reference_score: Scalar anomaly score [0.0 - 100.0] vs the genuine standard.
        anomalies: List of structural/layout deviation notes.
        match_details: Dict of reference match metrics (alignment, zones, score).
    """
    if query_image is None or query_image.size == 0:
        raise ValueError("Invalid query image provided for reference comparison.")

    templates = {
        side: _get_rectified_reference(os.path.join(REFERENCE_DIR, filename))
        for side, filename in REFERENCE_TEMPLATE_FILES.items()
    }
    templates = {side: img for side, img in templates.items() if img is not None}

    if not templates:
        h, w = query_image.shape[:2]
        return np.zeros((h, w), dtype=np.float32), 0.0, [], {"status": "No reference templates stored"}

    # Rectify the query card (no-op for already-rectified input).
    query_rectified, rectify_transform = _rectify_card(query_image, return_transform=True)

    selected_side = _select_reference_side(query_rectified, templates, ref_type)
    ref_img = templates[selected_side]
    h_ref, w_ref = ref_img.shape[:2]

    # 1. Feature alignment: ORB ratio test -> MAGSAC homography -> ECC refine.
    aligned_q, alignment_status, forward_transform = _align_query_to_reference(query_rectified, ref_img)

    # 2. Illumination-normalized structural difference.
    aligned_gray = _normalize_illumination(aligned_q)
    r_gray = _normalize_illumination(ref_img)

    diff = np.abs(aligned_gray - r_gray)
    diff_blurred = cv2.GaussianBlur(diff, DIFF_BLUR_KERNEL, 0)

    # Suppress global exposure/contrast shifts via background subtraction.
    diff_med = float(np.median(diff_blurred))
    diff_norm = np.clip((diff_blurred - diff_med) / DIFF_BACKGROUND_DIVISOR, 0.0, 1.0)

    # 3. Deviation scoring: global mean + hottest zone, with a boost that
    # fires only when the deviation concentrates in a single card zone.
    mean_diff = float(np.mean(diff_norm))

    zone_scores = _zone_mean_diffs(diff_norm, selected_side)
    zone_peak = max(zone_scores.values(), default=0.0)
    worst_zone = max(zone_scores, key=zone_scores.get, default="none")

    zone_median = float(np.median(list(zone_scores.values()))) if zone_scores else 0.0
    concentration = zone_peak / (zone_median + CONCENTRATION_MEDIAN_SMOOTHING)

    raw_ref_score = (mean_diff * SCORE_WEIGHT_GLOBAL_MEAN) + (zone_peak * SCORE_WEIGHT_ZONE_PEAK)
    if concentration >= CONCENTRATION_RATIO_THRESHOLD:
        raw_ref_score += zone_peak * CONCENTRATION_BOOST_FACTOR
    if worst_zone in CRITICAL_ZONES and zone_peak >= CRITICAL_ZONE_SCORE_THRESHOLD:
        raw_ref_score += CRITICAL_ZONE_BOOST
    reference_score = float(min(100.0, max(0.0, raw_ref_score)))

    # 4. Anomaly reporting.
    anomalies: List[str] = []
    if reference_score > REFERENCE_ANOMALY_SCORE_THRESHOLD:
        anomalies.append(
            f"Structural layout deviation detected against genuine {selected_side.upper()} "
            f"reference standard (Anomaly Score: {reference_score:.1f}%)"
        )

    flagged_zones = sorted(
        ((name, score) for name, score in zone_scores.items()
         if score >= ZONE_ALERT_MEAN_THRESHOLD),
        key=lambda item: item[1], reverse=True,
    )[:MAX_REPORTED_ZONES]
    for zone_name, zone_score in flagged_zones:
        critical = " (security-critical zone)" if zone_name in CRITICAL_ZONES else ""
        anomalies.append(
            f"Card zone '{zone_name}' deviates from genuine reference standard "
            f"(zone deviation: {zone_score:.1f}%){critical}"
        )

    # Map the diff map back onto the UPLOADED image geometry. Warping through
    # the inverse alignment transform (not a plain resize) keeps the heat
    # anchored to the actual tampered pixels for tilted / perspective-shifted
    # uploads. The rectification warp (raw photo -> rectified card) is composed
    # in as well. The full symmetric diff is kept here so content-vs-content
    # tampering (a replaced photo) localizes as strongly as added or erased
    # strokes; ghost-free presentation is handled at render time.
    h_q, w_q = query_image.shape[:2]
    total_forward = forward_transform
    if total_forward is not None and rectify_transform is not None:
        total_forward = total_forward @ rectify_transform
    if total_forward is not None:
        diff_map_q = cv2.warpPerspective(
            diff_norm, total_forward, (w_q, h_q),
            flags=cv2.INTER_LINEAR,
        )
        diff_map_q = np.nan_to_num(diff_map_q, nan=0.0).astype(np.float32)
    else:
        diff_map_q = cv2.resize(diff_norm, (w_q, h_q))

    match_details = {
        "matched_reference_side": selected_side,
        "reference_standard": "KIET Group of Institutions student ID (canonical genuine template)",
        "reference_dimensions": [w_ref, h_ref],
        "alignment_status": alignment_status,
        "reference_deviation_score": round(reference_score, 2),
        "zone_deviation_scores": {k: round(v, 2) for k, v in zone_scores.items()},
        "flagged_zones": [
            {"zone": zone_name, "deviation": round(zone_score, 2),
             "critical": zone_name in CRITICAL_ZONES}
            for zone_name, zone_score in flagged_zones
        ],
        "worst_zone": worst_zone,
    }

    return diff_map_q, reference_score, anomalies, match_details
