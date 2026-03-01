from __future__ import annotations

import json
from pathlib import Path

from project_control.core.ghost import analyze_ghost
from project_control.ui.state import AppState
from project_control.graph.ensure import ensure_graph
from project_control.config.graph_config import GraphConfig, load_graph_config


def ghost_fast(project_root: Path) -> None:
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    if not snapshot_path.exists():
        print("Run pc scan first.")
        return
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    result = analyze_ghost(snapshot, {}, snapshot_path, deep=False)
    counts = {k: len(v) for k, v in result.items() if isinstance(v, list)}
    print("Ghost detectors (shallow):")
    for k, v in sorted(counts.items()):
        print(f"- {k}: {v}")


def ghost_structural(project_root: Path, state: AppState) -> None:
    cfg = _config_with_state(project_root, state)
    _, metrics_path, _ = ensure_graph(project_root, cfg, force=False)
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        print("Metrics unavailable; run graph build first.")
        return
    totals = metrics.get("totals", {})
    cycles = metrics.get("cycles", [])
    orphans = metrics.get("orphanCandidates", [])
    print("Structural graph findings (from metrics):")
    print(f"- Nodes: {totals.get('nodeCount', '?')}")
    print(f"- Edges: {totals.get('edgeCount', '?')}")
    print(f"- Cycles: {len(cycles)}")
    print(f"- Orphans: {len(orphans)}")


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
