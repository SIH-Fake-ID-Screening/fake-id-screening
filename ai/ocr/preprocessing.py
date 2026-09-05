"""
ai/ocr/preprocessing.py
------------------------
OpenCV & Pillow image preprocessing helper functions.
Implements grayscale conversion, contrast enhancement, denoising,
adaptive thresholding, and deskewing. Safe fallback included.
"""

import logging
from typing import Tuple, Optional, Union
from PIL import Image
import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
    HAS_CV2 = True
except ImportError:
    HAS_CV2 = False
    logger.warning("opencv-python (cv2) not found in environment. Image preprocessing will use PIL fallbacks.")


def preprocess_image(image_path_or_array: Union[str, np.ndarray]) -> Tuple[np.ndarray, np.ndarray]:
    """
    Load an image and generate preprocessed variations optimized for OCR.

    Parameters
    ----------
    image_path_or_array : str | np.ndarray
        Path to image file or existing BGR image array.

    Returns
    -------
    Tuple[np.ndarray, np.ndarray]:
        (original_bgr_image, preprocessed_image)
    """
    if isinstance(image_path_or_array, str):
        if HAS_CV2:
            img = cv2.imread(image_path_or_array)
            if img is None:
                raise FileNotFoundError(f"Could not load image file from path: {image_path_or_array}")
        else:
            try:
                pil_img = Image.open(image_path_or_array).convert("RGB")
                img = np.array(pil_img)[:, :, ::-1]  # Convert RGB to BGR numpy array
            except Exception as exc:
                raise FileNotFoundError(f"Could not load image file from path: {image_path_or_array}") from exc
    elif isinstance(image_path_or_array, np.ndarray):
        img = image_path_or_array.copy()
    else:
        raise ValueError("Invalid input: expected file path string or numpy ndarray")

    original = img.copy()

    if not HAS_CV2:
        return original, original

    try:
        # 1. Resize if image is extremely small or very large for OCR
        h, w = img.shape[:2]
        if max(h, w) > 2400:
            scale = 2400.0 / max(h, w)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
        elif min(h, w) < 400:
            scale = 800.0 / max(min(h, w), 1)
            img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_CUBIC)

        # 2. Convert to Grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 3. Contrast Enhancement via CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # 4. Denoising
        denoised = cv2.fastNlMeansDenoising(enhanced, h=10)

        # 5. Deskewing calculation
        deskewed = deskew_image(denoised)

        preprocessed_bgr = cv2.cvtColor(deskewed, cv2.COLOR_GRAY2BGR)
        return original, preprocessed_bgr

    except Exception as exc:
        logger.warning("Error during image preprocessing: %s. Falling back to original image.", exc)
        return original, original


def deskew_image(gray_img: np.ndarray) -> np.ndarray:
    """Detect and correct document skew up to +/- 45 degrees."""
    try:
        # Find all foreground pixels via Otsu threshold
        _, thresh = cv2.threshold(gray_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        coords = np.column_stack(np.where(thresh > 0))

        if len(coords) < 50:
            return gray_img

        angle = cv2.minAreaRect(coords)[-1]
        if angle < -45:
            angle = -(90 + angle)
        else:
            angle = -angle

        # If rotation is minimal (< 0.5 degrees or > 45 degrees), do not deskew
        if abs(angle) < 0.5 or abs(angle) > 45.0:
            return gray_img

        h, w = gray_img.shape[:2]
        center = (w // 2, h // 2)
        M = cv2.getRotationMatrix2D(center, angle, 1.0)
        deskewed = cv2.warpAffine(
            gray_img, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE
        )
        return deskewed
    except Exception:
        return gray_img
