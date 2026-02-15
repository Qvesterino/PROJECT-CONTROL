"""Legacy file detector for PROJECT CONTROL."""

from __future__ import annotations

from typing import Any, Dict, List


def _normalize_patterns(patterns: List[str]) -> List[str]:
    return [pattern.lower().strip() for pattern in patterns if pattern.strip()]


def detect_legacy(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[str]:
    """
    Identify legacy files by filename patterns configured in patterns.yaml.

    Args:
        snapshot: Scan snapshot with a ``files`` list that includes ``path`` entries.
        patterns: Configuration which should expose ``legacy_patterns`` as a list of keywords.

    Returns:
        Paths from the snapshot whose filenames contain any of the configured legacy patterns.
    """
    legacy_patterns = _normalize_patterns(patterns.get("legacy_patterns", []))
    if not legacy_patterns:
        return []

    legacy_files: List[str] = []

    for file in snapshot.get("files", []):
        path_value = file.get("path")
        if not path_value:
            continue

        lowered_path = path_value.lower()
        if any(pattern in lowered_path for pattern in legacy_patterns):
            legacy_files.append(path_value)

    return legacy_files


analyze = detect_legacy
