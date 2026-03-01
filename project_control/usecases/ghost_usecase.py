"""Orchestrates ghost analysis without CLI or persistence side effects."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from project_control.config.patterns_loader import load_patterns
from project_control.core.dto import GhostAnalysisResult
from project_control.core.snapshot_validator import validate_snapshot
from project_control.core.ghost import analyze_ghost


class GhostUseCase:
    def __init__(self, project_root: Path, debug: bool = False):
        self.project_root = project_root
        self.debug = debug
        self.snapshot_path = project_root / ".project-control" / "snapshot.json"
        self.patterns = load_patterns(self.project_root)

    def run(
        self,
        snapshot: Dict[str, Any],
        compare_snapshot: Optional[Dict[str, Any]] = None,
        enable_drift: bool = False,
        enable_trend: bool = False,
        mode: str = "pragmatic",
        deep: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute ghost analysis and return structured results.

        Returns existing analysis shape with optional drift/trend fields:
        {
            "orphans": [...],
            "legacy": [...],
            "session": [...],
            "duplicates": [...],
            "semantic_findings": [...],
            "graph_orphans": [...],
            "graph": {...},
            "metrics": {...},
            "anomalies": {...},
            "entrypoints": [...],
            "drift": {...} | None,
            "trend": {...} | None,
        }
        """
        validate_snapshot(snapshot)
        if self.debug:
            print(f"Snapshot schema validated ({len(snapshot.get('files', []))} files)")

        # Only compute drift when explicitly enabled and comparison is provided.
        compare = compare_snapshot if enable_drift else None

        analysis = analyze_ghost(
            snapshot,
            self.patterns,
            self.snapshot_path,
            mode=mode,
            deep=False if deep else False,
            compare_snapshot=None,
            debug=self.debug,
        )

        raw_graph = analysis.get("graph", {})
        graph = dict(raw_graph) if isinstance(raw_graph, dict) else {}
        if "nodes" not in graph:
            graph["nodes"] = list(raw_graph.keys()) if isinstance(raw_graph, dict) else []
        if "edges" not in graph and isinstance(raw_graph, dict):
            graph["edges"] = sum(len(v) for v in raw_graph.values())
        metrics = analysis.get("metrics", {})
        anomalies = analysis.get("anomalies", {})
        drift = analysis.get("drift") if enable_drift else None
        trend = analysis.get("trend") if enable_trend else None

        assert isinstance(graph, dict)
        assert isinstance(metrics, dict)
        assert isinstance(anomalies, dict)

        # Expose full analysis for layers that still need legacy fields (orphans, etc.).
        self.last_analysis = analysis

        result = GhostAnalysisResult(
            graph=graph,
            metrics=metrics,
            anomalies=anomalies,
            drift=drift,
            trend=trend,
        )

        result.validate()
        return analysis
