import os
import logging
import threading
import numpy as np
from typing import Protocol, NamedTuple, List, Dict, Any, Optional, Tuple
import cv2

from preprocessing.document import load_image
from preprocessing.document_crop import detect_document, DocumentDetection
from forensic.ela import analyze_ela
from forensic.srm import analyze_srm
from forensic.metadata import analyze_metadata
from forensic.copy_move import analyze_copy_move
from forensic.ai_spectrum import analyze_ai_spectrum
from forensic.reference_matching import compare_with_reference
from localization.heatmap import fuse_heatmaps
from localization.overlay import generate_overlay, render_heatmap_overlay
from scoring.risk_score import compute_risk_score
from forensic.reference_matching import CARD_LAYOUT_ZONES

logger = logging.getLogger(__name__)

# Configurable constants
MIN_REGION_PEAK_SCORE = 45.0
MIN_REGION_MEAN_SCORE = 25.0
MAX_REPORTED_REGIONS = 10
REGION_MERGE_IOU = 0.25
CLEAN_HEATMAP_SUPPRESSION = 0.45
CLEAN_HEATMAP_FLOOR = 0.58


class TamperingPrediction(NamedTuple):
    tampered: bool
    risk_score: float             # [0.0 - 100.0]
    risk_level: str              # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    forensic_score: float        # Combined ELA + SRM + Copy-Move score
    metadata_score: float        # EXIF/XMP anomaly score
    confidence: float            # Forensic heuristic confidence [0.0 - 1.0]
    localization_mask: np.ndarray # 2D float array normalized [0, 1] matching image dimensions
    overlay_image: np.ndarray     # BGR image with visual annotations
    heatmap_overlay_image: np.ndarray  # BGR heatmap blended on the image, same dims as input (dashboard artifact)
    regions: List[Dict[str, Any]] # Bounding boxes and properties of suspicious regions
    metadata_anomalies: List[str]# List of detected metadata discrepancies
    trigger_reason: List[str] = []
    diagnostics: Dict[str, Any] = {}


class TamperingModel(Protocol):
    def predict(self, image: np.ndarray, filepath: Optional[str] = None) -> TamperingPrediction:
        """Analyze document image and return tampering prediction with localization mask."""
        ...


def _iou(a: Dict[str, Any], b: Dict[str, Any]) -> float:
    """IoU between two region dicts with bbox=[x, y, w, h]."""
    ax, ay, aw, ah = a["bbox"]
    bx, by, bw, bh = b["bbox"]
    ix1, iy1 = max(ax, bx), max(ay, by)
    ix2, iy2 = min(ax + aw, bx + bw), min(ay + ah, by + bh)
    iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
    inter = iw * ih
    if inter == 0:
        return 0.0
    union = aw * ah + bw * bh - inter
    return inter / union if union > 0 else 0.0


def _merge_two(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two overlapping regions into their bounding union, keeping the stronger score."""
    ax, ay, aw, ah = a["bbox"]
    bx, by, bw, bh = b["bbox"]
    x1, y1 = min(ax, bx), min(ay, by)
    x2, y2 = max(ax + aw, bx + bw), max(ay + ah, by + bh)
    merged = dict(a if a["peak_score"] >= b["peak_score"] else b)
    merged["bbox"] = [x1, y1, x2 - x1, y2 - y1]
    merged["peak_score"] = max(a["peak_score"], b["peak_score"])
    merged["mean_score"] = (a["mean_score"] + b["mean_score"]) / 2.0
    return merged


def _filter_and_merge_regions(
    regions: List[Dict[str, Any]],
    min_peak: float = MIN_REGION_PEAK_SCORE,
    min_mean: float = MIN_REGION_MEAN_SCORE,
    max_regions: int = MAX_REPORTED_REGIONS,
    merge_iou: float = REGION_MERGE_IOU,
) -> List[Dict[str, Any]]:
    """Remove low-energy noise and merge duplicate/near-duplicate regions."""
    thresholded = [
        r for r in regions
        if float(r.get("peak_score", 0.0)) >= min_peak
        or (
            float(r.get("peak_score", 0.0)) >= (min_peak * 0.8)
            and float(r.get("mean_score", 0.0)) >= min_mean
        )
    ]

    thresholded.sort(key=lambda r: r.get("peak_score", 0.0), reverse=True)
    merged: List[Dict[str, Any]] = []
    for region in thresholded:
        placed = False
        for i, existing in enumerate(merged):
            if _iou(region, existing) >= merge_iou:
                merged[i] = _merge_two(existing, region)
                placed = True
                break
        if not placed:
            merged.append(region)

    merged.sort(key=lambda r: r.get("peak_score", 0.0), reverse=True)
    return merged[:max_regions]


def _tag_region_zones(
    regions: List[Dict[str, Any]],
    shape_hw: Tuple[int, int],
    layout_side: Optional[str],
) -> None:
    """Annotate each region dict with the standard card zone containing its
    center (e.g. 'photo', 'name_line'), based on the rectified card layout."""
    if not regions or layout_side not in CARD_LAYOUT_ZONES:
        for r in regions:
            r.setdefault("zone", "unzoned")
        return
    h, w = shape_hw
    for r in regions:
        rx, ry, rw, rh = r["bbox"]
        cx = (rx + rw / 2.0) / max(w, 1)
        cy = (ry + rh / 2.0) / max(h, 1)
        zone_name = "unzoned"
        for name, (fx, fy, fw, fh) in CARD_LAYOUT_ZONES[layout_side].items():
            if fx <= cx <= fx + fw and fy <= cy <= fy + fh:
                zone_name = name
                break
        r["zone"] = zone_name


class ELASRMModel:
    """
    Active baseline forensic analyzer implementing TamperingModel Protocol.
    Fuses ELA, SRM, Copy-Move, AI spectrum, and Reference Template Matching against
    genuine front/back ID card reference standards.
    """
    def __init__(self, ela_quality: int = 90):
        self.ela_quality = ela_quality
        self.device = "cpu"
        self.active_backend = "ela_srm_reference_baseline"
        logger.info("Initialized ELASRMModel with reference template matcher.")

    def predict(self, image: np.ndarray, filepath: Optional[str] = None) -> TamperingPrediction:
        if image is None or image.size == 0:
            raise ValueError("Invalid or empty image provided to ELASRMModel.predict().")

        h_orig, w_orig = image.shape[:2]

        # 1. Document Detection & Perspective Warp Crop Stage
        doc_det = detect_document(image)
        work_img = doc_det.warped_image

        # 2. Multi-Spectral Forensic Extraction
        ela_map, ela_score = analyze_ela(work_img, quality=self.ela_quality)
        srm_map, srm_score = analyze_srm(work_img)
        cm_map, cm_score, cm_count = analyze_copy_move(work_img)
        ai_map, ai_score, ai_anomalies = analyze_ai_spectrum(work_img)

        # 3. Reference Template Comparison Engine against Genuine Front/Back Cards
        ref_map, ref_score, ref_anomalies, ref_details = compare_with_reference(work_img, ref_type="auto")

        meta_dict, meta_anomalies, meta_score = analyze_metadata(filepath)
        all_anomalies = meta_anomalies + ai_anomalies + ref_anomalies

        if not doc_det.success:
            all_anomalies.append("Document boundary detection failed; analyzed full frame image")

        combined_srm_ai_ref = (0.50 * srm_score) + (0.20 * ai_score) + (0.30 * ref_score)

        # Fuse heatmaps: the zone-gated reference diff drives tamper localization
        doc_fused_heatmap, doc_regions = fuse_heatmaps(
            ela_map, srm_map, cm_map,
            reference_map=ref_map,
            zone_scores=ref_details.get("zone_deviation_scores"),
            layout_side=ref_details.get("matched_reference_side"),
        )
        doc_regions = _filter_and_merge_regions(doc_regions)

        # Tag each region with the standard card zone it falls in (rectified
        # frame shares the reference layout geometry) for dashboard reporting.
        _tag_region_zones(doc_regions, work_img.shape[:2], ref_details.get("matched_reference_side"))

        # Map back to original image frame coordinates if polygon warped
        if doc_det.success and doc_det.polygon is not None:
            inv_M = cv2.getPerspectiveTransform(
                np.array([[0, 0], [work_img.shape[1] - 1, 0], [work_img.shape[1] - 1, work_img.shape[0] - 1], [0, work_img.shape[0] - 1]], dtype=np.float32),
                doc_det.polygon.astype(np.float32)
            )
            fused_heatmap = cv2.warpPerspective(doc_fused_heatmap, inv_M, (w_orig, h_orig), flags=cv2.INTER_LINEAR)
            
            regions: List[Dict[str, Any]] = []
            for r in doc_regions:
                rx, ry, rw, rh = r["bbox"]
                pts = np.array([[rx, ry], [rx + rw, ry], [rx + rw, ry + rh], [rx, ry + rh]], dtype=np.float32).reshape(-1, 1, 2)
                transformed_pts = cv2.perspectiveTransform(pts, inv_M).reshape(4, 2)
                x_min, y_min = np.min(transformed_pts, axis=0)
                x_max, y_max = np.max(transformed_pts, axis=0)
                x1, y1 = int(max(0, x_min)), int(max(0, y_min))
                x2, y2 = int(min(w_orig, x_max)), int(min(h_orig, y_max))
                r_mapped = dict(r)
                r_mapped["bbox"] = [x1, y1, x2 - x1, y2 - y1]
                regions.append(r_mapped)
        else:
            fused_heatmap = cv2.resize(doc_fused_heatmap, (w_orig, h_orig)) if doc_fused_heatmap.shape[:2] != (h_orig, w_orig) else doc_fused_heatmap
            regions = doc_regions

        # Sequential region ids (1..N by score rank) keep dashboard labels clean.
        for seq_id, r in enumerate(regions, start=1):
            r["region_id"] = seq_id

        risk_result = compute_risk_score(
            ela_score=ela_score,
            srm_score=combined_srm_ai_ref,
            copy_move_score=cm_score,
            metadata_score=meta_score,
            suspicious_regions=regions,
            reference_score=ref_score,
        )

        final_conf = risk_result["confidence"]
        if not doc_det.success:
            final_conf = float(round(max(0.35, final_conf - 0.15), 2))

        if not risk_result["tampered"]:
            fused_heatmap = np.clip(fused_heatmap * CLEAN_HEATMAP_SUPPRESSION, 0.0, 1.0)
            fused_heatmap = np.where(fused_heatmap > CLEAN_HEATMAP_FLOOR, fused_heatmap, 0.0)
            overlay_img = generate_overlay(
                image, fused_heatmap, regions, alpha=0.45, glow_strength=0.8,
                tampered=risk_result["tampered"], risk_score=risk_result["risk_score"],
            )
        else:
            overlay_img = generate_overlay(
                image, fused_heatmap, regions,
                tampered=risk_result["tampered"], risk_score=risk_result["risk_score"],
            )

        # Clean dashboard artifact: forensic thermal map on the image, same
        # dims — deep-blue base + hot blobs on tampered zones + numbered
        # region badges.
        heatmap_overlay_img = render_heatmap_overlay(
            image, fused_heatmap, regions=regions,
            zone_scores=ref_details.get("zone_deviation_scores"),
            layout_side=ref_details.get("matched_reference_side"),
        )

        diagnostics = risk_result.get("diagnostics", {})
        diagnostics["document_detection"] = doc_det.status
        diagnostics["reference_match_details"] = ref_details
        diagnostics["forensic_confidence_heuristic"] = final_conf
        diagnostics["pretrained_deep_learning_model_loaded"] = False

        return TamperingPrediction(
            tampered=risk_result["tampered"],
            risk_score=risk_result["risk_score"],
            risk_level=risk_result["risk_level"],
            forensic_score=risk_result["forensic_score"],
            metadata_score=meta_score,
            confidence=final_conf,
            localization_mask=fused_heatmap,
            overlay_image=overlay_img,
            heatmap_overlay_image=heatmap_overlay_img,
            regions=regions,
            metadata_anomalies=all_anomalies,
            trigger_reason=risk_result.get("trigger_reason", ["none"]),
            diagnostics=diagnostics,
        )


class TruForModel:
    """Adapter interface for TruFor (baseline fallback when weights unpopulated)."""
    _PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DEFAULT_WEIGHTS_PATH = os.path.join(_PACKAGE_DIR, "models", "weights", "trufor.pth")

    def __init__(self, weights_path: str = DEFAULT_WEIGHTS_PATH):
        self.weights_path = weights_path
        self.is_loaded = False
        self.device = "cpu"
        self.active_backend = "ela_srm_reference_baseline"
        self._fallback_model = ELASRMModel()

        if os.path.exists(self.weights_path):
            logger.info("TruFor weights found at '%s', but model architecture is unpopulated.", self.weights_path)
        else:
            logger.info("TruFor weights not found at '%s'. Using active reference baseline.", self.weights_path)

    def predict(self, image: np.ndarray, filepath: Optional[str] = None) -> TamperingPrediction:
        return self._fallback_model.predict(image, filepath)


_model_lock = threading.Lock()
_cached_model: Optional[TamperingModel] = None


def get_default_model() -> TamperingModel:
    """Return singleton model instance."""
    global _cached_model
    if _cached_model is not None:
        return _cached_model

    with _model_lock:
        if _cached_model is None:
            _cached_model = TruForModel()
    return _cached_model


def detect_tampering(
    image: np.ndarray,
    filepath: Optional[str] = None,
    model: Optional[TamperingModel] = None,
) -> Dict[str, Any]:
    """Public entry point for document tampering analysis."""
    if isinstance(image, str):
        image = load_image(image)

    if image is None or image.size == 0:
        raise ValueError("Invalid image provided to detect_tampering().")

    active_model = model or get_default_model()
    prediction = active_model.predict(image, filepath=filepath)

    suspicious_regions: List[Dict[str, Any]] = []
    for index, region in enumerate(prediction.regions):
        bbox = region.get("bbox", [0, 0, 0, 0])
        if len(bbox) != 4:
            continue
        x, y, w, h = [int(v) for v in bbox]
        suspicious_regions.append({
            "region_id": index,
            "x": x,
            "y": y,
            "width": w,
            "height": h,
            "confidence": float(np.clip(region.get("peak_score", 0.0) / 100.0, 0.0, 1.0)),
            "peak_score": float(region.get("peak_score", 0.0)),
            "mean_score": float(region.get("mean_score", 0.0)),
        })

    tampering_probability = float(np.clip(prediction.risk_score / 100.0, 0.0, 1.0))
    forensic_confidence = float(np.clip(prediction.confidence, 0.0, 1.0))

    result: Dict[str, Any] = {
        "tampered": bool(prediction.tampered),
        "tampering_probability": tampering_probability,
        "forensic_confidence": forensic_confidence,
        "confidence": forensic_confidence,
        "risk_score": float(prediction.risk_score),
        "risk_level": prediction.risk_level,
        "forensic_score": float(prediction.forensic_score),
        "metadata_score": float(prediction.metadata_score),
        "suspicious_regions": suspicious_regions,
        "metadata_anomalies": list(prediction.metadata_anomalies),
        "backend_name": getattr(active_model, "active_backend", getattr(active_model, "__class__", type(active_model)).__name__),
        "device": getattr(active_model, "device", "cpu"),
        "localization_mask": prediction.localization_mask,
        "overlay_image": prediction.overlay_image,
        "trigger_reason": list(getattr(prediction, "trigger_reason", ["none"])),
        "diagnostics": dict(getattr(prediction, "diagnostics", {})),
    }
    return result
