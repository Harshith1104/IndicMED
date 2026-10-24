from __future__ import annotations


def simplify_answer(answer: str, max_characters: int = 1400) -> str:
    """Conservatively shorten at a sentence boundary without adding facts."""
    if len(answer) <= max_characters:
        return answer
    candidate = answer[:max_characters]
    boundary = max(candidate.rfind(". "), candidate.rfind("? "), candidate.rfind("! "))
    return candidate[: boundary + 1] if boundary > max_characters // 2 else candidate.rstrip() + "…"

