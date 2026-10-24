import unicodedata

from .clean_text import clean_text


def normalize_text(text: object) -> str:
    return unicodedata.normalize("NFKC", clean_text(text))

