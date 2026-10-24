from __future__ import annotations

from collections.abc import Sequence


def retrieval_metrics(expected_ids: Sequence[str], ranked_ids: Sequence[Sequence[str]], ks=(1, 3, 5)) -> dict[str, float]:
    if len(expected_ids) != len(ranked_ids):
        raise ValueError("Expected IDs and rankings must have equal length")
    if not expected_ids:
        raise ValueError("At least one query is required")
    values = {f"recall_at_{k}": sum(target in ranks[:k] for target, ranks in zip(expected_ids, ranked_ids)) / len(expected_ids) for k in ks}
    reciprocal = []
    for target, ranks in zip(expected_ids, ranked_ids):
        reciprocal.append(1.0 / (ranks.index(target) + 1) if target in ranks else 0.0)
    values["mrr"] = sum(reciprocal) / len(reciprocal)
    return values

