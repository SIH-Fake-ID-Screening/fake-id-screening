import cv2
import numpy as np
from typing import List, Dict, Any, Optional

from forensic.reference_matching import CARD_LAYOUT_ZONES

# Zone blobs: a card zone starts glowing when its deviation from the genuine
# reference standard crosses this percentage.
ZONE_BLOB_MIN_DEVIATION = 10.0


def generate_overlay(
    image: np.ndarray,
    heatmap: np.ndarray,
    regions: List[Dict[str, Any]],
    alpha: float = 0.72,
    glow_strength: float = 1.25,
    preserve_detail: bool = True,
    tampered: Optional[bool] = None,
    risk_score: Optional[float] = None,
) -> np.ndarray:
    """
    Generate an enhanced, professional forensic overlay:
    - Edge-aware bilateral filtering to preserve crisp document boundaries
    - Selective alpha blending (un-tampered areas remain natural, suspicious areas glow)
    - Perceptually uniform TURBO color map
    - Glowing multi-ring contours around detected suspicious regions
    - Integrated forensic HUD banner and risk color legend

    Args:
        image: Original BGR uint8 NumPy array.
        heatmap: 2D float32 array normalized to [0.0 - 1.0].
        regions: List of region dictionaries with bounding boxes.
        alpha: Blend weight for heatmap overlay.
        glow_strength: Additional glow emphasis for high-risk bounding boxes.
        preserve_detail: Whether to keep document detail when blending the heatmap.
        tampered: Optional overall tampering verdict for the HUD banner.
        risk_score: Optional overall risk score [0-100] for the HUD banner.

    Returns:
        overlay: BGR uint8 NumPy array with enhanced visual annotations.
    """
    h, w = image.shape[:2]

    heatmap = np.clip(np.asarray(heatmap, dtype=np.float32), 0.0, 1.0)
    if preserve_detail:
        heatmap_smooth = cv2.bilateralFilter((heatmap * 255.0).astype(np.float32), d=9, sigmaColor=75, sigmaSpace=75)
    else:
        heatmap_smooth = cv2.GaussianBlur((heatmap * 255.0).astype(np.float32), (11, 11), 0)
    heatmap_norm = np.clip(heatmap_smooth / 255.0, 0.0, 1.0)
    heatmap_enhanced = np.clip(np.power(heatmap_norm, 1.35) * 1.15, 0.0, 1.0)

    heatmap_uint8 = (heatmap_enhanced * 255.0).astype(np.uint8)
    color_heatmap = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_TURBO)

    focus_mask = np.clip((heatmap_enhanced - 0.08) / 0.92, 0.0, 1.0)
    mask_weight = focus_mask[:, :, np.newaxis] * alpha
    blended = (image.astype(np.float32) * (1.0 - mask_weight) + color_heatmap.astype(np.float32) * mask_weight).astype(np.uint8)

    for reg in regions:
        x, y, rw, rh = reg["bbox"]
        peak = float(reg.get("peak_score", 0.0))
        reg_id = reg["region_id"]

        if peak >= 70.0:
            core_color = (0, 0, 255)
            glow_color = (0, 120, 255)
        elif peak >= 45.0:
            core_color = (0, 165, 255)
            glow_color = (0, 215, 255)
        else:
            core_color = (0, 220, 220)
            glow_color = (0, 255, 255)

        x1 = max(0, x - 2)
        y1 = max(0, y - 2)
        x2 = min(w - 1, x + rw + 2)
        y2 = min(h - 1, y + rh + 2)

        thickness = max(2, int(glow_strength * 2.0))
        cv2.rectangle(blended, (x1, y1), (x2, y2), glow_color, thickness + 1)
        cv2.rectangle(blended, (x, y), (x + rw, y + rh), core_color, thickness)

        label = f"Region #{reg_id} [{peak:.1f}% Risk]"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = max(0.45, min(0.7, w / 1200.0))
        (lbl_w, lbl_h), _ = cv2.getTextSize(label, font, font_scale, 1)

        badge_y1 = max(0, y - lbl_h - 10)
        badge_x2 = min(w, x + lbl_w + 12)
        cv2.rectangle(blended, (x, badge_y1), (badge_x2, y), core_color, -1)
        cv2.putText(blended, label, (x + 6, max(lbl_h + 2, y - 4)), font, font_scale, (255, 255, 255), 1, cv2.LINE_AA)

    hud_h = max(40, int(h * 0.07))
    hud_bg = np.zeros((hud_h, w, 3), dtype=np.uint8)
    cv2.rectangle(hud_bg, (0, 0), (w, hud_h), (16, 16, 16), -1)

    max_risk = max([r["peak_score"] for r in regions], default=0.0)
    risk_txt = f" — RISK: {risk_score:.1f}%" if risk_score is not None else f" — PEAK RISK: {max_risk:.1f}%"
    if max_risk >= 70.0:
        status_txt = f"SUSPICIOUS REGION DETECTED{risk_txt}"
        status_color = (50, 50, 255)
    elif tampered and (risk_score or 0.0) >= 45.0:
        status_txt = f"TAMPERING DETECTED{risk_txt}"
        status_color = (50, 50, 255)
    elif len(regions) > 0:
        status_txt = f"MODERATE ANOMALY DETECTED{risk_txt}"
        status_color = (0, 165, 255)
    elif tampered:
        status_txt = f"TAMPERING SUSPECTED — STANDARD DEVIATION{risk_txt}"
        status_color = (0, 165, 255)
    else:
        status_txt = "INTEGRITY CHECK PASSED — NO ANOMALIES DETECTED"
        status_color = (50, 205, 50)

    font_hud = cv2.FONT_HERSHEY_SIMPLEX
    hud_scale = max(0.45, min(0.7, w / 1100.0))
    cv2.putText(hud_bg, status_txt, (20, int(hud_h * 0.65)), font_hud, hud_scale, status_color, 2, cv2.LINE_AA)

    legend_w = int(w * 0.22)
    legend_h = int(hud_h * 0.35)
    legend_x = w - legend_w - 20
    legend_y = int(hud_h * 0.3)

    if legend_w > 60:
        legend_bar = np.linspace(0, 255, legend_w, dtype=np.uint8).reshape(1, legend_w)
        legend_color = cv2.applyColorMap(legend_bar, cv2.COLORMAP_TURBO)
        legend_color = cv2.resize(legend_color, (legend_w, legend_h))
        hud_bg[legend_y:legend_y+legend_h, legend_x:legend_x+legend_w] = legend_color
        cv2.rectangle(hud_bg, (legend_x, legend_y), (legend_x + legend_w, legend_y + legend_h), (200, 200, 200), 1)

    return np.vstack([hud_bg, blended])


def render_heatmap_overlay(
    image: np.ndarray,
    heatmap: Optional[np.ndarray] = None,
    regions: Optional[List[Dict[str, Any]]] = None,
    zone_scores: Optional[Dict[str, float]] = None,
    layout_side: Optional[str] = None,
    alpha: float = 0.72,
    base_level: float = 0.14,
) -> np.ndarray:
    """
    Render a dashboard-ready forensic thermal map in the standard presentation
    style: a deep-blue "Low Anomaly" base across the whole card with smooth,
    well-defined hot blobs over every tampered area.

    The thermal layer is built from two clean parametric sources — never from
    raw diff texture, so no reference-template content can bleed through:
      1. Zone blobs: every standard card zone whose deviation from the genuine
         reference exceeds ZONE_BLOB_MIN_DEVIATION gets a soft blob scaled by
         how far it deviates (photo, name line, QR, ...).
      2. Field blobs: the fused heat field, soft-thresholded and heavily
         smoothed, catches tampering outside the standard zones.

    The output has EXACTLY the same dimensions as the input image and contains
    no banner, so it can be displayed side-by-side with the original. Numbered
    red badges tie each blob to the report's region list.
    """
    h, w = image.shape[:2]
    heat = np.zeros((h, w), dtype=np.float32)

    # ---- 1. Zone-driven blobs -------------------------------------------
    zones = CARD_LAYOUT_ZONES.get(layout_side, {}) if layout_side else {}
    for zone_name, (fx, fy, fw, fh) in zones.items():
        deviation = float((zone_scores or {}).get(zone_name, 0.0))
        if deviation < ZONE_BLOB_MIN_DEVIATION:
            continue
        amplitude = float(np.clip((deviation - 8.0) / 30.0, 0.35, 1.0))
        x1 = int(np.clip((fx + fw * 0.05) * w, 0, w - 2))
        y1 = int(np.clip((fy + fh * 0.07) * h, 0, h - 2))
        x2 = int(np.clip((fx + fw * 0.95) * w, x1 + 2, w))
        y2 = int(np.clip((fy + fh * 0.93) * h, y1 + 2, h))
        heat[y1:y2, x1:x2] = np.maximum(heat[y1:y2, x1:x2], amplitude)

    # ---- 2. Smoothed heat-field blobs ------------------------------------
    if heatmap is not None:
        hm = np.clip(np.asarray(heatmap, dtype=np.float32), 0.0, 1.0)
        if hm.shape[:2] != (h, w):
            hm = cv2.resize(hm, (w, h), interpolation=cv2.INTER_LINEAR)
        field_peak = float(np.max(hm))
        if field_peak > 1e-6:
            hm = hm / field_peak
        soft = np.where(hm > 0.24, hm, 0.0).astype(np.float32)
        k_open = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 9))
        soft = cv2.morphologyEx(soft, cv2.MORPH_OPEN, k_open)
        soft = cv2.morphologyEx(soft, cv2.MORPH_CLOSE,
                                cv2.getStructuringElement(cv2.MORPH_RECT, (17, 17)))
        field_kernel = max(51, int(min(h, w) * 0.09))
        if field_kernel % 2 == 0:
            field_kernel += 1
        soft = cv2.GaussianBlur(soft, (field_kernel, field_kernel), 0)
        soft_peak = float(np.max(soft))
        if soft_peak > 1e-6:
            soft = np.power(np.clip(soft / soft_peak, 0.0, 1.0), 1.4)
            heat = np.maximum(heat, soft)

    # ---- Fuse and smooth into clean thermal blobs -------------------------
    final_kernel = max(41, int(min(h, w) * 0.06))
    if final_kernel % 2 == 0:
        final_kernel += 1
    heat = cv2.GaussianBlur(heat, (final_kernel, final_kernel), 0)
    heat_peak = float(np.max(heat))
    if heat_peak > 1e-6:
        heat = np.power(np.clip(heat / heat_peak, 0.0, 1.0), 1.3)
    else:
        heat = np.zeros_like(heat)

    # Deep-blue low-anomaly base; blobs rise through green/yellow to red.
    thermal = base_level + (1.0 - base_level) * heat
    color_heatmap = cv2.applyColorMap((thermal * 255.0).astype(np.uint8), cv2.COLORMAP_TURBO)

    # Tint the document surface strongly, the surrounding background barely.
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    doc_mask = np.clip((gray.astype(np.float32) - 35.0) / 55.0, 0.15, 1.0)[:, :, np.newaxis]

    weight = alpha * doc_mask
    blended = image.astype(np.float32) * (1.0 - weight) + color_heatmap.astype(np.float32) * weight
    blended = np.clip(blended, 0, 255).astype(np.uint8)

    # ---- Numbered badges ---------------------------------------------------
    # Small red circle badges tie each blob to the report's region list
    # ("1 -> Replaced Photograph"). Outlines are drawn only for compact
    # regions; merged band regions get their badge at the hottest pixel.
    field_for_center = heatmap
    for reg in regions or []:
        x, y, rw, rh = [int(v) for v in reg.get("bbox", [0, 0, 0, 0])]
        reg_id = int(reg.get("region_id", 0))
        badge_r = max(9, min(w, h) // 90)
        area_frac = (rw * rh) / float(h * w)
        if 0.0 < area_frac <= 0.12:
            cv2.rectangle(blended, (max(0, x - 3), max(0, y - 3)),
                          (min(w - 1, x + rw + 3), min(h - 1, y + rh + 3)),
                          (40, 40, 230), 2)
            cx = max(badge_r + 1, x - 2)
            cy = max(badge_r + 1, y - 2)
        else:
            # Merged band region: place the badge at its hottest pixel.
            cx, cy = x + rw // 2, y + rh // 2
            if field_for_center is not None:
                fh = np.clip(np.asarray(field_for_center, dtype=np.float32), 0, 1)
                if fh.shape[:2] != (h, w):
                    fh = cv2.resize(fh, (w, h))
                x1, y1 = max(0, x), max(0, y)
                x2, y2 = min(w, x + rw), min(h, y + rh)
                if x2 > x1 and y2 > y1:
                    sub = fh[y1:y2, x1:x2]
                    dy, dx = np.unravel_index(np.argmax(sub), sub.shape)
                    cx, cy = x1 + int(dx), y1 + int(dy)
            cx = int(np.clip(cx, badge_r + 1, w - badge_r - 1))
            cy = int(np.clip(cy, badge_r + 1, h - badge_r - 1))
        cv2.circle(blended, (cx, cy), badge_r, (40, 40, 230), -1)
        cv2.putText(blended, str(reg_id), (cx - badge_r // 2 - 1, cy + badge_r // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, max(0.4, badge_r / 22.0), (255, 255, 255),
                    2, cv2.LINE_AA)

    return blended
