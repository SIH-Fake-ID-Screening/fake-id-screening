"""
ai/ocr/normalizer.py
--------------------
Text and date normalization helpers. Parses various date representations into YYYY-MM-DD
and cleans extracted field strings. Zero hallucination guarantee.
"""

import re
from datetime import datetime
from typing import Optional


def normalize_date(raw_date_str: Optional[str]) -> Optional[str]:
    """
    Parse and normalize raw date strings into standard ISO YYYY-MM-DD format.

    Supported inputs:
    - 2026-06-30 / 2026/06/30 / 2026.06.30
    - 30/06/2026 / 30-06-2026 / 30.06.2026
    - 06/30/2026 / 06-30-2026
    - 30 JUN 2026 / 30 June 2026 / Jun 30, 2026

    Returns YYYY-MM-DD or None if unresolvable.
    """
    if not raw_date_str:
        return None

    cleaned = raw_date_str.strip()
    # Remove ordinal suffixes (1st, 2nd, 3rd, 4th)
    cleaned = re.sub(r'(\d+)(st|nd|rd|th)', r'\1', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'[^\w\s\-\/\.]', ' ', cleaned)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    # Date formats to try
    formats = [
        "%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d",
        "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y",
        "%m/%d/%Y", "%m-%d-%Y",
        "%d %b %Y", "%d %B %Y",
        "%b %d %Y", "%B %d %Y",
        "%d-%b-%Y", "%d-%B-%Y",
        "%d %m %Y", "%m %d %Y", "%Y %m %d",  # space-separated numeric formats
        "%B %Y", "%b %Y"
    ]

    for fmt in formats:
        try:
            dt = datetime.strptime(cleaned, fmt)
            if 1900 <= dt.year <= 2100:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue

    # Regex extraction fallback for embedded date substring (e.g. "DOB 14/05/2002")
    match = re.search(r'(\d{1,4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,4})', cleaned)
    if match:
        p1, p2, p3 = match.groups()
        # Case 1: YYYY-MM-DD
        if len(p1) == 4:
            year, month, day = int(p1), int(p2), int(p3)
        # Case 2: DD-MM-YYYY or MM-DD-YYYY
        elif len(p3) == 4:
            year = int(p3)
            if int(p1) > 12:
                day, month = int(p1), int(p2)
            else:
                day, month = int(p1), int(p2)
        else:
            return None

        try:
            dt = datetime(year, month, day)
            if 1900 <= dt.year <= 2100:
                return dt.strftime("%Y-%m-%d")
        except ValueError:
            return None

    return None


def clean_text_field(val: Optional[str]) -> Optional[str]:
    """Clean extracted field value by stripping redundant spaces and special chars."""
    if not val:
        return None
    val = re.sub(r'[\r\n\t]', ' ', val)
    val = re.sub(r'\s+', ' ', val).strip()
    val = val.strip(':=-_ ')
    return val if val else None
