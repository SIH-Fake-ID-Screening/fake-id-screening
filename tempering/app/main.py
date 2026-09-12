import os
import cv2
import json
import logging
import uuid
import tempfile
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    TamperingAnalysisResponse,
    HealthCheckResponse,
    OutputFilesInfo,
    RegionDetail,
    TamperedZone,
    ForensicChannels,
)
from models.inference import get_default_model, TruForModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tampering_service")

app = FastAPI(
    title="SIH26188 — Module 3: Tampering Detection Service",
    description="Standalone Python Forensic Service for Identity & Document Tampering Screening",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Model Engine
tampering_model = get_default_model()

# Module-relative paths: the service runs correctly from any working directory
# (repo root, modules/tampering/, or a fresh clone).
PACKAGE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RESULTS_DIR = os.path.join(PACKAGE_DIR, "results")
os.makedirs(RESULTS_DIR, exist_ok=True)

# Serve analysis artifacts (mask / overlay / heatmap / report JSON) over HTTP so
# a dashboard can render them directly:  /artifacts/<filename>
app.mount("/artifacts", StaticFiles(directory=RESULTS_DIR), name="artifacts")


@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint exposing active model backend and service status."""
    is_trufor_active = isinstance(tampering_model, TruForModel) and tampering_model.is_loaded
    active_name = "TruFor Deep Neural Network" if is_trufor_active else "Active ELA + SRM Baseline"

    return HealthCheckResponse(
        status="ok",
        service="SIH26188 Tampering Detection Service",
        active_model=active_name,
        trufor_available=os.path.exists(TruForModel.DEFAULT_WEIGHTS_PATH)
    )


@app.post("/api/tampering/analyze", response_model=TamperingAnalysisResponse)
async def analyze_document_tampering(file: UploadFile = File(...)):
    """
    POST /api/tampering/analyze endpoint accepting multipart document image uploads.
    Performs forensic analysis (ELA, SRM, metadata, copy-move, reference standard)
    and returns a dashboard-ready JSON report with artifact URLs.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file must be a valid image (JPEG, PNG, WEBP, etc.)"
        )

    try:
        contents = await file.read()
        nparr = np.frombuffer(contents, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to decode uploaded image bytes."
            )

        # Save temporary uploaded file to allow EXIF parsing
        original_filename = file.filename or f"doc_{uuid.uuid4().hex[:8]}.jpg"
        file_stem = os.path.splitext(original_filename)[0]
        temp_dir = tempfile.mkdtemp()
        temp_filepath = os.path.join(temp_dir, original_filename)

        with open(temp_filepath, "wb") as f:
            f.write(contents)

        # Execute Tampering Model Pipeline
        prediction = tampering_model.predict(img_bgr, filepath=temp_filepath)

        # Save Output Files into results/
        mask_filename = f"{file_stem}_mask.png"
        overlay_filename = f"{file_stem}_overlay.png"
        heatmap_filename = f"{file_stem}_heatmap.png"
        report_filename = f"{file_stem}_report.json"

        mask_path = os.path.join(RESULTS_DIR, mask_filename)
        overlay_path = os.path.join(RESULTS_DIR, overlay_filename)
        heatmap_path = os.path.join(RESULTS_DIR, heatmap_filename)
        report_path = os.path.join(RESULTS_DIR, report_filename)

        # 1. Save Mask (2D Float converted to uint8 grayscale 0-255)
        mask_uint8 = (prediction.localization_mask * 255.0).astype(np.uint8)
        cv2.imwrite(mask_path, mask_uint8)

        # 2. Save Forensic Overlay (HUD + region boxes)
        cv2.imwrite(overlay_path, prediction.overlay_image)

        # 3. Save clean heatmap overlay (dashboard artifact, same dims as input)
        cv2.imwrite(heatmap_path, prediction.heatmap_overlay_image)

        # 4. Dashboard-facing structured data
        ref_details = prediction.diagnostics.get("reference_match_details", {})
        tampered_zones = [
            TamperedZone(zone=z["zone"], deviation=z["deviation"], critical=z["critical"])
            for z in ref_details.get("flagged_zones", [])
        ]
        channels = ForensicChannels(
            ela=float(prediction.diagnostics.get("ela_score", 0.0)),
            srm=float(prediction.diagnostics.get("srm_score", 0.0)),
            reference=float(prediction.diagnostics.get("reference_score", 0.0)),
            copy_move=float(prediction.diagnostics.get("copy_move_score", 0.0)),
            metadata=float(prediction.diagnostics.get("metadata_score_raw", prediction.metadata_score)),
        )

        report_payload = {
            "file_name": original_filename,
            "tampered": prediction.tampered,
            "risk_score": prediction.risk_score,
            "risk_level": prediction.risk_level,
            "forensic_score": prediction.forensic_score,
            "metadata_score": prediction.metadata_score,
            "confidence": prediction.confidence,
            "channels": channels.model_dump(),
            "tampered_zones": [z.model_dump() for z in tampered_zones],
            "suspicious_regions_count": len(prediction.regions),
            "regions": prediction.regions,
            "metadata_anomalies": prediction.metadata_anomalies,
            "diagnostics": prediction.diagnostics,
            "artifacts": {
                "mask": f"/artifacts/{mask_filename}",
                "overlay": f"/artifacts/{overlay_filename}",
                "heatmap": f"/artifacts/{heatmap_filename}",
                "report": f"/artifacts/{report_filename}",
            },
            "output_files": {
                "mask_path": mask_path,
                "overlay_path": overlay_path,
                "heatmap_path": heatmap_path,
                "report_json_path": report_path
            }
        }

        with open(report_path, "w") as rf:
            json.dump(report_payload, rf, indent=2)

        # Clean up temp upload file
        if os.path.exists(temp_filepath):
            os.remove(temp_filepath)
            os.rmdir(temp_dir)

        # Format API Response
        region_models = [RegionDetail(**r) for r in prediction.regions]

        return TamperingAnalysisResponse(
            tampered=prediction.tampered,
            risk_score=prediction.risk_score,
            risk_level=prediction.risk_level,
            forensic_score=prediction.forensic_score,
            metadata_score=prediction.metadata_score,
            confidence=prediction.confidence,
            channels=channels,
            tampered_zones=tampered_zones,
            regions=region_models,
            metadata_anomalies=prediction.metadata_anomalies,
            output_files=OutputFilesInfo(
                mask_path=mask_path,
                overlay_path=overlay_path,
                heatmap_path=heatmap_path,
                report_json_path=report_path,
                mask_url=f"/artifacts/{mask_filename}",
                overlay_url=f"/artifacts/{overlay_filename}",
                heatmap_url=f"/artifacts/{heatmap_filename}",
                report_url=f"/artifacts/{report_filename}",
            )
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing image tampering analysis: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Forensic pipeline processing failure: {str(e)}"
        )
