from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.evaluation.retrieval_metrics import retrieval_metrics
from src.retrieval import SemanticRetriever
from src.translation import IndicTranslator
from src.utils.helpers import load_config, resolve_project_path

INDIC_LANGUAGES = ("hi", "te", "ta")


def ensure_backtranslations(test_set: pd.DataFrame, translator: IndicTranslator, cache_path: Path,
                            batch_size: int) -> pd.DataFrame:
    columns = ["query_id", "language", "original_query", "translated_english_query"]
    cache = pd.read_csv(cache_path).fillna("") if cache_path.exists() else pd.DataFrame(columns=columns)
    valid_keys = {(row.query_id, row.language, row.query) for row in test_set.itertuples() if row.language in INDIC_LANGUAGES}
    if not cache.empty:
        cache = cache[cache.apply(lambda row: (row["query_id"], row["language"], row["original_query"]) in valid_keys, axis=1)]
    completed = {(row.query_id, row.language, row.original_query) for row in cache.itertuples()}
    records = cache.to_dict("records")
    for language in INDIC_LANGUAGES:
        pending = [row for row in test_set[test_set["language"] == language].itertuples()
                   if (row.query_id, language, row.query) not in completed]
        for start in range(0, len(pending), batch_size):
            chunk = pending[start:start + batch_size]
            translations = translator.translate_batch([row.query for row in chunk], language, "en", batch_size=batch_size)
            records.extend({"query_id": row.query_id, "language": language, "original_query": row.query,
                            "translated_english_query": translated}
                           for row, translated in zip(chunk, translations))
            pd.DataFrame(records, columns=columns).to_csv(cache_path, index=False, encoding="utf-8")
            print(f"backtranslation {language}: {min(start + len(chunk), len(pending))}/{len(pending)} new")
    return pd.DataFrame(records, columns=columns)


def evaluate_group(retriever: SemanticRetriever, frame: pd.DataFrame, strategy: str,
                   query_column: str) -> tuple[dict[str, float], list[dict[str, object]]]:
    started = time.perf_counter()
    results = retriever.retrieve_batch(frame[query_column].tolist(), 5)
    elapsed = time.perf_counter() - started
    rankings, records = [], []
    for row, retrieved in zip(frame.itertuples(), results):
        ids = [item["id"] for item in retrieved]
        rank = ids.index(row.document_id) + 1 if row.document_id in ids else None
        rankings.append(ids)
        records.append({
            "query_id": row.query_id, "document_id": row.document_id, "language": row.language,
            "strategy": strategy, "original_query": row.query,
            "english_query": getattr(row, query_column), "rank_of_correct_document": rank,
            "top1_document_id": ids[0], "top1_score": retrieved[0]["score"],
            "correct_at_1": rank == 1, "correct_at_3": rank is not None and rank <= 3,
            "correct_at_5": rank is not None and rank <= 5,
        })
    metrics = retrieval_metrics(frame["document_id"].tolist(), rankings)
    metrics["evaluation_seconds"] = elapsed
    return metrics, records


def build_error_analysis(results: pd.DataFrame, output: Path) -> None:
    english = results[(results.language == "en") & (results.strategy == "semantic")][["query_id", "correct_at_1"]]
    english = english.rename(columns={"correct_at_1": "english_correct_at_1"})
    samples = []
    for language in INDIC_LANGUAGES:
        subset = results[results.language == language]
        direct = subset[subset.strategy == "direct_semantic"].add_prefix("direct_")
        translated = subset[subset.strategy == "translate_semantic"].add_prefix("translated_")
        merged = direct.merge(translated, left_on="direct_query_id", right_on="translated_query_id")
        merged = merged.merge(english, left_on="direct_query_id", right_on="query_id")
        for row in merged.itertuples():
            direct_rank = row.direct_rank_of_correct_document
            translated_rank = row.translated_rank_of_correct_document
            direct_one, translated_one = direct_rank == 1, translated_rank == 1
            notes = []
            if direct_one and not translated_one: notes.append("direct_succeeds_translation_fails")
            if translated_one and not direct_one: notes.append("translation_succeeds_direct_fails")
            if direct_one and translated_one: notes.append("both_succeed")
            if pd.isna(direct_rank) and pd.isna(translated_rank): notes.append("both_fail_top5")
            if row.english_correct_at_1 and not (direct_one and translated_one): notes.append("english_succeeds_indic_not_both")
            if (pd.notna(direct_rank) and 2 <= direct_rank <= 5) or (pd.notna(translated_rank) and 2 <= translated_rank <= 5):
                notes.append("correct_at_rank_2_to_5")
            for note in notes:
                samples.append({"language": language, "original_query": row.direct_original_query,
                                "translated_english_query": row.translated_english_query,
                                "expected_document_id": row.direct_document_id,
                                "direct_top1": row.direct_top1_document_id,
                                "translated_top1": row.translated_top1_document_id,
                                "direct_correct_rank": direct_rank,
                                "translated_correct_rank": translated_rank, "notes": note})
    frame = pd.DataFrame(samples)
    selected = pd.concat([group.head(2) for _, group in frame.groupby(["language", "notes"], sort=True)])
    selected.to_csv(output, index=False, encoding="utf-8")


def plot_metrics(metrics: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    labels = metrics.assign(label=metrics.language.str.upper() + " — " + metrics.strategy.str.replace("_", " "))
    labels.set_index("label")[["recall_at_1", "recall_at_3", "recall_at_5"]].plot.bar(figsize=(11, 6), rot=25)
    plt.ylabel("Recall"); plt.ylim(0, 1); plt.tight_layout()
    plt.savefig(figures_dir / "multilingual_recall_comparison.png", dpi=160); plt.close()
    labels.set_index("label")[["mrr"]].plot.bar(figsize=(10, 5), rot=25, legend=False)
    plt.ylabel("MRR"); plt.ylim(0, 1); plt.tight_layout()
    plt.savefig(figures_dir / "multilingual_mrr_comparison.png", dpi=160); plt.close()


def main(batch_size: int) -> None:
    config = load_config()
    test_set = pd.read_csv(resolve_project_path("data/test/multilingual_test_set.csv")).fillna("")
    data = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).fillna("")
    settings = config["models"]["translation"]
    translator = IndicTranslator(settings["en_to_indic"], settings["indic_to_en"])
    cache_path = resolve_project_path("data/test/multilingual_backtranslations.csv")
    backtranslations = ensure_backtranslations(test_set, translator, cache_path, batch_size)
    test_set = test_set.merge(backtranslations[["query_id", "language", "translated_english_query"]],
                              on=["query_id", "language"], how="left")
    test_set.loc[test_set.language == "en", "translated_english_query"] = test_set.loc[test_set.language == "en", "query"]

    retriever = SemanticRetriever(config["models"]["embedding_model"]).fit(
        data, np.load(resolve_project_path(config["paths"]["embeddings"]))
    )
    metric_rows, result_rows = [], []
    groups = [("en", "semantic", "query")]
    groups += [(language, strategy, "query" if strategy == "direct_semantic" else "translated_english_query")
               for language in INDIC_LANGUAGES for strategy in ("direct_semantic", "translate_semantic")]
    for language, strategy, column in groups:
        frame = test_set[test_set.language == language].copy()
        metrics, records = evaluate_group(retriever, frame, strategy, column)
        metric_rows.append({"language": language, "strategy": strategy, "sample_size": len(frame), **metrics})
        result_rows.extend(records)
        print(language, strategy, metrics)
    results_dir = resolve_project_path("outputs/results")
    metrics_frame, results_frame = pd.DataFrame(metric_rows), pd.DataFrame(result_rows)
    metrics_frame.to_csv(results_dir / "multilingual_metrics.csv", index=False)
    results_frame.to_csv(results_dir / "multilingual_retrieval_results.csv", index=False)
    build_error_analysis(results_frame, results_dir / "multilingual_error_analysis.csv")
    plot_metrics(metrics_frame, resolve_project_path("outputs/figures"))
    print(metrics_frame.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-size", type=int, default=16)
    main(parser.parse_args().batch_size)
