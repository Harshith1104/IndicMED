from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.translation import IndicTranslator
from src.utils.helpers import load_config, resolve_project_path

LANGUAGES = ("en", "hi", "te", "ta")


def _write_checkpoint(rows: list[dict[str, object]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(path, index=False, encoding="utf-8")


def main(sample_size: int, batch_size: int, force: bool) -> None:
    config = load_config()
    seed = int(config["project"]["random_seed"])
    output = resolve_project_path("data/test/multilingual_test_set.csv")
    partial = output.with_suffix(".partial.csv")
    metadata_path = output.with_suffix(".metadata.json")
    intended = {"sample_size": sample_size, "random_seed": seed, "languages": list(LANGUAGES)}
    if output.exists() and metadata_path.exists() and not force:
        if json.loads(metadata_path.read_text(encoding="utf-8")) == intended:
            print(f"Reusing matching multilingual test set: {output}")
            return
        raise ValueError("Existing test set configuration differs; use --force to rebuild")
    if force:
        partial.unlink(missing_ok=True)
        output.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)

    data = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).fillna("")
    sample = data.sample(min(sample_size, len(data)), random_state=seed).reset_index(drop=True)
    base = []
    for index, row in sample.iterrows():
        base.append({"query_id": f"mq-{index:04d}", "document_id": row["id"], "language": "en",
                     "query": row["question"], "english_query": row["question"],
                     "translation_source": "original_medquad", "category": row["category"], "source": row["source"]})

    existing_rows = []
    if partial.exists() and not force:
        existing_rows = pd.read_csv(partial).fillna("").to_dict("records")
        expected_ids = {row["document_id"] for row in base}
        if {row["document_id"] for row in existing_rows} - expected_ids:
            raise ValueError("Partial checkpoint does not match the deterministic sample; use --force")
        print(f"Resuming from {len(existing_rows)} checkpointed rows")
    rows = existing_rows if existing_rows else list(base)
    valid_pairs = {(str(row["query_id"]), language) for row in base for language in LANGUAGES}
    checkpoint_pairs = [(str(row["query_id"]), str(row["language"])) for row in rows]
    if any(pair not in valid_pairs for pair in checkpoint_pairs) or len(checkpoint_pairs) != len(set(checkpoint_pairs)):
        raise ValueError("Partial checkpoint contains invalid or duplicate query-language rows; use --force")
    completed = {(str(row["query_id"]), str(row["language"])) for row in rows}
    if not existing_rows:
        _write_checkpoint(rows, partial)

    settings = config["models"]["translation"]
    translator = IndicTranslator(settings["en_to_indic"], settings["indic_to_en"])
    for language in LANGUAGES[1:]:
        pending = [row for row in base if (str(row["query_id"]), language) not in completed]
        for start in range(0, len(pending), batch_size):
            chunk = pending[start:start + batch_size]
            translations = translator.translate_batch([str(row["english_query"]) for row in chunk], "en", language,
                                                       batch_size=batch_size)
            for original, translated in zip(chunk, translations):
                rows.append({**original, "language": language, "query": translated,
                             "translation_source": settings["en_to_indic"]})
            _write_checkpoint(rows, partial)
            print(f"{language}: {min(start + len(chunk), len(pending))}/{len(pending)} newly translated")

    frame = pd.DataFrame(rows)
    order = {language: index for index, language in enumerate(LANGUAGES)}
    frame["_language_order"] = frame["language"].map(order)
    frame = frame.sort_values(["query_id", "_language_order"]).drop(columns="_language_order")
    if len(frame) != len(sample) * len(LANGUAGES):
        raise RuntimeError(f"Expected {len(sample) * 4} rows, found {len(frame)}")
    if not frame.groupby("query_id")["document_id"].nunique().eq(1).all():
        raise RuntimeError("Expected document IDs are not aligned across languages")
    frame.to_csv(output, index=False, encoding="utf-8")
    metadata_path.write_text(json.dumps(intended, indent=2), encoding="utf-8")
    partial.unlink(missing_ok=True)
    print(f"Saved {len(frame)} rows for {len(sample)} aligned questions: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=200)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    main(args.sample_size, args.batch_size, args.force)
