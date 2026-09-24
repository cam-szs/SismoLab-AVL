"""[BOILERPLATE - implemented] JSON persistence boundary."""

import json
from pathlib import Path
from typing import Any


class PersistenceService:
    """Load and save scenario-shaped JSON documents."""

    def load(self, path: str | Path, mode: str = "replace") -> dict[str, Any]:
        """Load JSON using replace or merge mode."""
        with Path(path).open("r", encoding="utf-8") as source:
            data = json.load(source)
        if not isinstance(data, dict):
            raise ValueError("scenario JSON must contain an object")
        if mode not in {"replace", "merge"}:
            raise ValueError("load mode must be 'replace' or 'merge'")
        return data

    def export(self, path: str | Path, data: dict[str, Any]) -> None:
        """Export application data as UTF-8 JSON."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as target:
            json.dump(data, target, indent=2, ensure_ascii=False)
