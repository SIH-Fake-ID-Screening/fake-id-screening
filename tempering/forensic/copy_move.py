import cv2
import numpy as np
from typing import Tuple, List


def analyze_copy_move(image: np.ndarray, min_spatial_dist: float = 80.0) -> Tuple[np.ndarray, float, int]:
    """
    Detect copy-move forgery (duplication of stamps, seals, or text blocks) using keypoint matching.

    Args:
        image: BGR uint8 NumPy array.
        min_spatial_dist: Minimum pixel distance between keypoints to classify as copy-move duplicate.

    Returns:
        copy_move_map: 2D float32 array normalized to [0.0, 1.0] showing copy-move duplicated areas.
        copy_move_score: Scalar score [0.0 - 100.0] indicating duplication confidence.
        matches_count: Number of suspicious non-local matched keypoint pairs.
    """
    if image is None or image.size == 0:
        raise ValueError("Invalid image input for copy-move analysis.")

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape

    copy_move_map = np.zeros((h, w), dtype=np.float32)

    # Initialize ORB detector
    orb = cv2.ORB_create(nfeatures=2500, scaleFactor=1.2, nlevels=8)
    keypoints, descriptors = orb.detectAndCompute(gray, None)

    if descriptors is None or len(descriptors) < 10:
        return copy_move_map, 0.0, 0

    # Brute-force matcher with kNN (k=3 to query distinct keypoints)
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
    matches = bf.knnMatch(descriptors, descriptors, k=3)

    suspicious_pts: List[np.ndarray] = []

    for match in matches:
        if len(match) >= 3:
            m = match[1]  # 1st nearest distinct keypoint
            n = match[2]  # 2nd nearest keypoint
            if m.distance < 20 and m.distance < 0.75 * n.distance:
                pt1 = np.array(keypoints[m.queryIdx].pt)
                pt2 = np.array(keypoints[m.trainIdx].pt)
                dist = np.linalg.norm(pt1 - pt2)

                if dist > min_spatial_dist:
                    suspicious_pts.append(pt1)
                    suspicious_pts.append(pt2)

    matches_count = len(suspicious_pts) // 2

    # Compute copy move score first
    raw_score = (matches_count - 120) * 0.45
    copy_move_score = float(min(100.0, max(0.0, raw_score)))

    # Draw point clusters on map
    for pt in suspicious_pts:
        x, y = int(pt[0]), int(pt[1])
        cv2.circle(copy_move_map, (x, y), 20, 1.0, -1)

    if np.max(copy_move_map) > 0:
        copy_move_map = cv2.GaussianBlur(copy_move_map, (15, 15), 0)
        max_val = np.max(copy_move_map)
        if max_val > 0:
            map_scale = (copy_move_score / 100.0)
            copy_move_map = np.clip((copy_move_map / max_val) * map_scale, 0.0, 1.0)

    return copy_move_map, copy_move_score, matches_count
