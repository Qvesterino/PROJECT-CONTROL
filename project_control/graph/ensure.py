"""Helpers to ensure graph artifacts exist and are fresh."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Tuple

from project_control.config.graph_config import GraphConfig, hash_config, load_graph_config
from project_control.core.content_store import ContentStore
from project_control.core.snapshot_service import load_snapshot
from project_control.graph.builder import GraphBuilder, compute_snapshot_hash
from project_control.graph.metrics import compute_metrics
from project_control.graph.artifacts import write_artifacts


def ensure_graph(project_root: Path, config: GraphConfig | None = None, force: bool = False) -> Tuple[Path, Path, Path]:
    """
    Ensure graph artifacts exist and are in sync with snapshot/config.
    Returns paths (snapshot_json, metrics_json, report_md).
    """
    try:
        snapshot = load_snapshot(project_root)  # may raise FileNotFoundError
    except FileNotFoundError as exc:
        raise FileNotFoundError("Run pc scan first") from exc
    config = config or load_graph_config(project_root, None)

    out_dir = project_root / ".project-control" / "out"
    graph_path = out_dir / "graph.snapshot.json"
    metrics_path = out_dir / "graph.metrics.json"
    report_path = out_dir / "graph.report.md"

    needs_build = force or not graph_path.exists() or not metrics_path.exists()
    if not needs_build:
        try:
            graph_data = json.loads(graph_path.read_text(encoding="utf-8"))
            meta = graph_data.get("meta", {})
            snapshot_hash = meta.get("snapshotHash")
            config_hash = meta.get("configHash")
            current_snapshot_hash = compute_snapshot_hash(snapshot)
            current_config_hash = hash_config(config)
            if snapshot_hash != current_snapshot_hash or config_hash != current_config_hash:
                needs_build = True
        except Exception:
            needs_build = True

    if needs_build:
        snapshot_path = project_root / ".project-control" / "snapshot.json"
        content_store = ContentStore(snapshot, snapshot_path)
        builder = GraphBuilder(project_root, snapshot, content_store, config)
        graph = builder.build()
        metrics = compute_metrics(graph, config)
        snapshot_path_out, metrics_path_out, report_path_out = write_artifacts(project_root, graph, metrics)
        return snapshot_path_out, metrics_path_out, report_path_out

    return graph_path, metrics_path, report_path
