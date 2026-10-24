from __future__ import annotations

import re

SUPPORTED = {"en", "hi", "te", "ta"}


def detect_language(text: str, fallback: str = "en") -> str:
    """Detect supported scripts first, then use langdetect for Latin text."""
    if re.search(r"[\u0c00-\u0c7f]", text):
        return "te"
    if re.search(r"[\u0b80-\u0bff]", text):
        return "ta"
    if re.search(r"[\u0900-\u097f]", text):
        return "hi"
    try:
        from langdetect import DetectorFactory, detect
        DetectorFactory.seed = 42
        result = detect(text)
        return result if result in SUPPORTED else fallback
    except Exception:
        return fallback

