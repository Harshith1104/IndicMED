"""Create aligned multilingual query files using the configured translator."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.translation import IndicTranslator
from src.utils.helpers import load_config, resolve_project_path


def main(sample_size: int) -> None:
    config = load_config()
    sample = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).sample(sample_size, random_state=42)
    settings = config["models"]["translation"]
    translator = IndicTranslator(settings["en_to_indic"], settings["indic_to_en"])
    names = {"hi": "hindi", "te": "telugu", "ta": "tamil"}
    combined = []
    for language, name in names.items():
        translated = sample[["id", "question"]].copy()
        translated["question"] = [translator.translate_from_english(value, language) for value in translated["question"]]
        translated["language"] = language
        translated.to_csv(resolve_project_path(f"data/translated/{name}_questions.csv"), index=False)
        combined.append(translated)
    pd.concat(combined).to_csv(resolve_project_path("data/test/multilingual_test_set.csv"), index=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=100)
    main(parser.parse_args().sample_size)

