"""Smart ghost analysis orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

from analysis import (
    duplicate_detector,
    legacy_detector,
    orphan_detector,
    session_detector,
)


class Detector(Protocol):
    def analyze(self, snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Any]:
        ...


def _run_detector(module: Any, snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Any]:
    analyzer = getattr(module, "analyze", None)
    if callable(analyzer):
        return analyzer(snapshot, patterns)
    return []


def analyze_ghost(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> Dict[str, List[Any]]:
    """Run every ghost detector and combine their findings."""
    result = {
        "orphans": _run_detector(orphan_detector, snapshot, patterns),
        "legacy": _run_detector(legacy_detector, snapshot, patterns),
        "session": _run_detector(session_detector, snapshot, patterns),
        "duplicates": _run_detector(duplicate_detector, snapshot, patterns),
    }

    result["orphans"] = sorted(result["orphans"], key=lambda p: p.lower())
    return result
