import logging
import numpy as np
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

LOW_RISK_MAX = 20.0
MEDIUM_RISK_MAX = 45.0
HIGH_RISK_MAX = 70.0


def compute_risk_score(
    ela_score: float,
    srm_score: float,
    copy_move_score: float,
    metadata_score: float,
    suspicious_regions: List[Dict[str, Any]],
    reference_score: float = 0.0
) -> Dict[str, Any]:
    """
    Perform multi-factor evidence fusion incorporating reference template comparison
    to compute standardized Tampering Risk Score.
    """
    # Weighted fusion of ELA, SRM/AI, Copy-Move, and Reference Template Matching
    forensic_raw = (0.30 * ela_score) + (0.30 * srm_score) + (0.30 * reference_score) + (0.10 * copy_move_score)

    max_region_score = max(
        [float(r.get("mean_score", r.get("peak_score", 0.0))) for r in suspicious_regions],
        default=0.0,
    )
    if max_region_score > 35.0:
        regional_boost = (max_region_score - 35.0) * 0.22
    else:
        regional_boost = 0.0

    forensic_score = float(min(100.0, max(0.0, forensic_raw + regional_boost)))
    capped_meta = float(min(15.0, metadata_score))
    # Calibrated reference-standard deviation adds a capped direct boost:
    # genuine re-captures score <= ~20 while content tampers score >= ~40.
    reference_boost = float(min(15.0, reference_score * 0.20))
    final_risk = float(min(100.0, max(0.0, forensic_score + capped_meta + reference_boost)))

    if final_risk < LOW_RISK_MAX:
        risk_level = "LOW"
    elif final_risk < MEDIUM_RISK_MAX:
        risk_level = "MEDIUM"
    elif final_risk < HIGH_RISK_MAX:
        risk_level = "HIGH"
    else:
        risk_level = "CRITICAL"

    has_region_signal = len(suspicious_regions) >= 3 and max_region_score >= 68.0
    strong_risk = final_risk >= 45.0 and forensic_score >= 40.0

    compact_regions = 0
    for region in suspicious_regions:
        x, y, w, h = region["bbox"]
        area = float(w * h)
        if area <= 0:
            continue
        aspect_ratio = max(w / max(h, 1.0), h / max(w, 1.0))
        if area <= 2500.0 and aspect_ratio <= 3.0:
            compact_regions += 1

    region_cluster = len(suspicious_regions) >= 2 and compact_regions >= 2 and max_region_score >= 75.0 and forensic_score >= 45.0
    high_region = max_region_score >= 85.0 and forensic_score >= 45.0
    moderate_cluster = len(suspicious_regions) >= 4 and forensic_score >= 45.0
    reference_tamper = (reference_score >= 40.0) and (final_risk >= 30.0)

    tampered = strong_risk or region_cluster or high_region or moderate_cluster or reference_tamper

    trigger_reason = [
        name for name, fired in [
            ("strong_risk", strong_risk),
            ("region_cluster", region_cluster),
            ("high_region", high_region),
            ("moderate_cluster", moderate_cluster),
            ("reference_tamper", reference_tamper),
        ] if fired
    ] or ["none"]

    score_spread = abs(ela_score - srm_score)
    agreement_factor = max(0.5, 1.0 - (score_spread / 100.0))
    confidence = float(round(min(0.99, max(0.50, agreement_factor * 0.75 + (final_risk / 300.0))), 2))

    return {
        "tampered": tampered,
        "risk_score": round(final_risk, 2),
        "risk_level": risk_level,
        "forensic_score": round(forensic_score, 2),
        "metadata_score": round(capped_meta, 2),
        "confidence": confidence,
        "trigger_reason": trigger_reason,
        "diagnostics": {
            "ela_score": round(ela_score, 2),
            "srm_score": round(srm_score, 2),
            "reference_score": round(reference_score, 2),
            "copy_move_score": round(copy_move_score, 2),
            "metadata_score_raw": round(metadata_score, 2),
            "reference_boost": round(reference_boost, 2),
            "max_region_score": round(max_region_score, 2),
            "region_count_raw": len(suspicious_regions),
            "regional_boost": round(regional_boost, 2),
            "score_spread_ela_srm": round(score_spread, 2),
            "agreement_factor": round(agreement_factor, 3),
            "has_region_signal_unused": has_region_signal,
        },
    }
