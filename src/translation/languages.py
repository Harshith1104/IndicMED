"""Central language metadata for application and IndicTrans2 codes."""
from __future__ import annotations

LANGUAGE_NAMES = {"en": "English", "hi": "Hindi", "te": "Telugu", "ta": "Tamil"}
INDICTRANS_CODES = {"en": "eng_Latn", "hi": "hin_Deva", "te": "tel_Telu", "ta": "tam_Taml"}
SCRIPT_RANGES = {"hi": ("\u0900", "\u097f"), "te": ("\u0c00", "\u0c7f"), "ta": ("\u0b80", "\u0bff")}


def get_translation_language_code(language: str) -> str:
    try:
        return INDICTRANS_CODES[language]
    except KeyError as error:
        raise ValueError(f"Unsupported language code: {language}") from error


def contains_expected_script(text: str, language: str) -> bool:
    if language == "en":
        return any(character.isascii() and character.isalpha() for character in text)
    start, end = SCRIPT_RANGES[language]
    return any(start <= character <= end for character in text)
