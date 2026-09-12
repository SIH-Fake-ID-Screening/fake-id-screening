import os
import sys
import argparse
import json
import cv2
import numpy as np

# Ensure the tampering package is importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from preprocessing.document import load_image
from preprocessing.document_crop import detect_document
from forensic.ela import analyze_ela
from forensic.srm import analyze_srm
from forensic.ai_spectrum import analyze_ai_spectrum
from forensic.copy_move import analyze_copy_move
from models.inference import get_default_model

PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main():
    parser = argparse.ArgumentParser(description="SIH26188 Module 3 — Single Image Tampering Forensic Analyzer")
    parser.add_argument("--image", required=True, type=str, help="Path to input document image")
    parser.add_argument("--debug", action="store_true", help="Output full intermediate stage debug images (01_original to 08_overlay)")
    args = parser.parse_args()

    image_path = os.path.abspath(args.image)
    if not os.path.exists(image_path):
        print(f"Error: Target image file '{image_path}' does not exist.")
        sys.exit(1)

    print(f"\n=================================================================")
    print(f"  SIH26188 Module 3: Document Forensic Tampering Analysis")
    print(f"=================================================================")
    print(f"Target Image Path       : {image_path}")

    path_lower = image_path.lower()
    if "genuine" in path_lower:
        actual_label = "GENUINE (Un-tampered)"
    elif "tampered" in path_lower or "fake" in path_lower:
        actual_label = "TAMPERED"
    else:
        actual_label = "Unknown (Unlabeled Input)"

    print(f"Actual Ground Truth     : {actual_label}")

    img_bgr = load_image(image_path)
    model = get_default_model()

    prediction = model.predict(img_bgr, filepath=image_path)

    results_dir = os.path.join(PACKAGE_DIR, "results")
    os.makedirs(results_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    mask_path = os.path.join(results_dir, f"{base_name}_mask.png")
    overlay_path = os.path.join(results_dir, f"{base_name}_overlay.png")
    heatmap_path = os.path.join(results_dir, f"{base_name}_heatmap.png")
    report_path = os.path.join(results_dir, f"{base_name}_report.json")

    cv2.imwrite(mask_path, (prediction.localization_mask * 255.0).astype(np.uint8))
    cv2.imwrite(overlay_path, prediction.overlay_image)
    cv2.imwrite(heatmap_path, prediction.heatmap_overlay_image)

    # Output intermediate stages if --debug flag is set (kept inside
    # results/debug/ so the results root only holds final artifacts)
    if args.debug:
        debug_dir = os.path.join(results_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
        print(f"\n[DEBUG MODE ACTIVATED] Saving intermediate pipeline stage images to {debug_dir}/ ...")
        doc_det = detect_document(img_bgr)
        ela_map, _ = analyze_ela(doc_det.warped_image)
        ai_map, _, _ = analyze_ai_spectrum(doc_det.warped_image)

        cv2.imwrite(os.path.join(debug_dir, "01_original.png"), img_bgr)
        cv2.imwrite(os.path.join(debug_dir, "02_document_crop.png"), doc_det.warped_image)
        cv2.imwrite(os.path.join(debug_dir, "03_ela_map.png"), (ela_map * 255.0).astype(np.uint8))
        cv2.imwrite(os.path.join(debug_dir, "04_ai_map.png"), (ai_map * 255.0).astype(np.uint8))
        cv2.imwrite(os.path.join(debug_dir, "05_combined_map.png"), (prediction.localization_mask * 255.0).astype(np.uint8))
        cv2.imwrite(os.path.join(debug_dir, "06_cleaned_mask.png"), ((prediction.localization_mask > 0.35).astype(np.uint8) * 255))
        cv2.imwrite(os.path.join(debug_dir, "07_final_heatmap.png"), (prediction.localization_mask * 255.0).astype(np.uint8))
        cv2.imwrite(os.path.join(debug_dir, "08_final_overlay.png"), prediction.overlay_image)

    ref_details = prediction.diagnostics.get("reference_match_details", {})

    report_data = {
        "image_path": image_path,
        "actual_label": actual_label,
        "tampered": prediction.tampered,
        "risk_score": prediction.risk_score,
        "risk_level": prediction.risk_level,
        "forensic_score": prediction.forensic_score,
        "metadata_score": prediction.metadata_score,
        "forensic_confidence": prediction.confidence,
        "channels": {
            "ela": prediction.diagnostics.get("ela_score", 0.0),
            "srm": prediction.diagnostics.get("srm_score", 0.0),
            "reference": prediction.diagnostics.get("reference_score", 0.0),
            "copy_move": prediction.diagnostics.get("copy_move_score", 0.0),
            "metadata": prediction.diagnostics.get("metadata_score_raw", prediction.metadata_score),
        },
        "tampered_zones": ref_details.get("flagged_zones", []),
        "suspicious_regions_count": len(prediction.regions),
        "regions": prediction.regions,
        "metadata_anomalies": prediction.metadata_anomalies,
        "diagnostics": prediction.diagnostics,
        "output_files": {
            "mask_path": mask_path,
            "overlay_path": overlay_path,
            "heatmap_path": heatmap_path,
            "report_path": report_path
        }
    }

    with open(report_path, "w") as f:
        json.dump(report_data, f, indent=2)

    print(f"\n--- Forensic Detection Results ---")
    print(f"Predicted Tampering     : {prediction.tampered}")
    print(f"Tampering Risk Score    : {prediction.risk_score:.2f} / 100.0 ({prediction.risk_level})")
    print(f"Forensic Score          : {prediction.forensic_score:.2f}")
    print(f"Metadata Score          : {prediction.metadata_score:.2f}")
    print(f"Forensic Confidence     : {prediction.confidence:.2f}")
    print(f"Suspicious Region Count : {len(prediction.regions)}")

    if prediction.metadata_anomalies:
        print(f"\nMetadata Anomalies Detected:")
        for anomaly in prediction.metadata_anomalies:
            print(f"  - {anomaly}")

    print(f"\n--- Output Artifacts Written ---")
    print(f"Localization Mask Path  : {mask_path}")
    print(f"Visual Overlay Path     : {overlay_path}")
    print(f"Heatmap Overlay Path    : {heatmap_path}")
    print(f"JSON Report Path        : {report_path}")
    print(f"=================================================================\n")


if __name__ == "__main__":
    main()