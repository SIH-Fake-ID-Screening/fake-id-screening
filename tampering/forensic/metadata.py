import os
from typing import Dict, Any, List, Tuple
from PIL import Image, ExifTags


SUSPICIOUS_SOFTWARE_TAGS = [
    "photoshop", "gimp", "canva", "paint.net", "adobe", "exiftool",
    "pixelmator", "lightroom", "affinity", "coreldraw", "snapseed", "picsart"
]


def analyze_metadata(filepath_or_pil: Any) -> Tuple[Dict[str, Any], List[str], float]:
    """
    Analyze image file metadata (EXIF / header metadata) for indicators of digital manipulation.

    Args:
        filepath_or_pil: File path string or PIL Image object.

    Returns:
        metadata_dict: Extracted clean metadata fields.
        anomalies: List of human-readable descriptive anomaly strings.
        metadata_score: Capped anomaly score [0.0 - 15.0] (supporting evidence only).
    """
    anomalies: List[str] = []
    metadata_dict: Dict[str, Any] = {}
    base_score = 0.0

    try:
        if isinstance(filepath_or_pil, str):
            if not os.path.exists(filepath_or_pil):
                return {"error": "File not found"}, ["File path invalid or unreachable"], 0.0
            pil_img = Image.open(filepath_or_pil)
        elif isinstance(filepath_or_pil, Image.Image):
            pil_img = filepath_or_pil
        else:
            return {"status": "No file path provided for metadata inspection"}, [], 0.0

        raw_exif = pil_img._getexif() if hasattr(pil_img, '_getexif') and callable(pil_img._getexif) else None

        if raw_exif:
            for tag_id, value in raw_exif.items():
                tag_name = ExifTags.TAGS.get(tag_id, str(tag_id))
                metadata_dict[tag_name] = str(value)

                # Check Software tag
                if tag_name.lower() == 'software':
                    val_str = str(value).lower()
                    for sw in SUSPICIOUS_SOFTWARE_TAGS:
                        if sw in val_str:
                            anomalies.append(f"Editing software signature detected in EXIF: '{value}'")
                            base_score += 10.0
                            break

                # Check DateTime vs DateTimeOriginal discrepancy
                if tag_name == 'DateTime' and 'DateTimeOriginal' in metadata_dict:
                    if str(value) != metadata_dict['DateTimeOriginal']:
                        anomalies.append(
                            f"Timestamp mismatch between Original ({metadata_dict['DateTimeOriginal']}) and Modified ({value})"
                        )
                        base_score += 5.0

        # Additional metadata checks (Format & Info dictionary)
        info = getattr(pil_img, 'info', {})
        if 'dpi' in info:
            metadata_dict['dpi'] = str(info['dpi'])

        # Check for Photoshop / Adobe IPTC/XMP markers in info
        info_keys_str = " ".join([str(k).lower() + ":" + str(v).lower() for k, v in info.items()])
        for sw in SUSPICIOUS_SOFTWARE_TAGS:
            if sw in info_keys_str and not any(sw in a.lower() for a in anomalies):
                anomalies.append(f"Editing software marker found in image metadata stream: '{sw}'")
                base_score += 8.0
                break

    except Exception as e:
        # Graceful handling of corrupted EXIF or unsupported format
        metadata_dict["parsing_error"] = str(e)

    # Enforce Hard Architecture Rule 6: Capped at 15.0 max (Supporting evidence only)
    metadata_score = float(min(15.0, base_score))

    return metadata_dict, anomalies, metadata_score
