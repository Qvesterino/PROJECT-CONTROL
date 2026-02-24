"""Graph configuration loading for JS/TS dependency analysis."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml


DEFAULT_INCLUDE_GLOBS = ["**/*.js", "**/*.jsx", "**/*.ts", "**/*.tsx", "**/*.mjs", "**/*.cjs", "**/*.py"]
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

DEFAULT_LANGUAGES = {
    "js_ts": {
        "enabled": True,
        "include_exts": [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"],
    },
    "python": {
        "enabled": False,
        "include_exts": [".py"],
    },
}


@dataclass(frozen=True)
class GraphConfig:
    include_globs: List[str] = field(default_factory=lambda: list(DEFAULT_INCLUDE_GLOBS))
    exclude_globs: List[str] = field(default_factory=lambda: list(DEFAULT_EXCLUDE_GLOBS))
    entrypoints: List[str] = field(default_factory=lambda: list(DEFAULT_ENTRYPOINTS))
    alias: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_ALIAS))
    orphan_allow_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_ORPHAN_ALLOW))
    treat_dynamic_imports_as_edges: bool = True
    languages: Dict[str, Dict[str, object]] = field(default_factory=lambda: dict(DEFAULT_LANGUAGES))

    def to_dict(self) -> Dict[str, object]:
        return {
            "include_globs": list(self.include_globs),
            "exclude_globs": list(self.exclude_globs),
            "entrypoints": list(self.entrypoints),
            "alias": dict(self.alias),
            "orphan_allow_patterns": list(self.orphan_allow_patterns),
            "treat_dynamic_imports_as_edges": self.treat_dynamic_imports_as_edges,
            "languages": {k: dict(v) for k, v in self.languages.items()},
        }

    def enabled_extensions(self) -> List[str]:
        """Flatten enabled language extensions."""
        exts: List[str] = []
        for body in self.languages.values():
            if not isinstance(body, dict):
                continue
            if not body.get("enabled", False):
                continue
            for ext in body.get("include_exts", []):
                if isinstance(ext, str):
                    exts.append(ext)
        return sorted(set(exts))


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
        treat_dynamic_imports_as_edges=bool(
            merged.get("treat_dynamic_imports_as_edges", defaults.treat_dynamic_imports_as_edges)
        ),
        languages=_parse_languages(merged.get("languages"), defaults.languages),
    )


def _parse_languages(raw: object, defaults: Dict[str, Dict[str, object]]) -> Dict[str, Dict[str, object]]:
    """
    Merge user-provided language config with defaults.
    Expected shape:
    languages:
      js_ts:
        enabled: true
        include_exts: [".js", ".ts"]
    """
    if not isinstance(raw, dict):
        return dict(defaults)

    merged: Dict[str, Dict[str, object]] = dict(defaults)
    for name, body in raw.items():
        if not isinstance(body, dict):
            continue
        enabled = bool(body.get("enabled", defaults.get(name, {}).get("enabled", False)))
        include_exts = body.get("include_exts", defaults.get(name, {}).get("include_exts", []))
        merged[name] = {
            "enabled": enabled,
            "include_exts": list(include_exts) if isinstance(include_exts, list) else [],
        }
    return merged


def hash_config(config: GraphConfig) -> str:
    """Compute deterministic hash of config contents."""
    payload = json.dumps(config.to_dict(), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
