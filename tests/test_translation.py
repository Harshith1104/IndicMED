import pytest

from src.preprocessing.language_detector import detect_language
from src.translation.indictrans import TranslationUnavailableError
from src.translation.languages import contains_expected_script, get_translation_language_code


@pytest.mark.parametrize("language,expected", [("en", "eng_Latn"), ("hi", "hin_Deva"),
                                                 ("te", "tel_Telu"), ("ta", "tam_Taml")])
def test_translation_language_mapping(language, expected) -> None:
    assert get_translation_language_code(language) == expected


def test_unknown_translation_language_rejected() -> None:
    with pytest.raises(ValueError):
        get_translation_language_code("xx")


@pytest.mark.parametrize("text,expected", [("health information", "en"), ("मधुमेह क्या है", "hi"),
                                             ("మధుమేహం ఏమిటి", "te"), ("நீரிழிவு என்றால் என்ன", "ta")])
def test_language_detection_for_supported_scripts(text, expected) -> None:
    assert detect_language(text) == expected


@pytest.mark.parametrize("text,language", [("मधुमेह", "hi"), ("మధుమేహం", "te"), ("நீரிழிவு", "ta")])
def test_expected_unicode_script(text, language) -> None:
    assert contains_expected_script(text, language)


class UnavailableTranslator:
    def translate_to_english(self, text, language):
        raise TranslationUnavailableError("unavailable")

    def translate_from_english(self, text, language):
        raise TranslationUnavailableError("unavailable")
