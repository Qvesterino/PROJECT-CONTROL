from __future__ import annotations

from pathlib import Path

from project_control.graph.ensure import ensure_graph
from project_control.cli.graph_cmd import graph_trace
from project_control.config.graph_config import load_graph_config, GraphConfig
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


def run_trace(project_root: Path, target: str, state: AppState) -> None:
    cfg = _config_with_state(project_root, state)
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
