from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.translation.indictrans import IndicTranslator
from src.translation.languages import contains_expected_script
from src.utils.helpers import load_config, resolve_project_path

SAMPLES = {
    "hi": "मधुमेह के लक्षण क्या हैं?",
    "te": "డయాబెటిస్ లక్షణాలు ఏమిటి?",
    "ta": "நீரிழிவு நோயின் அறிகுறிகள் என்ன?",
}
ENGLISH = "What are the symptoms of diabetes?"


def main() -> None:
    config = load_config()
    settings = config["models"]["translation"]
    translator = IndicTranslator(settings["en_to_indic"], settings["indic_to_en"])
    lines = ["IndicTrans2 six-direction smoke test", "===================================="]
    for language, source in SAMPLES.items():
        output = translator.translate_to_english(source, language)
        if not output.strip() or not contains_expected_script(output, "en"):
            raise RuntimeError(f"Invalid {language}->en output: {output!r}")
        lines.append(f"{language}->en | {source} | {output}")
    translator.unload("to_en")
    for language in SAMPLES:
        output = translator.translate_from_english(ENGLISH, language)
        if not output.strip() or not contains_expected_script(output, language):
            raise RuntimeError(f"Invalid en->{language} output: {output!r}")
        lines.append(f"en->{language} | {ENGLISH} | {output}")
    lines.append(f"Model load counts: {translator.load_counts}")
    lines.append(f"Loaded devices: {translator.loaded_devices}")
    destination = resolve_project_path("outputs/results/translation_smoke_test.txt")
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
