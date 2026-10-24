"""Download the official MedQuAD repository archive without requiring Git."""
from __future__ import annotations

import argparse
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.utils.helpers import PROJECT_ROOT

ARCHIVE_URL = "https://github.com/abachaa/MedQuAD/archive/refs/heads/master.zip"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "raw" / "medquad"


def download_medquad(output_dir: Path, force: bool = False) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    existing_xml = list(output_dir.rglob("*.xml"))
    if existing_xml and not force:
        print(f"MedQuAD already exists ({len(existing_xml)} XML files); use --force to replace it.")
        return

    with tempfile.TemporaryDirectory(prefix="indicmed_") as temporary:
        temp_dir = Path(temporary)
        archive = temp_dir / "medquad.zip"
        request = urllib.request.Request(ARCHIVE_URL, headers={"User-Agent": "IndicMed-course-project"})
        print(f"Downloading {ARCHIVE_URL}")
        with urllib.request.urlopen(request, timeout=120) as response, archive.open("wb") as target:
            shutil.copyfileobj(response, target)
        with zipfile.ZipFile(archive) as bundle:
            bundle.extractall(temp_dir / "extracted")
        root = next((temp_dir / "extracted").glob("MedQuAD-*"))
        if force and output_dir.exists():
            for child in output_dir.iterdir():
                if child.name != ".gitkeep":
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
        copied = 0
        for source in root.rglob("*.xml"):
            relative = source.relative_to(root)
            destination = output_dir / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            copied += 1
        for filename in ("README.md", "LICENSE.txt"):
            if (root / filename).exists():
                shutil.copy2(root / filename, output_dir / filename)
        if not copied:
            raise RuntimeError("The downloaded archive contained no XML files")
        print(f"Downloaded {copied} XML files to {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    download_medquad(args.output, args.force)
