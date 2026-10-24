from __future__ import annotations

import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.retrieval import SemanticRetriever
from src.utils.helpers import load_config, resolve_project_path

QUERIES = [
    "What are the symptoms of diabetes?",
    "What causes migraine?",
    "What is asthma?",
    "What are the treatments for high blood pressure?",
    "How is tuberculosis diagnosed?",
]


def main() -> None:
    config = load_config()
    data = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).fillna("")
    embeddings = np.load(resolve_project_path(config["paths"]["embeddings"]))
    with resolve_project_path(config["paths"]["metadata"]).open("rb") as handle:
        metadata = pickle.load(handle)
    if metadata["ids"] != data["id"].tolist() or len(embeddings) != len(data):
        raise ValueError("Embedding index and dataset do not match")
    retriever = SemanticRetriever(config["models"]["embedding_model"]).fit(data, embeddings)
    for query, results in zip(QUERIES, retriever.retrieve_batch(QUERIES, 3)):
        print(f"\nQUERY: {query}")
        for item in results:
            print(f"  #{item['rank']} score={item['score']:.4f} | {item['question']}")
            print(f"     {item['answer'][:220]}...")
            print(f"     Source: {item['source']} {item['source_url']}")


if __name__ == "__main__":
    main()
