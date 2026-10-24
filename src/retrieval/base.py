from __future__ import annotations

from typing import Any

import pandas as pd


REQUIRED_COLUMNS = {"id", "question", "answer"}


def validate_documents(documents: pd.DataFrame, text_field: str) -> pd.DataFrame:
    missing = REQUIRED_COLUMNS.union({text_field}) - set(documents.columns)
    if missing:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing)}")
    if documents.empty:
        raise ValueError("At least one document is required")
    result = documents.reset_index(drop=True).copy()
    result[text_field] = result[text_field].fillna("").astype(str)
    return result


def ranked_records(documents: pd.DataFrame, scores: Any, top_k: int) -> list[dict[str, Any]]:
    import numpy as np

    k = min(max(int(top_k), 0), len(documents))
    if k == 0:
        return []
    order = np.argsort(np.asarray(scores), kind="stable")[::-1][:k]
    records: list[dict[str, Any]] = []
    for rank, index in enumerate(order, start=1):
        item = documents.iloc[int(index)].to_dict()
        item.update(score=float(scores[index]), rank=rank)
        records.append(item)
    return records

