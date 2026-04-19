"""Shared config helper for services that need mode-aware GraphConfig."""

from __future__ import annotations

from pathlib import Path

from project_control.config.graph_config import GraphConfig, load_graph_config
from project_control.ui.state import AppState


def config_with_state(project_root: Path, state: AppState) -> GraphConfig:
    """Build a GraphConfig with language enabled/disabled based on AppState mode."""
    cfg = load_graph_config(project_root, None)
    languages = {
        "js_ts": {
            "enabled": state.project_mode in ("js_ts", "mixed"),
            "include_exts": list(cfg.languages.get("js_ts", {}).get("include_exts", [])),
        },
        "python": {
            "enabled": state.project_mode in ("python", "mixed"),
            "include_exts": list(cfg.languages.get("python", {}).get("include_exts", [])),
        },
    }
    return GraphConfig(
        include_globs=list(cfg.include_globs),
        exclude_globs=list(cfg.exclude_globs),
        entrypoints=list(cfg.entrypoints),
        alias=dict(cfg.alias),
        orphan_allow_patterns=list(cfg.orphan_allow_patterns),
        treat_dynamic_imports_as_edges=cfg.treat_dynamic_imports_as_edges,
        languages=languages,
    )
