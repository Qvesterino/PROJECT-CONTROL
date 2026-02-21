"""Workflow that orchestrates ghost analysis without persistence concerns."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from project_control.analysis.graph_trend import GraphTrendAnalyzer
from project_control.core.dto import ResultValidationError
from project_control.usecases.ghost_usecase import GhostUseCase
from project_control.core.result_dto import build_ui_result_dto, validate_ui_result_dto


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

        Returns a tuple of (ui_result_dto, updated_history_list).
        """
        self.usecase.run(
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

        validation_payload = {
            "orphans": analysis.get("orphans", []),
            "legacy": analysis.get("legacy", []),
            "session": analysis.get("session", []),
            "duplicates": analysis.get("duplicates", []),
            "semantic_findings": analysis.get("semantic_findings", []),
            "graph_orphans": analysis.get("graph_orphans", []),
        }

        graph_payload = None
        metrics_payload = analysis.get("metrics") if deep else None
        anomalies_payload = analysis.get("anomalies") if deep else None
        if deep:
            graph_payload = {
                "graph": analysis.get("graph", {}),
                "entrypoints": analysis.get("entrypoints", []),
            }

        drift_payload = analysis.get("drift") if deep else None
        trend_payload = analysis.get("trend") if deep else None

        try:
            dto = build_ui_result_dto(
                mode=mode,
                deep=deep,
                debug=self.debug,
                engine_version=None,
                graph_payload=graph_payload if deep else None,
                metrics_payload=metrics_payload if deep else None,
                anomalies_payload=anomalies_payload if deep else None,
                drift_payload=drift_payload if deep else None,
                trend_payload=trend_payload if deep else None,
                validation_payload=validation_payload,
            )
            validate_ui_result_dto(dto)
        except ValueError as exc:
            raise ResultValidationError(str(exc)) from exc

        return dto, updated_history
