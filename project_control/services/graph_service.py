from __future__ import annotations

import json
from pathlib import Path

from project_control.config.graph_config import GraphConfig, load_graph_config
from project_control.graph.ensure import ensure_graph
from project_control.ui.state import AppState


def _config_with_state(project_root: Path, state: AppState) -> GraphConfig:
    cfg = load_graph_config(project_root, None)
    languages = cfg.languages
    languages["js_ts"]["enabled"] = state.project_mode in ("js_ts", "mixed")
    languages["python"]["enabled"] = state.project_mode in ("python", "mixed")
    return GraphConfig(
        include_globs=list(cfg.include_globs),
        exclude_globs=list(cfg.exclude_globs),
        entrypoints=list(cfg.entrypoints),
        alias=dict(cfg.alias),
        orphan_allow_patterns=list(cfg.orphan_allow_patterns),
        treat_dynamic_imports_as_edges=cfg.treat_dynamic_imports_as_edges,
        languages=languages,
    )


def build_graph(project_root: Path, state: AppState) -> None:
    cfg = _config_with_state(project_root, state)
    snapshot_path, metrics_path, report_path = ensure_graph(project_root, cfg, force=False)
    print(f"Graph ready.\nSnapshot: {snapshot_path}\nMetrics: {metrics_path}\nReport: {report_path}")


def show_report(project_root: Path, state: AppState) -> None:
    cfg = _config_with_state(project_root, state)
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
