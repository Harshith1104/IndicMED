from typing import Any


def select_answer(results: list[dict[str, Any]]) -> dict[str, Any] | None:
    return results[0] if results else None

