import cv2
import numpy as np
from PIL import Image
import io
from typing import Tuple

# Named configuration variables (no bare numbers)
ELA_RE_SAVE_QUALITY = 90
ELA_SCALE_FACTOR = 15.0
GAUSSIAN_PRE_BLUR_KERNEL = (7, 7)
MORPH_EROSION_KERNEL = (5, 5)
LOCAL_BLUR_WINDOW = (15, 15)
ELA_PERCENTILE_THRESHOLD = 97.0
MAP_NORMALIZATION_DIVISOR = 0.40
BORDER_MARGIN_RATIO = 0.02
MIN_SPATIAL_REGION_AREA = 40.0
BASE_GRAPHIC_VARIANCE_THRESHOLD = 0.30
ELA_SCORE_MULTIPLIER = 350.0


def analyze_ela(
    image: np.ndarray,
    quality: int = ELA_RE_SAVE_QUALITY,
    scale: float = ELA_SCALE_FACTOR
) -> Tuple[np.ndarray, float]:
    """
    Perform Error Level Analysis (ELA) on an input image.

    Pipeline details:
      - Resaves image at JPEG quality=90 and calculates absolute pixel error difference scaled by 15.0.
      - Applies Gaussian pre-blur (7x7) and morphological erosion (5x5).
      - Uses percentile-based thresholding (97th percentile), border margin suppression (2%),
        and connected component filtering to isolate spatially coherent tampering anomalies.

    Args:
        image: BGR uint8 NumPy array.
        quality: Compression quality factor for resaving (1-100).
        scale: Error difference amplification scale factor.

    Returns:
        ela_map: 2D float32 array normalized to [0.0, 1.0] highlighting error discrepancies.
        ela_anomaly_score: Scalar score [0.0 - 100.0] indicating forensic compression inconsistency.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image input for ELA analysis.")

    h, w = image.shape[:2]

    rgb_img = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb_img)

    buffer = io.BytesIO()
    pil_img.save(buffer, format='JPEG', quality=quality)
    buffer.seek(0)

    resaved_pil = Image.open(buffer)
    resaved_np = cv2.cvtColor(np.array(resaved_pil), cv2.COLOR_RGB2BGR)

    diff = cv2.absdiff(image.astype(np.float32), resaved_np.astype(np.float32))
    scaled_diff = np.clip(diff * scale, 0, 255).astype(np.uint8)

    ela_gray = cv2.cvtColor(scaled_diff, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    ela_raw_map = cv2.GaussianBlur(ela_gray, GAUSSIAN_PRE_BLUR_KERNEL, 0)

    eroded_ela = cv2.erode(ela_raw_map, cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_EROSION_KERNEL))
    local_ela = cv2.blur(eroded_ela, LOCAL_BLUR_WINDOW)

    # Robust Percentile-Based High-Energy Error Extraction
    pct_val = float(np.percentile(local_ela, ELA_PERCENTILE_THRESHOLD))
    global_med = float(np.median(local_ela))

    ela_diff_map = np.abs(local_ela - global_med)
    max_diff = float(np.max(ela_diff_map))

    if max_diff > 1e-5:
        raw_ela_map = np.clip(ela_diff_map / MAP_NORMALIZATION_DIVISOR, 0.0, 1.0)
    else:
        raw_ela_map = np.zeros_like(ela_gray)

    # Edge suppression: suppress ordinary document text strokes
    edges = cv2.Canny((ela_gray * 255).astype(np.uint8), 50, 150)
    edge_dilated = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5)))
    raw_ela_map[edge_dilated > 0] *= 0.25

    # Connected Components Spatial Coherence Filter
    binary_ela = (raw_ela_map > (pct_val / max(max_diff, 1e-4) * 0.45)).astype(np.uint8)
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary_ela)
    ela_map = np.zeros_like(raw_ela_map)

    for i in range(1, num_labels):
        comp_area = stats[i, cv2.CC_STAT_AREA]
        if comp_area >= MIN_SPATIAL_REGION_AREA:
            ela_map[labels == i] = raw_ela_map[labels == i]

    # Border Margin Suppression
    b_h = int(h * BORDER_MARGIN_RATIO)
    b_w = int(w * BORDER_MARGIN_RATIO)
    if b_h > 0:
        ela_map[:b_h, :] = 0.0
        ela_map[-b_h:, :] = 0.0
    if b_w > 0:
        ela_map[:, :b_w] = 0.0
        ela_map[:, -b_w:] = 0.0

    raw_score = (max_diff - BASE_GRAPHIC_VARIANCE_THRESHOLD) * ELA_SCORE_MULTIPLIER
    ela_anomaly_score = float(min(100.0, max(0.0, raw_score)))

    return ela_map, ela_anomaly_score
