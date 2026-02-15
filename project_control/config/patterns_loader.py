"""Pattern configuration loader for PROJECT CONTROL."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict

import yaml

LOGGER = logging.getLogger(__name__)


_DEFAULT_PATTERNS: Dict[str, Any] = {
    "writers": ["scale", "emissive", "opacity", "position"],
    "entrypoints": ["main.js", "index.ts"],
    "ignore_dirs": [".git", ".project-control", "node_modules", "__pycache__"],
    "extensions": [".py", ".js", ".ts", ".md", ".txt"],
}


def _default_patterns() -> Dict[str, Any]:
    """Return a fresh copy of default patterns so callers can mutate safely."""
    return {key: value.copy() if isinstance(value, list) else value for key, value in _DEFAULT_PATTERNS.items()}


def load_patterns(project_root: str) -> Dict[str, Any]:
    """
    Read the patterns.yaml stored in `project_root/.project-control`.

    Returns defaults when the file is missing or invalid and merges any loaded
    values on top so callers don't have to spread defaults everywhere.
    """
    config_path = Path(project_root) / ".project-control" / "patterns.yaml"

    if not config_path.is_file():
        return _default_patterns()

    try:
        with config_path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
    except (yaml.YAMLError, OSError) as error:
        LOGGER.debug("Failed to load patterns from %s: %s", config_path, error)
        return _default_patterns()

    patterns = _default_patterns()
    patterns.update(data)
    return patterns
