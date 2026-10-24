from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | Path) -> Path:
    """Resolve a configured path relative to the project root."""
    value = Path(path)
    return value if value.is_absolute() else PROJECT_ROOT / value


def load_config(path: str | Path = "config/config.yaml") -> dict[str, Any]:
    config_path = resolve_project_path(path)
    with config_path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)

