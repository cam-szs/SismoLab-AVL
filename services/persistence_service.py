"""JSON persistence boundary for the scenario state."""

import json
from copy import deepcopy
from pathlib import Path
from typing import Any


class PersistenceService:
    """Load and save scenario-shaped JSON documents."""

    @staticmethod
    def _merge_dicts(base: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        merged = deepcopy(base)
        for key, value in patch.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
                merged[key] = PersistenceService._merge_dicts(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    def load(self, path: str | Path, mode: str = "replace") -> dict[str, Any]:
        """Load JSON using replace or merge mode."""
        with Path(path).open("r", encoding="utf-8") as source:
            data = json.load(source)
        if not isinstance(data, dict):
            raise ValueError("scenario JSON must contain an object")
        if mode not in {"replace", "merge"}:
            raise ValueError("load mode must be 'replace' or 'merge'")
        return data if mode == "replace" else data

    def merge_state(self, current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """Return a deep-merged state using the incoming patch semantics."""
        if not isinstance(current, dict) or not isinstance(patch, dict):
            raise ValueError("state and patch must be dictionaries")
        return self._merge_dicts(current, patch)

    def save_state(self, path: str | Path, data: dict[str, Any]) -> None:
        """Export application data as UTF-8 JSON."""
        self.export(path, data)

    def load_state(self, path: str | Path, mode: str = "replace") -> dict[str, Any]:
        """Compatibility alias for the project's persistence API."""
        return self.load(path, mode=mode)

    def export(self, path: str | Path, data: dict[str, Any]) -> None:
        """Export application data as UTF-8 JSON."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as target:
            json.dump(data, target, indent=2, ensure_ascii=False)
            target.write("\n")
