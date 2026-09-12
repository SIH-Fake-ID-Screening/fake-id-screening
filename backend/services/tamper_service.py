"""
backend/services/tamper_service.py
----------------------------------
Service wrapper for the tempering module.
"""

import sys
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Add BOTH SIH-Backend and SIH-Backend/tempering to sys.path
# to allow absolute imports within the tempering module to work without manual PYTHONPATH.
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
_TEMPERING_DIR = os.path.join(_PROJECT_ROOT, 'tempering')

if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)
if _TEMPERING_DIR not in sys.path:
    sys.path.insert(0, _TEMPERING_DIR)

# Now we can import the model from the tempering package
from tempering.models.inference import get_default_model, detect_tampering

_model = None

def get_model():
    """Return the singleton tampering model."""
    global _model
    if _model is None:
        logger.info("Initializing tampering model...")
        _model = get_default_model()
    return _model

def check_tampering(image_path: str) -> Dict[str, Any]:
    """
    Run tampering analysis on the provided image.
    Returns a dictionary with 'tampered', 'risk_score', 'risk_level', 'confidence', etc.
    """
    model = get_model()
    # Provide the filepath to detect_tampering so it loads the image itself or reads EXIF
    # (assuming detect_tampering handles the loading if passed image=filepath and filepath=filepath, 
    # but the API is: image: np.ndarray | str, filepath: str)
    # detect_tampering from inference.py takes: image: np.ndarray | str.
    result = detect_tampering(image=image_path, filepath=image_path, model=model)
    return result
