"""Session experiment detector for PROJECT CONTROL."""

from __future__ import annotations

from typing import Any, Dict, List


def detect_session_files(snapshot: Dict[str, Any]) -> List[str]:
    """
    Return any files whose names include 'session' (case-insensitive).

    Args:
        snapshot: Scan snapshot containing a ``files`` list.

    Returns:
        List of relative paths of session files.
    """
    matches: List[str] = []
    for file in snapshot.get("files", []):
        path = file.get("path", "")
        if "session" in path.lower():
            matches.append(path)
    return matches


analyze = lambda snapshot, patterns=None: detect_session_files(snapshot)
