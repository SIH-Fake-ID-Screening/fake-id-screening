import cv2
import numpy as np
from typing import Tuple, List, Dict, Any, Optional

from forensic.reference_matching import CARD_LAYOUT_ZONES

# ---------------------------------------------------------------------------
# Channel weights. When a reference-standard diff map is available it is the
# primary localization evidence — it highlights exactly the pixels that differ
# from the genuine card — so it dominates the fused tampering heatmap. ELA,
# SRM and copy-move remain as independent confirmation channels.
# ---------------------------------------------------------------------------
HEATMAP_WEIGHT_REF = 0.45
HEATMAP_WEIGHT_ELA = 0.20
HEATMAP_WEIGHT_SRM = 0.25
HEATMAP_WEIGHT_CM = 0.10

# Fallback weights when no reference comparison is available (generic mode).
FALLBACK_WEIGHT_ELA = 0.45
FALLBACK_WEIGHT_SRM = 0.40
FALLBACK_WEIGHT_CM = 0.15

# Zone gating: a card zone whose deviation score reaches ZONE_GATE_FULL_SCORE
# passes the reference diff at full strength; matching zones are attenuated to
# ZONE_GATE_MIN so alignment halos cannot masquerade as tampering.
ZONE_GATE_FULL_SCORE = 15.0
ZONE_GATE_MIN = 0.08
ZONE_GATE_BLUR_KERNEL = (31, 31)

BORDER_MARGIN_RATIO = 0.02
# Broad tampering (a replaced photo) produces moderate-but-wide fused heat,
# so the region threshold sits below the sharp-stroke level; genuine cards
# stay clean because zone gating already suppresses their heat.
BINARIZATION_THRESHOLD = 0.26
MIN_RELATIVE_REGION_AREA = 0.0004  # 0.04% of document area
MAX_ASPECT_RATIO = 4.5             # Rejects thin line noise (generic mode)
# In reference mode the diff is zone-gated, so a wide-thin region is a genuinely
# altered text line (e.g. a rewritten name) rather than print noise.
MAX_ASPECT_RATIO_REFERENCE_MODE = 12.0
MAX_TOP_REGIONS = 5                # Upstream top regions cap


def build_zone_gate(
    zone_scores: Optional[Dict[str, float]],
    layout_side: Optional[str],
    shape: Tuple[int, int],
) -> np.ndarray:
    """Build a per-pixel multiplier map from card layout zone deviations.

    Zones that deviate from the genuine standard keep their reference diff at
    full strength; zones that match the standard are suppressed to
    ZONE_GATE_MIN. Returns all-ones when zone data is unavailable.
    """
    h, w = shape[:2]
    if not zone_scores or layout_side not in CARD_LAYOUT_ZONES:
        return np.ones((h, w), dtype=np.float32)

    gate = np.full((h, w), ZONE_GATE_MIN, dtype=np.float32)
    for zone_name, (fx, fy, fw, fh) in CARD_LAYOUT_ZONES[layout_side].items():
        mult = float(np.clip(
            float(zone_scores.get(zone_name, 0.0)) / ZONE_GATE_FULL_SCORE,
            ZONE_GATE_MIN, 1.0,
        ))
        x1, y1 = int(fx * w), int(fy * h)
        x2, y2 = int(min(w, (fx + fw) * w)), int(min(h, (fy + fh) * h))
        if x2 > x1 and y2 > y1:
            gate[y1:y2, x1:x2] = mult

    return cv2.GaussianBlur(gate, ZONE_GATE_BLUR_KERNEL, 0)


def fuse_heatmaps(
    ela_map: np.ndarray,
    srm_map: np.ndarray,
    copy_move_map: np.ndarray,
    reference_map: Optional[np.ndarray] = None,
    zone_scores: Optional[Dict[str, float]] = None,
    layout_side: Optional[str] = None,
) -> Tuple[np.ndarray, List[Dict[str, Any]]]:
    """
    Fuse multi-spectral forensic response maps into a continuous 2D tampering
    localization heatmap that highlights where the document is actually
    tampered.

    Pipeline details:
      - Reference-standard diff channel (primary localization evidence),
        zone-gated by per-zone deviation against the genuine standard.
      - ELA / SRM / copy-move channels as independent confirmation evidence.
      - Multi-scale Gaussian pyramid blending + border margin suppression.
      - Morphological cleanup and connected component extraction with honest
        region scoring: 0.50*mean + 0.30*max + 0.20*spatial_coherence.

    Returns:
        fused_heatmap: 2D float32 array [0.0 - 1.0] in the rectified frame.
        suspicious_regions: Top post-filter region dicts with bbox + scores.
    """
    h, w = ela_map.shape[:2]
    img_area = float(h * w)

    def _fit(channel: Optional[np.ndarray]) -> np.ndarray:
        if channel is None:
            return np.zeros((h, w), dtype=np.float32)
        return cv2.resize(channel, (w, h)) if channel.shape[:2] != (h, w) else channel

    ela_res = _fit(ela_map)
    srm_res = _fit(srm_map)
    cm_res = _fit(copy_move_map)
    ref_res = _fit(reference_map)

    has_reference = bool(np.any(ref_res > 0.0))
    if has_reference:
        zone_gate = build_zone_gate(zone_scores, layout_side, (h, w))
        ref_localization = np.clip(ref_res * zone_gate, 0.0, 1.0)
        # Auxiliary channels are softened by the same zone gate: inside zones
        # that match the genuine standard their texture/print noise is damped
        # to 25%, so the fused map concentrates on truly deviating areas.
        aux_gate = 0.25 + 0.75 * zone_gate
        fused_raw = (
            (HEATMAP_WEIGHT_REF * ref_localization)
            + (HEATMAP_WEIGHT_ELA * ela_res * aux_gate)
            + (HEATMAP_WEIGHT_SRM * srm_res * aux_gate)
            + (HEATMAP_WEIGHT_CM * cm_res * aux_gate)
        )
    else:
        fused_raw = (
            (FALLBACK_WEIGHT_ELA * ela_res)
            + (FALLBACK_WEIGHT_SRM * srm_res)
            + (FALLBACK_WEIGHT_CM * cm_res)
        )

    # 1. Multi-scale Gaussian Pyramid Blending
    g1 = cv2.GaussianBlur(fused_raw, (5, 5), 0)
    g2 = cv2.GaussianBlur(fused_raw, (15, 15), 0)
    fused_pyramid = (0.65 * g1) + (0.35 * g2)

    # 2. Border Margin Suppression
    b_h = int(h * BORDER_MARGIN_RATIO)
    b_w = int(w * BORDER_MARGIN_RATIO)
    if b_h > 0:
        fused_pyramid[:b_h, :] = 0.0
        fused_pyramid[-b_h:, :] = 0.0
    if b_w > 0:
        fused_pyramid[:, :b_w] = 0.0
        fused_pyramid[:, -b_w:] = 0.0

    # Continuous Heatmap Scaling
    max_val = float(np.max(fused_pyramid))
    norm_denom = max(max_val, 0.45)
    fused_heatmap = np.clip(fused_pyramid / norm_denom, 0.0, 1.0)
    fused_heatmap = cv2.GaussianBlur(fused_heatmap, (7, 7), 0)

    # 3. Morphological Cleanup (Opening + Closing)
    binary_mask = (fused_heatmap > BINARIZATION_THRESHOLD).astype(np.uint8) * 255
    k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    k_close = cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7))
    cleaned_mask = cv2.morphologyEx(binary_mask, cv2.MORPH_OPEN, k_open)
    cleaned_mask = cv2.morphologyEx(cleaned_mask, cv2.MORPH_CLOSE, k_close)

    contours, _ = cv2.findContours(cleaned_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    suspicious_regions: List[Dict[str, Any]] = []
    min_area = max(img_area * MIN_RELATIVE_REGION_AREA, 30.0)
    max_aspect = MAX_ASPECT_RATIO_REFERENCE_MODE if has_reference else MAX_ASPECT_RATIO

    for idx, cnt in enumerate(contours):
        area = cv2.contourArea(cnt)
        if area < min_area:
            continue

        x, y, rw, rh = cv2.boundingRect(cnt)
        aspect_ratio = max(rw / max(rh, 1), rh / max(rw, 1))
        if aspect_ratio > max_aspect:  # Reject thin noise lines
            continue

        region_mask = fused_heatmap[y:y+rh, x:x+rw]
        if region_mask.size == 0:
            continue

        max_anomaly = float(np.max(region_mask))
        mean_anomaly = float(np.mean(region_mask))

        # Spatial coherence factor: compact filled regions vs sparse edge outlines
        fill_ratio = area / float(rw * rh)
        spatial_coherence = float(np.clip(fill_ratio * 1.2, 0.0, 1.0))

        # Honest Region Scoring Formula (No flat 100% clamping)
        honest_score = (0.50 * mean_anomaly) + (0.30 * max_anomaly) + (0.20 * spatial_coherence)
        honest_peak = float(round(max_anomaly * 100.0, 2))
        honest_mean = float(round(honest_score * 100.0, 2))

        suspicious_regions.append({
            "region_id": idx + 1,
            "bbox": [int(x), int(y), int(rw), int(rh)],
            "area_pixels": int(area),
            "peak_score": honest_peak,
            "mean_score": honest_mean,
            "aspect_ratio": round(aspect_ratio, 2),
            "spatial_coherence": round(spatial_coherence, 2)
        })

    # Sort by honest mean score descending and cap at MAX_TOP_REGIONS
    suspicious_regions.sort(key=lambda r: r["mean_score"], reverse=True)
    top_regions = suspicious_regions[:MAX_TOP_REGIONS]

    return fused_heatmap, top_regions
