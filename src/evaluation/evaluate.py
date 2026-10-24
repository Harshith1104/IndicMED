from __future__ import annotations

from typing import Any

import pandas as pd

from .retrieval_metrics import retrieval_metrics


def evaluate_retriever(retriever: Any, queries: pd.DataFrame, top_k: int = 5) -> tuple[dict[str, float], pd.DataFrame]:
    rankings: list[list[str]] = []
    records = []
    rows = list(queries.itertuples(index=False))
    if hasattr(retriever, "retrieve_batch"):
        all_results = retriever.retrieve_batch([row.question for row in rows], top_k)
    else:
        all_results = [retriever.retrieve(row.question, top_k) for row in rows]
    for row, results in zip(rows, all_results):
        ids = [item["id"] for item in results]
        rankings.append(ids)
        rank = ids.index(row.id) + 1 if row.id in ids else None
        records.append({"query_id": row.id, "question": row.question, "expected_id": row.id,
                        "rank": rank, "top1_id": ids[0] if ids else "", "retrieved_ids": "|".join(ids)})
    return retrieval_metrics(queries["id"].tolist(), rankings), pd.DataFrame(records)
