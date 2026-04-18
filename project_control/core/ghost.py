"""
GHOST CORE CONTRACT:

* Tento modul je jediný zdroj pravdy pre ghost analysis.
* Neobsahuje žiadnu deep/anomaly/drift logiku.
* Akékoľvek pokročilé analýzy patria do experimental layer.
"""

from __future__ import annotations

from typing import Any, Dict, List

from project_control.core.content_store import ContentStore
from project_control.analysis import (
    duplicate_detector,
    legacy_detector,
    orphan_detector,
    session_detector,
    semantic_detector,
)


def _run_detector(module: Any, snapshot: Dict[str, Any], patterns: Dict[str, Any], content_store: ContentStore) -> List[Any]:
    analyzer = getattr(module, "analyze", None)
    if callable(analyzer):
        return analyzer(snapshot, patterns, content_store)
    return []


def ghost(snapshot: Dict[str, Any], patterns: Dict[str, Any], content_store: ContentStore) -> Dict[str, List[Any]]:
    """
    Run shallow ghost detectors. Pure function, no side effects.

    Args:
        snapshot: The snapshot dictionary containing file metadata.
        patterns: Configuration patterns for detectors.
        content_store: ContentStore for filesystem-independent content access.

    Returns:
        Dict with exactly these keys:
        {
            "orphans": list,
            "legacy": list,
            "duplicates": list,
            "sessions": list,
            "semantic": list,
        }
    """
    return {
        "orphans": sorted(_run_detector(orphan_detector, snapshot, patterns, content_store), key=lambda p: str(p).lower()),
        "legacy": _run_detector(legacy_detector, snapshot, patterns, content_store),
        "duplicates": _run_detector(duplicate_detector, snapshot, patterns, content_store),
        "sessions": _run_detector(session_detector, snapshot, patterns, content_store),
        "semantic": _run_detector(semantic_detector, snapshot, patterns, content_store),
    }
