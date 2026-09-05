from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class RegionDetail(BaseModel):
    region_id: int
    bbox: List[int] = Field(..., description="[x, y, width, height]")
    area_pixels: int
    peak_score: float
    mean_score: float
    zone: Optional[str] = Field(None, description="Standard card zone containing this region (photo, name_line, qr_code, ...)")


class TamperedZone(BaseModel):
    zone: str = Field(..., description="Card layout zone name")
    deviation: float = Field(..., ge=0.0, le=100.0, description="Zone deviation from the genuine reference standard [%]")
    critical: bool = Field(False, description="Security-critical zone (photo, name, QR, signature...)")


class ForensicChannels(BaseModel):
    """Per-channel forensic evidence scores for dashboard gauges/charts."""
    ela: float = Field(0.0, ge=0.0, le=100.0, description="Error Level Analysis score")
    srm: float = Field(0.0, ge=0.0, le=100.0, description="SRM noise + AI spectrum + reference composite")
    reference: float = Field(0.0, ge=0.0, le=100.0, description="Deviation from the genuine reference standard")
    copy_move: float = Field(0.0, ge=0.0, le=100.0, description="Copy-move duplication score")
    metadata: float = Field(0.0, ge=0.0, le=15.0, description="EXIF metadata anomaly score (capped)")


class OutputFilesInfo(BaseModel):
    mask_path: str
    overlay_path: str
    heatmap_path: str = Field("", description="Color heatmap overlaid on the image (same dimensions, no banner)")
    report_json_path: str
    mask_url: Optional[str] = Field(None, description="Relative API URL to serve the mask PNG")
    overlay_url: Optional[str] = Field(None, description="Relative API URL to serve the overlay PNG")
    heatmap_url: Optional[str] = Field(None, description="Relative API URL to serve the heatmap overlay PNG")
    report_url: Optional[str] = Field(None, description="Relative API URL to fetch the stored JSON report")


class TamperingAnalysisResponse(BaseModel):
    tampered: bool
    risk_score: float = Field(..., ge=0.0, le=100.0, description="Overall Tampering Risk Score [0-100]")
    risk_level: str = Field(..., description="LOW, MEDIUM, HIGH, or CRITICAL")
    forensic_score: float = Field(..., ge=0.0, le=100.0, description="Combined ELA + SRM + Copy-Move Score")
    metadata_score: float = Field(..., ge=0.0, le=15.0, description="Capped EXIF Metadata Anomaly Score")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Model Confidence [0-1]")
    channels: ForensicChannels = Field(..., description="Per-channel forensic evidence scores")
    tampered_zones: List[TamperedZone] = Field(default_factory=list, description="Card zones deviating from the genuine reference standard")
    regions: List[RegionDetail]
    metadata_anomalies: List[str]
    output_files: OutputFilesInfo


class HealthCheckResponse(BaseModel):
    status: str
    service: str
    active_model: str
    trufor_available: bool
