import cv2
import numpy as np
from typing import Tuple, List

# Named constant configuration (no bare numbers)
LAPLACIAN_KERNEL_SIZE = 3
LOCAL_BLUR_WINDOW = (15, 15)
PERCENTILE_LOW = 10.0
PERCENTILE_HIGH = 90.0
MORPH_OPEN_KERNEL_SIZE = (5, 5)
BORDER_SUPPRESSION_MARGIN_RATIO = 0.02
MIN_CONNECTED_COMPONENT_AREA = 50.0


def analyze_ai_spectrum(image: np.ndarray) -> Tuple[np.ndarray, float, List[str]]:
    """
    Detect AI-generated document elements and synthetic image artifacts using 2D FFT spectral analysis
    and residual gradient noise distribution analysis.

    Pipeline details:
      - Analyzes 2D FFT Fourier ring magnitude for periodic spectral upsampling grid spikes.
      - Uses robust percentile statistics for local Laplacian variance, morphological opening/closing,
        and edge/border suppression to prevent normal high-gradient text from triggering AI flags.

    Returns:
        ai_map: 2D float32 array normalized to [0.0, 1.0] showing synthetic AI anomaly regions.
        ai_score: Scalar score [0.0 - 100.0] indicating AI generative model likelihood.
        ai_anomalies: List of specific AI spectral indicators detected.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image input for AI spectrum analysis.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
    h, w = gray.shape

    ai_anomalies: List[str] = []

    # 1. 2D FFT Spectral Grid Artifact Analysis
    f_transform = np.fft.fft2(gray)
    f_shift = np.fft.fftshift(f_transform)
    magnitude_spectrum = 20 * np.log(np.abs(f_shift) + 1e-5)

    cy, cx = h // 2, w // 2
    r_outer = min(cy, cx) * 0.8
    r_inner = min(cy, cx) * 0.3

    y_grid, x_grid = np.ogrid[:h, :w]
    dist_from_center = np.sqrt((y_grid - cy)**2 + (x_grid - cx)**2)
    angle_grid = np.abs(np.arctan2(y_grid - cy, x_grid - cx))

    axis_mask = (np.abs(angle_grid) > 0.09) & (np.abs(angle_grid - np.pi/2) > 0.09) & (np.abs(angle_grid - np.pi) > 0.09)
    ring_mask = (dist_from_center >= r_inner) & (dist_from_center <= r_outer) & axis_mask

    ring_spectrum = magnitude_spectrum[ring_mask]
    spectral_max_to_mean = float(np.max(ring_spectrum) / (np.mean(ring_spectrum) + 1e-5))

    if spectral_max_to_mean > 2.5:
        ai_anomalies.append("Generative AI periodic spectral lattice artifact detected in high-frequency domain")

    # 2. Robust Percentile Local Laplacian Variance & Texture Analysis
    laplacian = cv2.Laplacian(gray, cv2.CV_32F, ksize=LAPLACIAN_KERNEL_SIZE)
    abs_laplacian = np.abs(laplacian)

    local_lap_mean = cv2.blur(abs_laplacian, LOCAL_BLUR_WINDOW)
    local_lap_sq = cv2.blur(abs_laplacian**2, LOCAL_BLUR_WINDOW)
    local_lap_var = np.maximum(0, local_lap_sq - local_lap_mean**2)

    # Edge Mask: Suppress sharp text strokes and line borders
    edges = cv2.Canny((gray * 255).astype(np.uint8), 50, 150)
    edge_dilated = cv2.dilate(edges, cv2.getStructuringElement(cv2.MORPH_RECT, (7, 7)))
    edge_mask = (edge_dilated > 0).astype(np.float32)

    # Compute robust percentile statistics on non-edge background pixels
    non_edge_var = local_lap_var[edge_mask == 0]
    if len(non_edge_var) > 100:
        p_low = float(np.percentile(non_edge_var, PERCENTILE_LOW))
        p_high = float(np.percentile(non_edge_var, PERCENTILE_HIGH))
    else:
        p_low = float(np.percentile(local_lap_var, PERCENTILE_LOW))
        p_high = float(np.percentile(local_lap_var, PERCENTILE_HIGH))

    p_range = max(p_high - p_low, 1e-4)
    raw_anomaly = np.clip((local_lap_var - p_high) / p_range, 0.0, 1.0)

    # Suppress sharp text edge regions
    raw_anomaly[edge_mask > 0] *= 0.10

    # 3. Morphological Cleanup & Connected Component Filtering
    kernel_open = cv2.getStructuringElement(cv2.MORPH_RECT, MORPH_OPEN_KERNEL_SIZE)
    cleaned = cv2.morphologyEx((raw_anomaly * 255.0).astype(np.uint8), cv2.MORPH_OPEN, kernel_open)
    cleaned_float = cleaned.astype(np.float32) / 255.0

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats((cleaned_float > 0.35).astype(np.uint8))
    ai_map = np.zeros_like(cleaned_float)

    for i in range(1, num_labels):
        comp_area = stats[i, cv2.CC_STAT_AREA]
        if comp_area >= MIN_CONNECTED_COMPONENT_AREA:
            ai_map[labels == i] = cleaned_float[labels == i]

    # Border Margin Suppression
    b_margin_h = int(h * BORDER_SUPPRESSION_MARGIN_RATIO)
    b_margin_w = int(w * BORDER_SUPPRESSION_MARGIN_RATIO)
    if b_margin_h > 0:
        ai_map[:b_margin_h, :] = 0.0
        ai_map[-b_margin_h:, :] = 0.0
    if b_margin_w > 0:
        ai_map[:, :b_margin_w] = 0.0
        ai_map[:, -b_margin_w:] = 0.0

    # Compute AI Generative Score
    max_anomaly = float(np.max(ai_map))
    mean_anomaly = float(np.mean(ai_map))

    raw_ai_score = (max_anomaly * 25.0) + (mean_anomaly * 200.0) + (15.0 if ai_anomalies else 0.0)
    ai_score = float(min(100.0, max(0.0, raw_ai_score)))

    return ai_map, ai_score, ai_anomalies
