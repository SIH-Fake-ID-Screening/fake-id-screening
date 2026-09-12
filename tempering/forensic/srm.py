import cv2
import numpy as np
from typing import Tuple


def _get_srm_filters() -> list[np.ndarray]:
    """Define standard SRM (Spatial Rich Model) 3x3 high-pass residual filter kernels."""
    k1 = np.array([
        [ 0,  0,  0],
        [-1,  2, -1],
        [ 0,  0,  0]
    ], dtype=np.float32) / 2.0

    k2 = np.array([
        [-1,  2, -1],
        [ 2, -4,  2],
        [-1,  2, -1]
    ], dtype=np.float32) / 4.0

    k3 = np.array([
        [-1,  2, -1],
        [ 0,  0,  0],
        [ 1, -2,  1]
    ], dtype=np.float32) / 4.0

    return [k1, k2, k3]


def analyze_srm(image: np.ndarray) -> Tuple[np.ndarray, float]:
    """
    Extract Spatial Rich Model (SRM) residual noise map and calculate noise variance anomaly score.

    Pipeline details:
      - Filters image with 3x3 high-pass SRM kernels and applies morphological erosion (7x7).
      - Normalizes srm_map using a 0.035 scale factor: clip(local_noise / 0.035, 0.0, 1.0).

    Args:
        image: BGR uint8 NumPy array.

    Returns:
        srm_map: 2D float32 array normalized to [0.0, 1.0] representing local residual noise magnitude.
        srm_anomaly_score: Scalar score [0.0 - 100.0] indicating spatial noise inconsistency.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image input for SRM analysis.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0

    filters = _get_srm_filters()
    residual_sum = np.zeros_like(gray)

    for filt in filters:
        filtered = cv2.filter2D(gray, -1, filt)
        residual_sum += np.abs(filtered)

    residual_avg = residual_sum / len(filters)

    # Morphological erosion with 7x7 kernel removes thin 1-3px text & circle vector borders
    eroded_residual = cv2.erode(residual_avg, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))

    # Compute regional noise magnitude map
    local_noise = cv2.blur(eroded_residual, (15, 15))

    # Normalize srm_map to [0, 1]
    max_noise = float(np.max(local_noise))
    if max_noise > 1e-5:
        srm_map = np.clip(local_noise / 0.035, 0.0, 1.0)
    else:
        srm_map = np.zeros_like(gray)

    # Compute SRM noise anomaly score
    mean_noise = float(np.mean(local_noise))
    raw_score = (mean_noise * 50000.0) + (max(0.0, max_noise - 0.005) * 2500.0)
    srm_anomaly_score = float(min(100.0, max(0.0, raw_score)))

    return srm_map, srm_anomaly_score
