"""Graph configuration loading for JS/TS dependency analysis."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


DEFAULT_INCLUDE_GLOBS = ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.mjs", "**/*.cjs"]
DEFAULT_EXCLUDE_GLOBS = ["**/node_modules/**", "**/dist/**", "**/build/**", ".git/**"]
DEFAULT_ENTRYPOINTS = ["main.js", "index.ts"]
DEFAULT_ALIAS = {"@/": "src/"}
DEFAULT_ORPHAN_ALLOW = [
    "**/*.test.*",
    "**/*.spec.*",
    "**/*.stories.*",
    "**/scripts/**",
    "**/__tests__/**",
]


@dataclass(frozen=True)
class GraphConfig:
    include_globs: List[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_GLOBS))
    exclude_globs: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_GLOBS))
    entrypoints: List[str] = field(default_factory=lambda: list(DEFAULT_ENTRYPOINTS))
    alias: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ALIAS))
    orphan_allow_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_ORPHAN_ALLOW))
    treat_dynamic_imports_as_edges: bool = True

    def to_dict(self) -> Dict[str, object]:
        return {
            "include_globs": list(self.include_globs),
            "exclude_globs": list(self.exclude_globs),
            "entrypoints": list(self.entrypoints),
            "alias": dict(self.alias),
            "orphan_allow_patterns": list(self.orphan_allow_patterns),
            "treat_dynamic_imports_as_edges": self.treat_dynamic_imports_as_edges,
        }


def _load_yaml(path: Path) -> Dict[str, object]:
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream) or {}
        if not isinstance(data, dict):
            return {}
        return data


def load_graph_config(project_root: Path, config_path: Optional[Path] = None) -> GraphConfig:
    """
    Load graph configuration from YAML. Falls back to defaults when missing/invalid.
    Order: explicit --config path, then .project-control/graph.config.yaml, else defaults.
    """
    candidates = []
    if config_path:
        candidates.append(config_path)
    candidates.append(project_root / ".project-control" / "graph.config.yaml")

    merged: Dict[str, object] = {}
    for path in candidates:
        if path and path.is_file():
            try:
                merged = _load_yaml(path)
                break
            except Exception:
                merged = {}
                break

    defaults = GraphConfig()
    if not merged:
        return defaults

    return GraphConfig(
        include_globs=list(merged.get("include_globs", defaults.include_globs)),
        exclude_globs=list(merged.get("exclude_globs", defaults.exclude_globs)),
        entrypoints=list(merged.get("entrypoints", defaults.entrypoints)),
        alias=dict(merged.get("alias", defaults.alias)),
        orphan_allow_patterns=list(merged.get("orphan_allow_patterns", defaults.orphan_allow_patterns)),
        treat_dynamic_imports_as_edges=bool(merged.get("treat_dynamic_imports_as_edges", defaults.treat_dynamic_imports_as_edges)),
    )


def hash_config(config: GraphConfig) -> str:
    """Compute deterministic hash of config contents."""
    payload = json.dumps(config.to_dict(), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
