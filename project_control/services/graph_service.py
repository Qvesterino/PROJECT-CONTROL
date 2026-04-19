from __future__ import annotations

import json
from pathlib import Path

from project_control.graph.ensure import ensure_graph
from project_control.services._config import config_with_state
from project_control.ui.state import AppState


def build_graph(project_root: Path, state: AppState) -> None:
    cfg = config_with_state(project_root, state)
    snapshot_path, metrics_path, report_path = ensure_graph(project_root, cfg, force=False)
    print(f"Graph ready.\nSnapshot: {snapshot_path}\nMetrics: {metrics_path}\nReport: {report_path}")


def show_report(project_root: Path, state: AppState) -> None:
    cfg = config_with_state(project_root, state)
    _, metrics_path, report_path = ensure_graph(project_root, cfg, force=False)
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        metrics = {}
    totals = metrics.get("totals", {})
    print(f"Graph report (reuse if fresh)")
    print(f"- Nodes: {totals.get('nodeCount', '?')}")
    print(f"- Edges: {totals.get('edgeCount', '?')}")
    print(f"- Cycles: {len(metrics.get('cycles', []))}")
    print(f"- Orphans: {len(metrics.get('orphanCandidates', []))}")
    print(f"Report file: {report_path}")
