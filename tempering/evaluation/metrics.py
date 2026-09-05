import cv2
import numpy as np
from typing import Dict, Any, List


def compute_mask_iou(pred_mask: np.ndarray, gt_mask: np.ndarray, threshold: float = 0.35) -> float:
    """
    Compute pixel-level Intersection over Union (IoU) between binarized predicted mask and ground truth binary mask.

    Args:
        pred_mask: 2D float32 array normalized to [0.0 - 1.0].
        gt_mask: 2D uint8 or float array where > 0 represents tampered ground truth region.
        threshold: Threshold value to binarize predicted heatmap mask.

    Returns:
        iou_score: Float in range [0.0, 1.0].
    """
    h, w = pred_mask.shape[:2]
    if gt_mask.shape[:2] != (h, w):
        gt_mask = cv2.resize(gt_mask, (w, h), interpolation=cv2.INTER_NEAREST)

    if gt_mask.ndim == 3:
        gt_mask = cv2.cvtColor(gt_mask, cv2.COLOR_BGR2GRAY)

    pred_bin = (pred_mask >= threshold)
    gt_bin = (gt_mask > 0)

    intersection = np.logical_and(pred_bin, gt_bin).sum()
    union = np.logical_or(pred_bin, gt_bin).sum()

    if union == 0:
        # If ground truth is empty and prediction is empty, perfect IoU = 1.0
        return 1.0 if not pred_bin.any() else 0.0

    return float(intersection / union)


def compute_classification_metrics(y_true: List[bool], y_pred: List[bool]) -> Dict[str, float]:
    """
    Calculate Classification Accuracy, Precision, Recall, and F1-Score from true and predicted boolean labels.
    """
    y_t = np.array(y_true, dtype=bool)
    y_p = np.array(y_pred, dtype=bool)

    tp = np.logical_and(y_t == True, y_p == True).sum()
    tn = np.logical_and(y_t == False, y_p == False).sum()
    fp = np.logical_and(y_t == False, y_p == True).sum()
    fn = np.logical_and(y_t == True, y_p == False).sum()

    total = len(y_true)
    accuracy = float((tp + tn) / total) if total > 0 else 0.0
    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
    f1 = float(2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1_score": round(f1, 4),
        "tp": int(tp),
        "tn": int(tn),
        "fp": int(fp),
        "fn": int(fn)
    }
