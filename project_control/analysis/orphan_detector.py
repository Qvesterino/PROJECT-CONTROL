"""Detector for smart ghost orphan candidates."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List

from project_control.utils.fs_helpers import run_rg


CODE_EXTENSIONS = {".js", ".ts", ".py"}


def _reference_patterns(token: str) -> List[str]:
    escaped = re.escape(token)
    return [
        fr"import .*{escaped}",
        fr"from .*{escaped}",
        fr"require\(.*{escaped}",
    ]


def detect_orphans(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[str]:
    """
    Identify code files that do not appear to be referenced elsewhere.

    Args:
        snapshot: Scan snapshot structure with at least a ``files`` list.
        patterns: Configuration that may contain ``entrypoints`` to skip.

    Returns:
        List of relative file paths that look orphaned.
    """
    entrypoints = {Path(entry).name for entry in patterns.get("entrypoints", [])}
    orphans: List[str] = []

    for file in snapshot.get("files", []):
        rel_path = file.get("path")
        if not rel_path:
            continue

        path = Path(rel_path)
        if path.suffix not in CODE_EXTENSIONS:
            continue

        if path.name in entrypoints:
            continue

        name_without_ext = path.stem
        if not name_without_ext:
            continue

        patterns_to_check = _reference_patterns(name_without_ext)
        if any(run_rg(p).strip() for p in patterns_to_check):
            continue

        orphans.append(rel_path)

    return orphans


analyze = detect_orphans
