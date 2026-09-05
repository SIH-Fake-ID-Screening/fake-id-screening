import cv2
import numpy as np
from typing import Dict, Any


def assess_quality(image: np.ndarray) -> Dict[str, Any]:
    """
    Assess document image quality indicators:
    - Blur score (Laplacian variance)
    - Noise level estimation (Median Absolute Deviation of high pass residual)
    - Dynamic range / contrast assessment
    - Mean brightness
    """
    if image.ndim == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image.copy()

    # 1. Blur Score (Variance of Laplacian)
    laplacian_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    is_blurry = laplacian_var < 100.0

    # 2. Noise level estimation
    # High-pass filter via Gaussian blur subtraction
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    residual = gray.astype(np.float32) - blurred.astype(np.float32)
    noise_sigma = float(np.median(np.abs(residual - np.median(residual))) / 0.6745)

    # 3. Brightness and Contrast
    mean_brightness = float(np.mean(gray))
    std_contrast = float(np.std(gray))

    return {
        "blur_score": laplacian_var,
        "is_blurry": is_blurry,
        "noise_sigma": noise_sigma,
        "mean_brightness": mean_brightness,
        "std_contrast": std_contrast,
        "resolution": {"width": gray.shape[1], "height": gray.shape[0]}
    }
