"""Audit MedQuAD parsing and deduplication with reproducible evidence."""
from __future__ import annotations

import hashlib
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.prepare_dataset import parse_xml
from src.utils.helpers import PROJECT_ROOT


def main() -> None:
    raw_root = PROJECT_ROOT / "data/raw/medquad"
    output_dir = PROJECT_ROOT / "outputs/results"
    output_dir.mkdir(parents=True, exist_ok=True)
    xml_files = sorted(raw_root.rglob("*.xml"))
    rows: list[dict[str, str]] = []
    file_hashes: Counter[str] = Counter()
    relative_paths: set[str] = set()
    per_source_files: Counter[str] = Counter()
    per_source_nodes: Counter[str] = Counter()
    per_source_empty_answers: Counter[str] = Counter()
    total_pair_nodes = 0
    empty_questions = 0
    empty_answers = 0

    for path in xml_files:
        relative = path.relative_to(raw_root).as_posix()
        relative_paths.add(relative.casefold())
        source_dir = path.relative_to(raw_root).parts[0]
        per_source_files[source_dir] += 1
        file_hashes[hashlib.sha256(path.read_bytes()).hexdigest()] += 1
        pair_nodes = ET.parse(path).getroot().findall(".//QAPair")
        total_pair_nodes += len(pair_nodes)
        per_source_nodes[source_dir] += len(pair_nodes)
        for pair in pair_nodes:
            question_node, answer_node = pair.find("Question"), pair.find("Answer")
            question_text = "" if question_node is None else "".join(question_node.itertext()).strip()
            answer_text = "" if answer_node is None else "".join(answer_node.itertext()).strip()
            empty_questions += not bool(question_text)
            empty_answers += not bool(answer_text)
            per_source_empty_answers[source_dir] += not bool(answer_text)
        for row in parse_xml(path, raw_root):
            rows.append({**row, "raw_file": relative, "source_directory": source_dir})

    frame = pd.DataFrame(rows)
    pair_columns = ["question", "answer"]
    exact_duplicate_mask = frame.duplicated(pair_columns, keep=False)
    duplicate_occurrences = int(exact_duplicate_mask.sum())
    unique_pairs = int(frame.drop_duplicates(pair_columns).shape[0])
    removed = len(frame) - unique_pairs
    repeated_file_groups = [count for count in file_hashes.values() if count > 1]

    group_rows = []
    for source in sorted(per_source_files):
        group = frame[frame["source_directory"] == source]
        unique_pairs_in_source = len(group.drop_duplicates(pair_columns))
        group_rows.append({
            "source_category": source,
            "xml_files": per_source_files[source],
            "qapair_nodes": per_source_nodes[source],
            "empty_answer_nodes": per_source_empty_answers[source],
            "raw_pairs": len(group),
            "unique_questions": group["question"].nunique(),
            "unique_answers": group["answer"].nunique(),
            "unique_pairs_within_source": unique_pairs_in_source,
            "duplicate_rows_removed_within_source": len(group) - unique_pairs_in_source,
            "rows_part_of_duplicate_pair": int(group.duplicated(pair_columns, keep=False).sum()),
        })
    grouped = pd.DataFrame(group_rows)
    grouped.to_csv(output_dir / "dataset_audit_by_source.csv", index=False)

    duplicate_groups = frame.loc[exact_duplicate_mask].groupby(pair_columns, sort=False, dropna=False)
    samples = []
    for (question, answer), group in duplicate_groups:
        samples.append({
            "occurrences": len(group),
            "question": question,
            "answer_snippet": answer[:300],
            "sources": " | ".join(sorted(group["source"].astype(str).unique())),
            "source_directories": " | ".join(sorted(group["source_directory"].unique())),
            "raw_files_sample": " | ".join(group["raw_file"].head(5)),
        })
    sample_frame = pd.DataFrame(samples).sort_values(["occurrences", "question"], ascending=[False, True])
    sample_frame.head(20).to_csv(output_dir / "dataset_duplicate_samples.csv", index=False)

    cross_source_pairs = sum(group["source_directory"].nunique() > 1 for _, group in duplicate_groups)
    report = [
        "IndicMed MedQuAD Dataset Audit",
        "================================",
        f"Raw XML files processed: {len(xml_files):,}",
        f"Unique relative XML paths: {len(relative_paths):,}",
        f"Byte-identical XML file groups: {len(repeated_file_groups):,}",
        f"Files participating in byte-identical groups: {sum(repeated_file_groups):,}",
        f"Total QAPair XML nodes: {total_pair_nodes:,}",
        f"QAPair nodes with empty questions: {empty_questions:,}",
        f"QAPair nodes with empty answers: {empty_answers:,}",
        f"Raw valid question-answer rows: {len(frame):,}",
        f"Unique questions: {frame['question'].nunique():,}",
        f"Duplicate question rows removed if deduping question only: {len(frame) - frame['question'].nunique():,}",
        f"Unique answers: {frame['answer'].nunique():,}",
        f"Duplicate answer rows removed if deduping answer only: {len(frame) - frame['answer'].nunique():,}",
        f"Unique exact question-answer pairs: {unique_pairs:,}",
        f"Rows removed by current exact-pair deduplication: {removed:,}",
        f"Rows belonging to a repeated exact-pair group: {duplicate_occurrences:,}",
        f"Distinct repeated exact-pair groups: {len(sample_frame):,}",
        f"Repeated exact-pair groups crossing source directories: {cross_source_pairs:,}",
        "",
        "Counts by source/category directory",
        grouped.to_string(index=False),
        "",
        "Top 10 exact duplicate groups",
        sample_frame.head(10).to_string(index=False),
    ]
    report_path = output_dir / "dataset_audit.txt"
    report_path.write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:17]))
    print(f"Saved detailed audit: {report_path}")
    print(f"Saved source counts: {output_dir / 'dataset_audit_by_source.csv'}")
    print(f"Saved duplicate samples: {output_dir / 'dataset_duplicate_samples.csv'}")


if __name__ == "__main__":
    main()
