"""CLI handlers for graph build/report commands."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from project_control.config.graph_config import GraphConfig, load_graph_config
from project_control.graph.builder import GraphBuilder
from project_control.graph.metrics import compute_metrics
from project_control.graph.artifacts import write_artifacts
from project_control.core.content_store import ContentStore
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR
from project_control.core.snapshot_service import load_snapshot


def _load_snapshot_or_fail(project_root: Path):
    try:
        return load_snapshot(project_root)
    except FileNotFoundError:
        print("Snapshot not found. Run 'pc scan' first.")
        return None


def graph_build(project_root: Path, config_path: Optional[Path]) -> int:
    snapshot = _load_snapshot_or_fail(project_root)
    if snapshot is None:
        return EXIT_VALIDATION_ERROR

    config = load_graph_config(project_root, config_path)
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    content_store = ContentStore(snapshot, snapshot_path)

    builder = GraphBuilder(project_root, snapshot, content_store, config)
    graph = builder.build()
    metrics = compute_metrics(graph, config)

    snapshot_path_out, metrics_path_out, report_path = write_artifacts(project_root, graph, metrics)
    print(f"Graph snapshot written to: {snapshot_path_out}")
    print(f"Graph metrics written to:  {metrics_path_out}")
    print(f"Graph report written to:   {report_path}")
    return EXIT_OK


def graph_report(project_root: Path, config_path: Optional[Path]) -> int:
    # Report regenerates artifacts to remain deterministic
    return graph_build(project_root, config_path)
