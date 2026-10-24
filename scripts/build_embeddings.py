from __future__ import annotations

import argparse
import pickle
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from src.utils.helpers import load_config, resolve_project_path


def main(limit: int | None = None) -> None:
    from sentence_transformers import SentenceTransformer

    config = load_config()
    data = pd.read_csv(resolve_project_path(config["paths"]["dataset"])).fillna("")
    if limit:
        data = data.head(limit)
    model_name = config["models"]["embedding_model"]
    model = SentenceTransformer(model_name)
    embeddings = model.encode(
        data[config["retrieval"]["text_field"]].tolist(),
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embedding_path = resolve_project_path(config["paths"]["embeddings"])
    metadata_path = resolve_project_path(config["paths"]["metadata"])
    embedding_path.parent.mkdir(parents=True, exist_ok=True)
    np.save(embedding_path, np.asarray(embeddings, dtype=np.float32))
    with metadata_path.open("wb") as handle:
        pickle.dump({
            "model_name": model_name,
            "text_field": config["retrieval"]["text_field"],
            "ids": data["id"].tolist(),
            "embedding_dimension": int(embeddings.shape[1]),
        }, handle)
    saved = np.load(embedding_path, mmap_mode="r")
    with metadata_path.open("rb") as handle:
        metadata = pickle.load(handle)
    print(f"Model: {model_name}")
    print(f"Embedding array shape: {saved.shape}")
    print(f"Document count: {len(data):,}")
    print(f"Metadata ID count: {len(metadata['ids']):,}")
    print(f"NaN values: {int(np.isnan(saved).sum()):,}")
    print(f"Saved embeddings: {embedding_path}")
    print(f"Saved metadata: {metadata_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int)
    main(parser.parse_args().limit)
