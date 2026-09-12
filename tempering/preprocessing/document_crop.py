import cv2
import numpy as np
from typing import NamedTuple, Tuple, Optional
import os
import logging

logger = logging.getLogger(__name__)


class DocumentDetection(NamedTuple):
    success: bool
    cropped_image: np.ndarray
    warped_image: np.ndarray
    polygon: Optional[np.ndarray]        # [4, 2] float32 array: TL, TR, BR, BL
    transform_matrix: Optional[np.ndarray]# [3, 3] perspective matrix
    confidence: float                    # [0.0 - 1.0] detection confidence
    status: str                          # "quad_success", "full_card_crop", "failed"


def _order_points(pts: np.ndarray) -> np.ndarray:
    """Order points in TL, TR, BR, BL order."""
    rect = np.zeros((4, 2), dtype=np.float32)
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]

    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    return rect


# Full-bleed detection: the frame border band is uniform card surface when the
# document was photographed edge-to-edge with no visible background.
FULL_BLEED_BORDER_STD_MAX = 45.0
FULL_BLEED_BORDER_MATCH_TOLERANCE = 45.0
FULL_BLEED_BORDER_RATIO = 0.025


def _is_full_bleed_document(gray: np.ndarray) -> bool:
    """Return True when the frame border band is uniform card surface, meaning
    the document extends beyond every frame edge (no background ring)."""
    h, w = gray.shape[:2]
    b = max(2, int(min(h, w) * FULL_BLEED_BORDER_RATIO))
    border = np.concatenate([
        gray[:b, :].ravel(), gray[-b:, :].ravel(),
        gray[:, :b].ravel(), gray[:, -b:].ravel(),
    ])
    interior = gray[h // 5: 4 * h // 5, w // 5: 4 * w // 5]

    if float(border.std()) > FULL_BLEED_BORDER_STD_MAX:
        return False
    if abs(float(border.mean()) - float(interior.mean())) > FULL_BLEED_BORDER_MATCH_TOLERANCE:
        return False
    return True


def detect_document(image: np.ndarray, save_debug: bool = False, debug_dir: str = "modules/tampering/results/debug") -> DocumentDetection:
    """
    Find the largest document/card quadrilateral or foreground document segment,
    and return perspective-corrected rectified document image.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image input for document detection.")

    h, w = image.shape[:2]
    img_area = float(h * w)

    # Grayscale & Blur
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)

    # Multi-method edge detection (Canny + Otsu + Morphological Closing)
    canny = cv2.Canny(blurred, 30, 150)
    _, otsu = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    combined_edges = cv2.bitwise_or(canny, otsu)

    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(combined_edges, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    best_poly: Optional[np.ndarray] = None
    best_area = 0.0
    best_cnt = None

    # Strategy 1: Explicit 4-point Quadrilateral Contour Approximation.
    # The document is the dominant object in frame — reject small interior
    # structures (e.g. a header bar or text block) that merely form a convex
    # quad, and reject sliver quads that cannot be a card/document shape.
    MIN_QUAD_AREA_RATIO = 0.30
    MAX_QUAD_ASPECT_RATIO = 3.5
    for cnt in contours[:10]:
        area = cv2.contourArea(cnt)
        if area < img_area * MIN_QUAD_AREA_RATIO:
            continue

        peri = cv2.arcLength(cnt, True)
        approx = cv2.approxPolyDP(cnt, 0.02 * peri, True)

        quad = None
        if len(approx) == 4 and cv2.isContourConvex(approx):
            quad = approx.reshape(4, 2).astype(np.float32)
        else:
            hull = cv2.convexHull(cnt)
            peri_h = cv2.arcLength(hull, True)
            approx_h = cv2.approxPolyDP(hull, 0.025 * peri_h, True)
            if len(approx_h) == 4 and cv2.isContourConvex(approx_h):
                quad = approx_h.reshape(4, 2).astype(np.float32)

        if quad is not None:
            ordered = _order_points(quad)
            w_top = np.linalg.norm(ordered[1] - ordered[0])
            w_bot = np.linalg.norm(ordered[2] - ordered[3])
            h_left = np.linalg.norm(ordered[3] - ordered[0])
            h_right = np.linalg.norm(ordered[2] - ordered[1])
            quad_w = max(w_top, w_bot)
            quad_h = max(h_left, h_right)
            aspect = max(quad_w / max(quad_h, 1.0), quad_h / max(quad_w, 1.0))
            if aspect > MAX_QUAD_ASPECT_RATIO:
                continue

            best_poly = quad
            best_area = area
            best_cnt = cnt
            break

    # Strategy 2: Bounding Box / Full Card Crop Fallback for Cropped Scans
    status = "quad_success"
    if best_poly is None and len(contours) > 0:
        largest_cnt = contours[0]
        area = cv2.contourArea(largest_cnt)
        if area >= img_area * 0.70:
            # Card fills almost the entire image frame
            x, y, bw, bh = cv2.boundingRect(largest_cnt)
            best_poly = np.array([[x, y], [x + bw, y], [x + bw, y + bh], [x, y + bh]], dtype=np.float32)
            best_area = float(bw * bh)
            best_cnt = largest_cnt
            status = "full_card_crop"
        elif _is_full_bleed_document(gray):
            # Card/document surface extends to every frame edge (no background
            # ring visible) — the whole frame is the document.
            best_poly = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
            best_area = img_area
            status = "full_frame_card"
        else:
            # Full image frame fallback
            best_poly = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
            best_area = img_area
            status = "full_frame_fallback"

    if best_poly is None:
        best_poly = np.array([[0, 0], [w - 1, 0], [w - 1, h - 1], [0, h - 1]], dtype=np.float32)
        best_area = img_area
        status = "failed"

    ordered_poly = _order_points(best_poly)
    warped, M = perspective_correct(image, ordered_poly)

    area_ratio = min(1.0, best_area / (img_area * 0.85))
    detection_conf = float(round(min(0.98, max(0.50, 0.50 + area_ratio * 0.48)), 2))

    # Bounding crop
    x_min, y_min = np.min(ordered_poly, axis=0).astype(int)
    x_max, y_max = np.max(ordered_poly, axis=0).astype(int)
    x1, y1 = max(0, x_min), max(0, y_min)
    x2, y2 = min(w, x_max), min(h, y_max)
    cropped = image[y1:y2, x1:x2].copy()

    # Render Phase 1 Debug Artifacts if requested
    if save_debug:
        os.makedirs(debug_dir, exist_ok=True)
        # 01_original.png
        cv2.imwrite(os.path.join(debug_dir, "01_original.png"), image)
        # 02_edges.png
        cv2.imwrite(os.path.join(debug_dir, "02_edges.png"), closed)
        # 03_document_contour.png
        contour_img = image.copy()
        cv2.polylines(contour_img, [ordered_poly.astype(np.int32)], True, (0, 255, 0), 3)
        cv2.imwrite(os.path.join(debug_dir, "03_document_contour.png"), contour_img)
        # 04_document_mask.png
        mask = np.zeros((h, w), dtype=np.uint8)
        cv2.fillPoly(mask, [ordered_poly.astype(np.int32)], 255)
        cv2.imwrite(os.path.join(debug_dir, "04_document_mask.png"), mask)
        # 05_rectified_document.png
        cv2.imwrite(os.path.join(debug_dir, "05_rectified_document.png"), warped)

    return DocumentDetection(
        success=(status in ["quad_success", "full_card_crop", "full_frame_card"]),
        cropped_image=cropped,
        warped_image=warped,
        polygon=ordered_poly,
        transform_matrix=M,
        confidence=detection_conf,
        status=status,
    )


def crop_document(image: np.ndarray, polygon: np.ndarray) -> np.ndarray:
    """Crop image to bounding box of polygon."""
    x_min, y_min = np.min(polygon, axis=0).astype(int)
    x_max, y_max = np.max(polygon, axis=0).astype(int)
    h, w = image.shape[:2]
    x1, y1 = max(0, x_min), max(0, y_min)
    x2, y2 = min(w, x_max), min(h, y_max)
    return image[y1:y2, x1:x2].copy()


def perspective_correct(image: np.ndarray, polygon: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Warp image to rectangular top-down view given quadrilateral polygon points."""
    ordered = _order_points(polygon.astype(np.float32))
    tl, tr, br, bl = ordered

    width_a = np.linalg.norm(br - bl)
    width_b = np.linalg.norm(tr - tl)
    max_w = max(int(width_a), int(width_b))

    height_a = np.linalg.norm(tr - br)
    height_b = np.linalg.norm(tl - bl)
    max_h = max(int(height_a), int(height_b))

    max_w = max(100, max_w)
    max_h = max(100, max_h)

    dst = np.array([
        [0, 0],
        [max_w - 1, 0],
        [max_w - 1, max_h - 1],
        [0, max_h - 1]
    ], dtype=np.float32)

    M = cv2.getPerspectiveTransform(ordered, dst)
    warped = cv2.warpPerspective(image, M, (max_w, max_h), flags=cv2.INTER_CUBIC)
    return warped, M
