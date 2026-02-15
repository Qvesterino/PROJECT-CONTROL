"""Smart ghost analysis orchestrator."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol

from project_control.analysis import (
    duplicate_detector,
    legacy_detector,
    orphan_detector,
    session_detector,
)
from project_control.analysis.import_graph_detector import detect_graph_orphans
from project_control.analysis import semantic_detector

class Detector(Protocol):
    def analyze(self, snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Any]:
        ...


def _run_detector(module: Any, snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Any]:
    analyzer = getattr(module, "analyze", None)
    if callable(analyzer):
        return analyzer(snapshot, patterns)
    return []


def analyze_ghost(
    snapshot: Dict[str, Any],
    patterns: Dict[str, Any],
    mode: str = "pragmatic",
    deep: bool = False,
    
) -> Dict[str, List[Any]]:
    """Run every ghost detector and combine their findings."""
    result = {
        "orphans": _run_detector(orphan_detector, snapshot, patterns),
        "legacy": _run_detector(legacy_detector, snapshot, patterns),
        "session": _run_detector(session_detector, snapshot, patterns),
        "duplicates": _run_detector(duplicate_detector, snapshot, patterns),
        "semantic_findings": _run_detector(semantic_detector, snapshot, patterns),
        "graph_orphans": [],
    }

    result["orphans"] = sorted(result["orphans"], key=lambda p: p.lower())
    if deep:
        result["graph_orphans"] = detect_graph_orphans(
            snapshot, patterns, apply_ignore=(mode == "pragmatic")
        )
    return result
