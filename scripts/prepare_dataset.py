"""Parse MedQuAD XML into a normalized, retrieval-ready CSV."""
from __future__ import annotations

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.preprocessing.clean_text import clean_text
from src.utils.helpers import PROJECT_ROOT

COLUMNS = ["id", "question", "answer", "category", "source", "source_url"]


def _first_text(element: ET.Element, names: tuple[str, ...]) -> str:
    for name in names:
        node = element.find(name)
        if node is not None and node.text:
            return clean_text(node.text)
    return ""


def _attribute(element: ET.Element, *names: str) -> str:
    lowered = {key.lower(): value for key, value in element.attrib.items()}
    for name in names:
        if lowered.get(name.lower()):
            return clean_text(lowered[name.lower()])
    return ""


def parse_xml(path: Path, raw_root: Path) -> list[dict[str, str]]:
    root = ET.parse(path).getroot()
    relative = path.relative_to(raw_root).as_posix()
    category = _attribute(root, "Name", "Category", "Focus") or path.parent.name
    source = _attribute(root, "Source", "Name") or path.parent.name
    source_url = _attribute(root, "URL", "SourceURL")
    rows: list[dict[str, str]] = []
    pairs = root.findall(".//QAPair")
    for position, pair in enumerate(pairs):
        question_node = pair.find("Question")
        answer_node = pair.find("Answer")
        question = clean_text(question_node.text if question_node is not None else "")
        answer = clean_text(answer_node.text if answer_node is not None else "")
        if not question or not answer:
            continue
        pair_id = _attribute(pair, "pid", "id")
        stable_key = f"{relative}|{pair_id or position}|{question}"
        row_id = "medquad-" + hashlib.sha1(stable_key.encode("utf-8")).hexdigest()[:16]
        row_category = (
            _attribute(question_node, "type", "focus") if question_node is not None else ""
        ) or category
        rows.append(
            {
                "id": row_id,
                "question": question,
                "answer": answer,
                "category": row_category,
                "source": source,
                "source_url": source_url,
            }
        )
    return rows


def prepare(raw_dir: Path, output: Path) -> pd.DataFrame:
    xml_files = sorted(raw_dir.rglob("*.xml"))
    if not xml_files:
        raise FileNotFoundError(
            f"No MedQuAD XML files found under {raw_dir}. Run: python scripts/download_dataset.py"
        )
    rows: list[dict[str, str]] = []
    failures: list[str] = []
    for path in xml_files:
        try:
            rows.extend(parse_xml(path, raw_dir))
        except ET.ParseError as error:
            failures.append(f"{path}: {error}")
    frame = pd.DataFrame(rows, columns=COLUMNS)
    frame = frame.drop_duplicates(subset=["question", "answer"]).reset_index(drop=True)
    if frame.empty:
        raise RuntimeError("XML files were found, but no valid question-answer pairs were parsed")
    output.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(output, index=False, encoding="utf-8")
    frame.to_csv(output.with_name("medical_faqs.csv"), index=False, encoding="utf-8")
    print(f"Prepared {len(frame):,} unique QA pairs from {len(xml_files):,} XML files")
    print(f"Skipped malformed files: {len(failures)}")
    print(f"Saved: {output}")
    return frame


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", type=Path, default=PROJECT_ROOT / "data/raw/medquad")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/processed/medquad_clean.csv")
    args = parser.parse_args()
    prepare(args.raw_dir, args.output)
