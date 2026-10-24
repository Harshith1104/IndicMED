from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.retrieval import BM25Retriever, TfidfRetriever
from src.utils.helpers import load_config, resolve_project_path


def main(query: str, method: str, top_k: int) -> None:
    config = load_config()
    data = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).fillna("")
    retriever = TfidfRetriever() if method == "tfidf" else BM25Retriever()
    for result in retriever.fit(data).retrieve(query, top_k):
        print(f"#{result['rank']} score={result['score']:.4f} id={result['id']}")
        print(f"Question: {result['question']}")
        print(f"Answer: {result['answer'][:400]}")
        print(f"Source: {result['source']} {result['source_url']}")
        print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("query")
    parser.add_argument("--method", choices=("tfidf", "bm25"), default="tfidf")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    main(args.query, args.method, args.top_k)
