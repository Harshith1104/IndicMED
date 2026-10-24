from src.preprocessing.clean_text import clean_text


def test_clean_text_preserves_unicode_and_normalizes_space() -> None:
    assert clean_text("  తెలుగు\n  text &amp; more ") == "తెలుగు text & more"


def test_clean_text_handles_empty_values() -> None:
    assert clean_text(None) == ""
    assert clean_text("") == ""

