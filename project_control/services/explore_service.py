from __future__ import annotations

from pathlib import Path

from project_control.graph.ensure import ensure_graph
from project_control.cli.graph_cmd import graph_trace
from project_control.services._config import config_with_state
from project_control.ui.state import AppState


def run_trace(project_root: Path, target: str, state: AppState) -> None:
    cfg = config_with_state(project_root, state)
    ensure_graph(project_root, cfg, force=False)
    max_depth = None if state.trace_all_paths else state.trace_depth
    max_paths = None if state.trace_all_paths else 200
    graph_trace(
        project_root=project_root,
        config_path=None,
        target=target,
        direction=state.trace_direction,
        max_depth=max_depth,
        max_paths=max_paths,
        show_line=True,
        config_override=cfg,
    )
