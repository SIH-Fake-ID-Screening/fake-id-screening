# SIH26188 — Module 3: Tampering Detection Service
**Ministry of Home Affairs / SSB Fake Identity & Document Screening System**

Standalone Python forensic service for identity document tampering screening, photo replacement detection, text manipulation analysis, stamp forgery identification, and EXIF/XMP metadata anomaly detection.

---

## 0. Project Folder Layout

```
modules/tampering/
├── reference/            ← Canonical GENUINE card standard (separate from everything else)
│   ├── kiet_id_front.png     (front template, 986x1600)
│   ├── kiet_id_back.jpg      (back template, 1026x1600)
│   └── archive/              (older lower-resolution captures, kept for provenance)
├── samples/              ← Evaluation datasets (genuine variants, tampered variants + GT masks)
├── results/              ← RUN OUTPUTS ONLY (mask / overlay / report per analysis; debug/ for --debug)
├── forensic/             ← ELA, SRM, copy-move, AI-spectrum, metadata, reference matching
├── localization/         ← Heatmap fusion + overlay rendering
├── scoring/              ← Multi-factor risk fusion
├── preprocessing/        ← Image loading, document detection & rectification, quality
├── models/               ← TamperingModel protocol, ELASRMModel, TruFor adapter
├── evaluation/           ← CLI analyzer, benchmark suite, metrics
├── tests/                ← pytest suite
└── app/                  ← FastAPI service
```

`results/` contains **only** analysis artifacts: for every analyzed image it receives
`<name>_mask.png`, `<name>_overlay.png` and `<name>_report.json`. The `--debug` CLI flag
writes intermediate stage images into `results/debug/` instead of the results root.

---

## 1. Architecture & Pipeline Overview

The pipeline processes input document images through multi-spectral forensic channels:

```
Input Image
    │
    ├── Preprocessing & Quality Assessment (document.py, quality.py)
    │
    ├── Multi-Spectral Forensic Analysis
    │   ├── Error Level Analysis / JPEG Compression (ela.py)
    │   ├── Spatial Rich Model / Noise Residuals (srm.py)
    │   ├── Copy-Move Keypoint Matching (copy_move.py)
    │   └── EXIF/XMP Metadata Anomaly Inspector (metadata.py)
    │
    ├── Decoupled Neural Interface Protocol (TamperingModel -> TruForModel / ELASRMModel)
    │
    ├── Tampering Localization & Morphological Heatmap Fusion (heatmap.py)
    ├── Visual Overlay & Suspicious Region Bounding Renderer (overlay.py)
    ├── Multi-Factor Evidence Fusion & Risk Scoring (risk_score.py)
    │
    └── Output Contract Delivery: JSON Report + Mask PNG + Overlay PNG
```

---

## 2. Model Architecture & TruFor Integration

- **Model Interface Contract**: Defined as a Python `Protocol` (`TamperingModel`) in `models/inference.py`.
- **Currently Active Backend**: `ELASRMModel` (multi-spectral baseline incorporating ELA, SRM filter residuals, copy-move matching, and EXIF analysis).
- **TruFor Neural Adapter (`TruForModel`)**:
  - TruFor weights path: `modules/tampering/models/weights/trufor.pth`.
  - If weights are absent, the adapter logs a status notification and defers to `ELASRMModel`.
  - **To plug in TruFor later**:
    1. Download `trufor.pth` from the official research release.
    2. Place weights at `modules/tampering/models/weights/trufor.pth`.
    3. Install PyTorch (`pip install torch torchvision`).
    4. The `TruForModel` adapter in `models/inference.py` automatically detects and uses TruFor.

---

## 2.1 Reference Standard: KIET ID Card (Canonical Genuine Templates)

The backend verifies identity cards against a **canonical genuine standard** stored in its own dedicated folder:

- `modules/tampering/reference/kiet_id_front.png` (front, 986x1600)
- `modules/tampering/reference/kiet_id_back.jpg` (back, 1026x1600)

`forensic/reference_matching.py` compares every query card against this standard:

1. **Template rectification** — references are perspective-rectified once and cached.
2. **Alignment** — ORB ratio-test matching → MAGSAC homography → ECC affine refinement (falls back to resize).
3. **Illumination-normalized diffing** — CLAHE equalization + background subtraction so exposure/shadows do not trigger false alarms.
4. **Card-layout zone analysis** — deviation is measured per standard zone (`photo`, `name_line`, `qr_code`, `signature`, `roll_number`, header, and back-side fields).
5. **Concentration scoring** — genuine re-captures (exposure, perspective, resolution changes) spread deviation across all zones (score ≤ ~20); content tampering concentrates in one zone (score ≥ ~40) and receives a concentration boost. Security-critical zones (photo, name, QR, signature) add an extra penalty.

Empirical calibration (see `evaluation/benchmark.py`):

| Case family | Reference deviation | Verdict |
|---|---|---|
| Genuine re-captures (exposure/perspective/low-res) | 0 – 14 | LOW, not tampered |
| Photo / name / QR / signature / DOB tampers | 44 – 100 | Tampered (zone named in report) |
| Non-KIET documents | 60 – 98 | Rejected (flagged) |

Benchmark (13 samples): **92.3% accuracy, 100% recall, 90% precision, F1 = 0.947**, mean localization IoU 0.31.

### Tampering Localization (the heatmap)

`localization/heatmap.py` builds the tampering localization heatmap so it highlights **where the document is actually tampered**:

- The **reference-standard diff map is the primary channel** (weight 0.45) — it marks exactly the pixels that differ from the genuine card.
- The diff is **warped back onto the uploaded image's own geometry** through the inverse of the alignment transform (homography ∘ ECC ∘ rectification), so the heat stays anchored to the actual tampered pixels even when the upload is tilted, rotated, or perspective-shifted — never a plain resize of the reference-frame map.
- The diff is **zone-gated**: zones whose deviation score matches the genuine standard are suppressed to 8% strength, so alignment halos and print noise cannot light up; zones that genuinely deviate pass at full strength. The ELA/SRM/copy-move channels are softened by the same gate (25% floor in matching zones).
- ELA (0.20), SRM (0.25) and copy-move (0.10) remain as independent confirmation channels; without a reference match the map falls back to generic ELA/SRM/copy-move weighting.
- The overlay (`<name>_overlay.png`) draws bounding boxes with per-region risk scores exactly on the tampered areas (e.g. the swapped photo, the rewritten name line, the forged signature), and the HUD banner states the verdict.

To regenerate the KIET evaluation dataset (genuine variants + tampered variants with ground-truth masks):

```bash
PYTHONPATH=modules/tampering python modules/tampering/samples/generate_kiet_samples.py
```

---

## 3. Installation & Setup

```bash
# Navigate to workspace
cd /path/to/SIH

# Create virtual environment
python3 -m venv modules/tampering/venv
source modules/tampering/venv/bin/activate

# Install dependencies
pip install -r modules/tampering/requirements.txt
```

---

## 4. Running Single Image Inference (CLI)

```bash
PYTHONPATH=modules/tampering python -m evaluation.test --image modules/tampering/samples/tampered_photo/photo_01.png
```

### Expected Output Contract:
Generates three files in `modules/tampering/results/`:
1. `<filename>_mask.png`: 2D binarized/grayscale localization heatmap.
2. `<filename>_overlay.png`: Original image with color-coded heatmap and bounding boxes highlighting suspicious regions.
3. `<filename>_report.json`: Structured analysis report.

---

## 5. Running Dataset Benchmark Suite (CLI)

```bash
PYTHONPATH=modules/tampering python -m evaluation.benchmark --input modules/tampering/samples/
```

Computes empirical classification metrics (**Accuracy, Precision, Recall, F1 Score**) and spatial localization metrics (**Mean Mask-level IoU**).

---

## 6. Starting FastAPI Web Server

The service reads `HOST` and `PORT` from environment variables (defaults `0.0.0.0:8000`) —
no hardcoded port, so it runs unchanged on any machine or deployment platform:

```bash
# From repository root
HOST=0.0.0.0 PORT=8000 python modules/tampering/run.py

# Or from modules/tampering/
PORT=9000 python run.py
```

All paths (results, references, weights) are resolved relative to the module directory,
so the service works from any clone location or working directory.

### Endpoints:
- `GET /health`: Health status & loaded model backend info.
- `POST /api/tampering/analyze`: Accepts multipart image upload (`File`), returns JSON analysis.
- `GET /artifacts/<filename>`: Serves stored analysis artifacts (mask / overlay / heatmap PNGs and report JSONs) so a dashboard can render them directly.

### Dashboard Integration Contract

The service is designed to be consumed by an external dashboard. Every analysis produces
**four artifacts** in `modules/tampering/results/` and returns them with ready-to-use URLs:

| Artifact | File | Purpose on the dashboard |
|---|---|---|
| Grayscale mask | `<name>_mask.png` | Raw localization mask (pixel-level) |
| Forensic overlay | `<name>_overlay.png` | Report view: HUD banner + region boxes + risk legend |
| **Heatmap overlay** | `<name>_heatmap.png` | **Clean color heatmap on the original image, same dimensions, no banner — display side-by-side with the uploaded image** |
| JSON report | `<name>_report.json` | Full structured report (everything below + diagnostics) |

The `POST /api/tampering/analyze` response contains everything the whole-report view needs:

```jsonc
{
  "tampered": true,
  "risk_score": 49.23,              // 0-100
  "risk_level": "HIGH",             // LOW | MEDIUM | HIGH | CRITICAL
  "confidence": 0.56,               // 0-1
  "channels": {                     // per-channel evidence for gauges/charts
    "ela": 0.0, "srm": 33.98, "reference": 59.91, "copy_move": 0.0, "metadata": 0.0
  },
  "tampered_zones": [               // card zones deviating from the genuine standard
    {"zone": "name_line", "deviation": 21.74, "critical": true}
  ],
  "regions": [                      // suspicious regions, tagged with their card zone
    {"region_id": 1, "bbox": [x, y, w, h], "zone": "name_line",
     "peak_score": 99.91, "mean_score": 74.2, "area_pixels": 51230}
  ],
  "metadata_anomalies": ["..."],
  "output_files": {
    "mask_url": "/artifacts/<name>_mask.png",
    "overlay_url": "/artifacts/<name>_overlay.png",
    "heatmap_url": "/artifacts/<name>_heatmap.png",
    "report_url": "/artifacts/<name>_report.json"
  }
}
```

Dashboard rendering guide: show the uploaded image and `heatmap_url` side-by-side
(the heatmap marks WHERE it is tampered), use `regions` + `tampered_zones` for the
findings list, `channels` for evidence gauges, and `overlay_url` for the full
annotated report view.

---

## 7. Forensic Limitations & Screening Guidance

> [!WARNING]
> - **Error Level Analysis (ELA) Limitations**: ELA highlights JPEG re-compression differences. Re-saving or resizing a genuine document can introduce uniform ELA noise. ELA must **never** be used as sole evidence of forgery.
> - **Metadata Limitations**: Missing EXIF tags or social media compression stripping is common in uploaded documents and is treated **strictly as supporting evidence** (capped at max +15 contribution to risk score).
> - **Terminology Standard**: All reports use probabilistic risk metrics (`Tampering Risk`, `Suspicious Region`, `Requires Verification`). Absolute certainty claims (e.g. "100% Fake") are explicitly prohibited.
