import os
import sys
import argparse
import cv2
import numpy as np
from typing import List, Dict, Any

# Ensure the tampering package is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.document import load_image
from models.inference import get_default_model
from evaluation.metrics import compute_mask_iou, compute_classification_metrics

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="SIH26188 Module 3 — Forensic Dataset Benchmark Evaluator")
    parser.add_argument("--input", default=os.path.join(PACKAGE_DIR, "samples"), type=str,
                        help="Directory containing dataset samples")
    args = parser.parse_args()

    input_dir = os.path.abspath(args.input)
    if not os.path.exists(input_dir):
        print(f"Error: Input dataset directory '{input_dir}' does not exist.")
        sys.exit(1)

    print(f"\n=================================================================")
    print(f"  SIH26188 Module 3: Tampering Detection Benchmark Suite")
    print(f"=================================================================")
    print(f"Benchmark Input Dataset Directory: {input_dir}\n")

    model = get_default_model()

    y_true: List[bool] = []
    y_pred: List[bool] = []
    iou_scores: List[float] = []
    results_table: List[Dict[str, Any]] = []

    # Find sample images. Category is the top-level directory under the input
    # root; runtime template copies (reference/), archived sources (archive/)
    # and non-card documents (synthetic_docs/) are excluded from evaluation.
    SKIP_DIRS = {"reference", "archive"}
    sample_files: List[str] = []
    for root, _, files in os.walk(input_dir):
        rel_dir = os.path.relpath(root, input_dir)
        parts = rel_dir.split(os.sep)
        top_dir = parts[0]
        if top_dir in SKIP_DIRS or any(p in SKIP_DIRS for p in parts):
            continue
        for f in sorted(files):
            if f.lower().endswith(('.png', '.jpg', '.jpeg')) and not f.lower().endswith('_gt.png'):
                sample_files.append(os.path.join(root, f))

    if not sample_files:
        print(f"No valid sample image files found in '{input_dir}'.")
        sys.exit(0)

    for img_path in sample_files:
        filename = os.path.basename(img_path)
        rel_dir = os.path.relpath(os.path.dirname(img_path), input_dir)
        dir_name = rel_dir.split(os.sep)[0]
        base_stem = os.path.splitext(filename)[0]

        # Check for corresponding ground truth mask (_gt.png)
        gt_mask_path = os.path.join(os.path.dirname(img_path), f"{base_stem}_gt.png")
        gt_exists = os.path.exists(gt_mask_path)

        if gt_exists:
            gt_img = cv2.imread(gt_mask_path, cv2.IMREAD_GRAYSCALE)
            is_tampered_gt = bool(np.max(gt_img) > 0)
        else:
            gt_img = None
            is_tampered_gt = "genuine" not in dir_name.lower()

        # Run Prediction
        img = load_image(img_path)
        pred = model.predict(img, filepath=img_path)

        # Compute IoU if ground truth mask exists
        if gt_exists and gt_img is not None:
            iou = compute_mask_iou(pred.localization_mask, gt_img)
            iou_scores.append(iou)
            iou_str = f"{iou:.4f}"
        else:
            iou_str = "N/A"

        y_true.append(is_tampered_gt)
        y_pred.append(pred.tampered)

        results_table.append({
            "category": dir_name,
            "filename": filename,
            "gt_label": "Tampered" if is_tampered_gt else "Genuine",
            "pred_label": "Tampered" if pred.tampered else "Genuine",
            "risk_score": pred.risk_score,
            "confidence": pred.confidence,
            "iou": iou_str
        })

    # Compute Overall Metrics
    metrics = compute_classification_metrics(y_true, y_pred)
    mean_iou = float(np.mean(iou_scores)) if iou_scores else 0.0

    # Output Results Table
    print(f"{'Category':<16} {'Filename':<18} {'GT Label':<10} {'Pred Label':<10} {'Risk Score':<12} {'IoU':<8}")
    print("-" * 80)
    for r in results_table:
        print(f"{r['category']:<16} {r['filename']:<18} {r['gt_label']:<10} {r['pred_label']:<10} {r['risk_score']:<12.2f} {r['iou']:<8}")

    print("\n" + "=" * 80)
    print(f"                       EMPIRICAL BENCHMARK SUMMARY")
    print("=" * 80)
    print(f"Total Samples Evaluated        : {len(sample_files)}")
    print(f"Overall Accuracy               : {metrics['accuracy'] * 100.0:.2f}%")
    print(f"Precision                      : {metrics['precision'] * 100.0:.2f}%")
    print(f"Recall                         : {metrics['recall'] * 100.0:.2f}%")
    print(f"F1 Score                       : {metrics['f1_score']:.4f}")
    if iou_scores:
        print(f"Mean Mask-level IoU            : {mean_iou:.4f}")
    print(f"Confusion Matrix               : TP={metrics['tp']}, TN={metrics['tn']}, FP={metrics['fp']}, FN={metrics['fn']}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()



