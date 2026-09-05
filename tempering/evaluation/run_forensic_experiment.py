import os
import sys
import json
import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("modules/tampering"))

from preprocessing.document import load_image
from preprocessing.document_crop import detect_document
from forensic.ela import analyze_ela
from forensic.srm import analyze_srm
from forensic.ai_spectrum import analyze_ai_spectrum
from forensic.copy_move import analyze_copy_move
from forensic.metadata import analyze_metadata
from localization.heatmap import fuse_heatmaps
from localization.overlay import generate_overlay
from scoring.risk_score import compute_risk_score


def run_experiment(image_path: str):
    image_path = os.path.abspath(image_path)
    if not os.path.exists(image_path):
        raise FileNotFoundError(f"Image not found at: {image_path}")

    img_bgr = load_image(image_path)
    h_orig, w_orig = img_bgr.shape[:2]

    exp_dir = os.path.abspath("modules/tampering/results/forensic_exp")
    os.makedirs(exp_dir, exist_ok=True)

    # STEP 1 — DOCUMENT DETECTION & RECTIFICATION
    doc_det = detect_document(img_bgr)
    work_img = doc_det.warped_image

    crop_path = os.path.join(exp_dir, "01_document_crop.png")
    rect_path = os.path.join(exp_dir, "02_document_rectified.png")
    cv2.imwrite(crop_path, doc_det.cropped_image)
    cv2.imwrite(rect_path, doc_det.warped_image)

    # STEP 2–4 — FORENSIC EXTRACTION
    ela_map, ela_score = analyze_ela(work_img)
    srm_map, srm_score = analyze_srm(work_img)
    ai_map, ai_score, ai_anomalies = analyze_ai_spectrum(work_img)
    cm_map, cm_score, cm_count = analyze_copy_move(work_img)
    meta_dict, meta_anomalies, meta_score = analyze_metadata(image_path)

    ela_path = os.path.join(exp_dir, "03_ela_map.png")
    noise_path = os.path.join(exp_dir, "04_noise_map.png")
    cv2.imwrite(ela_path, (ela_map * 255.0).astype(np.uint8))
    cv2.imwrite(noise_path, (srm_map * 255.0).astype(np.uint8))

    # STEP 5 — MODEL STATUS
    # Honest disclosure: TruFor PyTorch model weights unpopulated
    model_name = "ELA+SRM Baseline (TruFor PyTorch Weights Unpopulated)"
    model_loaded = False
    model_confidence = None

    # STEP 6–7 — FUSION & HEATMAP GENERATION
    combined_srm_ai = (0.75 * srm_score) + (0.25 * ai_score)
    fused_heatmap, suspicious_regions = fuse_heatmaps(ela_map, srm_map, cm_map, ai_map)

    raw_map_path = os.path.join(exp_dir, "05_raw_combined_map.png")
    mask_path = os.path.join(exp_dir, "06_cleaned_tampering_mask.png")
    heatmap_path = os.path.join(exp_dir, "07_tampering_heatmap.png")
    overlay_path = os.path.join(exp_dir, "08_final_overlay.png")
    json_path = os.path.join(exp_dir, "09_forensic_report.json")

    cv2.imwrite(raw_map_path, (fused_heatmap * 255.0).astype(np.uint8))
    cleaned_mask = ((fused_heatmap > 0.35).astype(np.uint8) * 255)
    cv2.imwrite(mask_path, cleaned_mask)

    # Color Heatmap Rendering (TURBO colormap)
    heatmap_uint8 = (fused_heatmap * 255.0).astype(np.uint8)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_TURBO)
    cv2.imwrite(heatmap_path, heatmap_color)

    # Overlay rendering
    overlay_img = generate_overlay(work_img, fused_heatmap, suspicious_regions)
    cv2.imwrite(overlay_path, overlay_img)

    # STEP 8–9 — EVIDENCE FUSION & DECISION
    risk_result = compute_risk_score(
        ela_score=ela_score,
        srm_score=combined_srm_ai,
        copy_move_score=cm_score,
        metadata_score=meta_score,
        suspicious_regions=suspicious_regions,
    )

    tampering_risk = float(risk_result["risk_score"])
    forensic_conf = float(risk_result["confidence"])

    if tampering_risk >= 55.0 and len(suspicious_regions) >= 1:
        decision = "LIKELY_TAMPERED"
        decision_label = "LIKELY TAMPERED"
    elif tampering_risk <= 35.0 and len(suspicious_regions) == 0:
        decision = "LIKELY_GENUINE"
        decision_label = "LIKELY GENUINE"
    else:
        decision = "UNCERTAIN"
        decision_label = "UNCERTAIN"

    # Format JSON suspicious regions
    json_regions = []
    for r in suspicious_regions:
        json_regions.append({
            "id": r["region_id"],
            "type": "SUSPICIOUS_PATCH",
            "score": float(r["mean_score"] / 100.0),
            "confidence": float(r["peak_score"] / 100.0),
            "bbox": r["bbox"],
            "reason": f"Local ELA/SRM noise residual score elevated ({r['mean_score']}%)"
        })

    report_data = {
        "document": {
            "width": w_orig,
            "height": h_orig
        },
        "decision": decision,
        "tampering_risk": round(tampering_risk, 2),
        "confidence": round(forensic_conf, 2),
        "model": {
            "name": model_name,
            "loaded": model_loaded,
            "confidence": model_confidence
        },
        "signals": {
            "ela": round(ela_score, 2),
            "noise": round(srm_score, 2),
            "texture": round(ai_score, 2),
            "compression": round(ela_score, 2),
            "metadata": round(meta_score, 2)
        },
        "suspicious_regions": json_regions,
        "artifacts": {
            "document_crop": crop_path,
            "rectified": rect_path,
            "ela_map": ela_path,
            "noise_map": noise_path,
            "combined_map": raw_map_path,
            "mask": mask_path,
            "heatmap": heatmap_path,
            "overlay": overlay_path
        }
    }

    with open(json_path, "w") as f:
        json.dump(report_data, f, indent=2)

    # STEP 11 — TERMINAL OUTPUT CONTRACT
    print("===============================================")
    print("SIH26188 — MODULE 3 FORENSIC ANALYSIS")
    print("===============================================")
    print(f"\nDocument:\n{os.path.basename(image_path)}")
    print(f"\nDocument detected:\nYES ({doc_det.status})")
    print(f"\nAI model loaded:\n{'YES' if model_loaded else 'NO'}")
    print(f"\nModel:\nNO TRAINED FORENSIC MODEL LOADED ({model_name})")
    print("\n-----------------------------------------------")
    print("FORENSIC RESULTS")
    print("-----------------------------------------------")
    print(f"\nTampering Risk:\n{tampering_risk:.2f} / 100")
    print(f"\nDecision:\n{decision_label}")
    print(f"\nConfidence:\n{int(forensic_conf * 100)}%")
    print(f"\nSuspicious Regions:\n{len(suspicious_regions)}")
    print("\n-----------------------------------------------")
    print("REGIONS")
    print("-----------------------------------------------")
    if not suspicious_regions:
        print("\nNo suspicious regions detected (0 suspicious patches).")
    else:
        for r in suspicious_regions:
            print(f"\nRegion #{r['region_id']}")
            print(f"Type: SUSPICIOUS_PATCH")
            print(f"Score: {r['mean_score'] / 100.0:.2f}")
            print(f"Confidence: {r['peak_score'] / 100.0:.2f}")
            print(f"Location: bbox={r['bbox']}")
            print(f"Reason: Local compression & high-frequency residual inconsistency ({r['mean_score']}%)")

    print("\n-----------------------------------------------")
    print("OUTPUT FILES")
    print("-----------------------------------------------")
    print(f"\nDocument crop:\n{crop_path}")
    print(f"\nELA:\n{ela_path}")
    print(f"\nNoise:\n{noise_path}")
    print(f"\nHeatmap:\n{heatmap_path}")
    print(f"\nOverlay:\n{overlay_path}")
    print(f"\nJSON:\n{json_path}")
    print("===============================================\n")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        run_experiment(sys.argv[1])
    else:
        run_experiment("/Users/yuvrajpatel/.gemini/antigravity/brain/f5aefdb9-dd95-401f-9455-adce2f610aa1/media__1788430787491.png")
