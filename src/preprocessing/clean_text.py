from __future__ import annotations

import html
import re


def clean_text(text: object) -> str:
    """Normalize whitespace and harmless markup without losing Indic text."""
    if text is None:
        return ""
    value = html.unescape(str(text))
    value = re.sub(r"<[^>]+>", " ", value)
    value = value.replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()

