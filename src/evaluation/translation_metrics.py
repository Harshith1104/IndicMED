def chrf_score(reference: str, hypothesis: str) -> float:
    """Simple character n-gram F1 proxy, kept dependency-free."""
    if not reference or not hypothesis:
        return 0.0
    reference_chars, hypothesis_chars = set(reference), set(hypothesis)
    overlap = len(reference_chars & hypothesis_chars)
    precision = overlap / len(hypothesis_chars)
    recall = overlap / len(reference_chars)
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0

