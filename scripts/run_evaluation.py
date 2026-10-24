from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.evaluation.evaluate import evaluate_retriever
from src.retrieval import BM25Retriever, SemanticRetriever, TfidfRetriever
from src.utils.helpers import load_config, resolve_project_path


def generate_figures(metrics: pd.DataFrame, figures_dir: Path) -> None:
    figures_dir.mkdir(parents=True, exist_ok=True)
    labels = {"recall_at_1": "Recall@1", "recall_at_3": "Recall@3", "recall_at_5": "Recall@5"}
    metrics.set_index("method")[list(labels)].rename(columns=labels).plot.bar(rot=0)
    plt.ylabel("Recall"); plt.ylim(0, 1); plt.tight_layout()
    plt.savefig(figures_dir / "recall_comparison.png", dpi=160); plt.close()
    metrics.set_index("method")[["mrr"]].rename(columns={"mrr": "MRR"}).plot.bar(rot=0, legend=False)
    plt.ylabel("MRR"); plt.ylim(0, 1); plt.tight_layout()
    plt.savefig(figures_dir / "mrr_comparison.png", dpi=160); plt.close()


def create_error_analysis(details: pd.DataFrame, output: Path) -> None:
    pivot = details.pivot(index=["query_id", "question", "expected_id"], columns="method", values=["rank", "top1_id"]).reset_index()
    pivot.columns = ["_".join(str(part) for part in column if part) if isinstance(column, tuple) else column for column in pivot.columns]
    pivot = pivot.rename(columns={"top1_id_tfidf": "tfidf_top1", "top1_id_bm25": "bm25_top1", "top1_id_semantic": "semantic_top1", "rank_semantic": "semantic_correct_rank"})
    def note(row):
        target = row["expected_id"]
        if row.get("semantic_top1") == target and row.get("tfidf_top1") != target:
            return "semantic_rank1_tfidf_failed"
        if row.get("bm25_top1") == target and row.get("semantic_top1") != target:
            return "bm25_rank1_semantic_failed"
        if all(pd.isna(value) for value in (row.get("rank_tfidf"), row.get("rank_bm25"), row.get("semantic_correct_rank"))):
            return "all_methods_failed_top5"
        if pd.notna(row.get("semantic_correct_rank")) and 2 <= row["semantic_correct_rank"] <= 5:
            return "semantic_correct_at_rank_2_to_5"
        return "other"
    pivot["notes"] = pivot.apply(note, axis=1)
    labels = ["semantic_rank1_tfidf_failed", "bm25_rank1_semantic_failed", "all_methods_failed_top5", "semantic_correct_at_rank_2_to_5"]
    result = pd.concat([pivot[pivot["notes"] == label].head(5) for label in labels]).drop_duplicates("query_id").head(20)
    result = result.rename(columns={"expected_id": "expected_document_id"})
    columns = ["question", "expected_document_id", "tfidf_top1", "bm25_top1", "semantic_top1", "semantic_correct_rank", "notes"]
    result[columns].to_csv(output, index=False)


def main(sample_size: int) -> None:
    config = load_config()
    data = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).fillna("")
    queries = data.sample(min(sample_size, len(data)), random_state=config["project"]["random_seed"])
    embeddings_path = resolve_project_path(config["paths"]["embeddings"])
    if not embeddings_path.exists():
        raise FileNotFoundError("Build semantic embeddings first: python scripts/build_embeddings.py")
    methods = (("tfidf", TfidfRetriever()), ("bm25", BM25Retriever()),
               ("semantic", SemanticRetriever(config["models"]["embedding_model"])))
    metric_rows, query_rows = [], []
    for name, retriever in methods:
        start = time.perf_counter()
        retriever.fit(data, np.load(embeddings_path)) if name == "semantic" else retriever.fit(data)
        metrics, details = evaluate_retriever(retriever, queries)
        seconds = time.perf_counter() - start
        metric_rows.append({"method": name, "language": "en", "sample_size": len(queries), **metrics, "evaluation_seconds": seconds})
        details.insert(0, "method", name); details.insert(1, "language", "en")
        query_rows.append(details)
        print(f"{name}: {seconds:.2f}s")
    results_dir, figures_dir = resolve_project_path("outputs/results"), resolve_project_path("outputs/figures")
    results_dir.mkdir(parents=True, exist_ok=True)
    metrics_frame, details_frame = pd.DataFrame(metric_rows), pd.concat(query_rows, ignore_index=True)
    metrics_frame.to_csv(results_dir / "final_metrics.csv", index=False)
    details_frame.to_csv(results_dir / "retrieval_results.csv", index=False)
    create_error_analysis(details_frame, results_dir / "error_analysis.csv")
    generate_figures(metrics_frame, figures_dir)
    print(metrics_frame.to_string(index=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=200)
    main(parser.parse_args().sample_size)
