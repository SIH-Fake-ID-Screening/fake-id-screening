import cv2
import numpy as np
from typing import Union, Tuple, Optional
from PIL import Image
import io
import logging

logger = logging.getLogger(__name__)


def load_image(source: Union[str, bytes, np.ndarray, Image.Image]) -> np.ndarray:
    """
    Load an image from a file path, bytes, PIL Image, or existing numpy array.
    Returns a BGR uint8 NumPy array (standard OpenCV format).
    """
    if isinstance(source, np.ndarray):
        if source.ndim == 2:
            return cv2.cvtColor(source, cv2.COLOR_GRAY2BGR)
        elif source.shape[2] == 4:
            return cv2.cvtColor(source, cv2.COLOR_BGRA2BGR)
        return source.copy()

    if isinstance(source, Image.Image):
        img_rgb = np.array(source.convert('RGB'))
        return cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    if isinstance(source, bytes):
        nparr = np.frombuffer(source, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Failed to decode image from provided bytes.")
        return img

    if isinstance(source, str):
        img = cv2.imread(source, cv2.IMREAD_COLOR)
        if img is None:
            raise FileNotFoundError(f"Could not read image at path: {source}")
        return img

    raise TypeError(f"Unsupported image source type: {type(source)}")


def convert_colorspace(image: np.ndarray, target: str = 'RGB') -> np.ndarray:
    """Convert BGR image to target color space ('RGB', 'GRAY', 'YCrCb', 'HSV')."""
    target = target.upper()
    if target == 'RGB':
        return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    elif target == 'GRAY':
        return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    elif target == 'YCRCB':
        return cv2.cvtColor(image, cv2.COLOR_BGR2YCrCb)
    elif target == 'HSV':
        return cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    elif target == 'BGR':
        return image.copy()
    else:
        raise ValueError(f"Unsupported color space: {target}")


def resize_and_align(
    image: np.ndarray,
    target_size: Tuple[int, int] = (1024, 1024),
    preserve_aspect: bool = True
) -> Tuple[np.ndarray, float, Tuple[int, int]]:
    """
    Resize image to target dimensions.
    Returns: (resized_image, scale_factor, pad_offsets)
    """
    h, w = image.shape[:2]
    target_w, target_h = target_size

    if not preserve_aspect:
        resized = cv2.resize(image, (target_w, target_h), interpolation=cv2.INTER_AREA)
        return resized, 1.0, (0, 0)

    scale = min(target_w / w, target_h / h)
    new_w = int(w * scale)
    new_h = int(h * scale)

    resized_raw = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)

    # Pad to exact target size
    pad_w = target_w - new_w
    pad_h = target_h - new_h
    top, bottom = pad_h // 2, pad_h - (pad_h // 2)
    left, right = pad_w // 2, pad_w - (pad_w // 2)

    padded = cv2.copyMakeBorder(
        resized_raw, top, bottom, left, right, cv2.BORDER_CONSTANT, value=[0, 0, 0]
    )
    return padded, scale, (left, top)


def normalize_image(image: np.ndarray) -> np.ndarray:
    """Normalize pixel values to float32 [0.0, 1.0]."""
    return image.astype(np.float32) / 255.0
