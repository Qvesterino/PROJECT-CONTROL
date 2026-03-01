"""Smart ghost analysis orchestrator."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol
import json

from project_control.core.content_store import ContentStore
from project_control.analysis import (
    duplicate_detector,
    legacy_detector,
    orphan_detector,
    session_detector,
)


class Detector(Protocol):
    def analyze(self, snapshot: Dict[str, Any], patterns: Dict[str, Any], content_store: ContentStore) -> List[Any]:
        ...


def _run_detector(module: Any, snapshot: Dict[str, Any], patterns: Dict[str, Any], content_store: ContentStore) -> List[Any]:
    analyzer = getattr(module, "analyze", None)
    if callable(analyzer):
        return analyzer(snapshot, patterns, content_store)
    return []


def analyze_ghost(
    snapshot: Dict[str, Any],
    patterns: Dict[str, Any],
    snapshot_path: Path,
    mode: str = "pragmatic",
    deep: bool = False,
    compare_snapshot: Optional[Dict[str, Any]] = None,
    debug: bool = False,
    project_root: Optional[Path] = None,
    graph_config: Optional[object] = None,
    force_graph: bool = False,
) -> Dict[str, List[Any]]:
    """
    Run every ghost detector and combine their findings.
    
    Args:
        snapshot: The snapshot dictionary containing file metadata.
        patterns: Configuration patterns for detectors.
        snapshot_path: Path to snapshot.json (used to create ContentStore).
        mode: Analysis mode ("pragmatic" or "strict").
        deep: Whether to run deep analysis (import graph).
        debug: Enable debug output for deep graph analysis.
    """
    # Create ContentStore for filesystem-independent content access
    content_store = ContentStore(snapshot, snapshot_path)
    
    result = {
        "orphans": _run_detector(orphan_detector, snapshot, patterns, content_store),
        "legacy": _run_detector(legacy_detector, snapshot, patterns, content_store),
        "session": _run_detector(session_detector, snapshot, patterns, content_store),
        "duplicates": _run_detector(duplicate_detector, snapshot, patterns, content_store),
        "semantic_findings": [],
        "graph_orphans": [],
        "graph": {},
        "metrics": {},
    }

    result["orphans"] = sorted(result["orphans"], key=lambda p: p.lower())
    if deep:
        print("Deprecated: ghost deep legacy graph removed; falling back to shallow detectors.")
    return result
