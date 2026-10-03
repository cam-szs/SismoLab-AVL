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

    def load(
        self,
        path: str | Path,
        mode: str = "replace",
        current: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Load JSON, optionally merging it into an existing state."""
        with Path(path).open("r", encoding="utf-8") as source:
            data = json.load(source)
        if not isinstance(data, dict):
            raise ValueError("scenario JSON must contain an object")
        if mode not in {"replace", "merge"}:
            raise ValueError("load mode must be 'replace' or 'merge'")
        if mode == "replace":
            return data
        if current is None:
            return data
        return self.merge_state(current, data)

    def merge_state(self, current: dict[str, Any], patch: dict[str, Any]) -> dict[str, Any]:
        """Return a deep-merged state using the incoming patch semantics."""
        if not isinstance(current, dict) or not isinstance(patch, dict):
            raise ValueError("state and patch must be dictionaries")
        return self._merge_dicts(current, patch)

    def save_state(self, path: str | Path, data: dict[str, Any]) -> None:
        """Export application data as UTF-8 JSON."""
        self.export(path, data)

    def load_state(
        self,
        path: str | Path,
        mode: str = "replace",
        current: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Compatibility alias for the project's persistence API."""
        return self.load(path, mode=mode, current=current)

    def export(self, path: str | Path, data: dict[str, Any]) -> None:
        """Export application data as UTF-8 JSON."""
        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8") as target:
            json.dump(data, target, indent=2, ensure_ascii=False)
            target.write("\n")

    @staticmethod
    def validate_topology(tree: dict[str, Any] | None) -> None:
        """Validate a serialized BST topology before replacing live state."""
        seen: set[int] = set()

        def visit(node: dict[str, Any] | None, lower: Any = None, upper: Any = None) -> int:
            if node is None:
                return -1
            if not isinstance(node, dict) or not isinstance(node.get("key"), dict):
                raise ValueError("invalid topology node")
            key = node["key"]
            identity = int(key["event_id"])
            if identity in seen:
                raise ValueError(f"duplicate topology event {identity}")
            seen.add(identity)
            comparable = (
                int(key["priority"]),
                int(key["magnitude_tenths"]),
                identity,
            )
            if lower is not None and comparable <= lower:
                raise ValueError("topology violates global BST ordering")
            if upper is not None and comparable >= upper:
                raise ValueError("topology violates global BST ordering")
            left_height = visit(node.get("izquierdo"), lower, comparable)
            right_height = visit(node.get("derecho"), comparable, upper)
            expected = 1 + max(left_height, right_height)
            if int(node.get("height", expected)) != expected:
                raise ValueError(f"invalid stored height for event {identity}")
            expected_factor = left_height - right_height
            if int(node.get("factor_balanceo", expected_factor)) != expected_factor:
                raise ValueError(f"invalid stored balance for event {identity}")
            return expected

        visit(tree)
