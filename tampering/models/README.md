# Forensics Model Architecture & Adapter Interface

## Overview
Module 3 uses a decoupled architecture adhering to the `TamperingModel` Protocol interface. This ensures that forensic neural networks (such as TruFor) can be seamlessly plugged in without modifying the API, evaluation pipeline, or scoring logic.

---

## Active Backend: ELA + SRM Baseline (`ELASRMModel`)
Currently active by default. It fuses:
1. **Error Level Analysis (ELA)**: Detects re-compression discrepancies across spliced photo/text regions.
2. **Spatial Rich Model (SRM)**: Extracts high-frequency residual noise patterns using 3x3 high-pass filter kernels to identify spatial noise variance anomalies.
3. **Copy-Move Engine**: Performs keypoint feature matching (ORB/DCT) to detect cloned stamp seals or duplicated text fields.
4. **Metadata Anomaly Analyzer**: Inspects EXIF/XMP streams for editing software tags and timestamp mismatches.

---

## Research Target: TruFor Integration (`TruForModel`)

### TruFor Model Checkpoint Status
- **Pretrained Checkpoint Path**: `modules/tampering/models/weights/trufor.pth`
- **Current Status**: Weights file is **NOT included by default** in this repository.
- **Behavior**: The `TruForModel` adapter checks `os.path.exists('modules/tampering/models/weights/trufor.pth')`. If absent, it logs an informative status message and transparently defers execution to `ELASRMModel`.

### How to Install and Enable TruFor Later
1. Download the official TruFor weights (`trufor.pth`) from the official research repository (Guillaro et al., CVPR 2023).
2. Create the weights directory and place the weights file:
   ```bash
   mkdir -p modules/tampering/models/weights/
   cp path/to/downloaded/trufor.pth modules/tampering/models/weights/trufor.pth
   ```
3. Install PyTorch dependencies:
   ```bash
   pip install torch torchvision timm
   ```
4. The `TruForModel` adapter in `models/inference.py` will automatically detect `trufor.pth` and switch from the ELA+SRM baseline to TruFor neural inference.

---

## Contract Compliance (`TamperingModel` Protocol)
All models must implement:
```python
class TamperingModel(Protocol):
    def predict(self, image: np.ndarray, filepath: Optional[str] = None) -> TamperingPrediction:
        """Returns tampering prediction object matching output schema."""
        ...
```
