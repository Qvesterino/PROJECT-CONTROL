"""Workflow that orchestrates ghost analysis without persistence concerns."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from project_control.analysis.graph_trend import GraphTrendAnalyzer
from project_control.usecases.ghost_usecase import GhostUseCase


class GhostWorkflow:
    def __init__(self, project_root: Path, debug: bool = False):
        self.project_root = project_root
        self.debug = debug
        self.usecase = GhostUseCase(project_root, debug=debug)

    def run(
        self,
        snapshot: Dict[str, Any],
        compare_snapshot: Optional[Dict[str, Any]] = None,
        deep: bool = False,
        mode: str = "pragmatic",
        history: Optional[List[Dict[str, Any]]] = None,
    ) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Execute ghost analysis and optionally compute trend using provided history.

        Returns a tuple of (analysis_dict, updated_history_list).
        """
        analysis_result = self.usecase.run(
            snapshot,
            compare_snapshot=compare_snapshot,
            enable_drift=deep and compare_snapshot is not None,
            enable_trend=deep and compare_snapshot is not None,
            mode=mode,
            deep=deep,
        )
        analysis = getattr(self.usecase, "last_analysis", {})

        updated_history = history or []
        drift = analysis.get("drift")

        if deep and drift is not None and history is not None:
            new_entry = {"timestamp": datetime.now(timezone.utc).isoformat(), "drift": drift}
            updated_history = history + [new_entry]
            if len(updated_history) >= 2:
                trend = GraphTrendAnalyzer([entry["drift"] for entry in updated_history]).compute()
                if trend:
                    analysis["trend"] = trend

        return analysis, updated_history
