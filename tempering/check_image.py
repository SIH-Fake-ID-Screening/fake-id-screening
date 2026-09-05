"""
Quick CLI: analyze one image for document tampering.

Usage (from anywhere):
    python check_image.py --image /path/to/card.jpg
    python check_image.py --image /path/to/card.jpg --debug

Outputs (in modules/tampering/results/):
    <name>_heatmap.png   color thermal map on your uploaded image
    <name>_overlay.png   forensic report view (HUD + region boxes)
    <name>_mask.png      raw localization mask
    <name>_report.json   full structured report
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from evaluation.test import main

if __name__ == "__main__":
    main()
