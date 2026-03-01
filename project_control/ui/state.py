"""Persistent UI app state."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppState:
    project_mode: str = "js_ts"  # js_ts | python | mixed
    graph_profile: str = "pragmatic"  # pragmatic | strict
    trace_direction: str = "both"  # inbound | outbound | both
    trace_depth: int = 50
    trace_all_paths: bool = False


CONFIG_FILE = "config.json"


def _config_dir(project_root: Path) -> Path:
    return project_root / ".project-control"


def load_state(project_root: Path) -> AppState:
    path = _config_dir(project_root) / CONFIG_FILE
    if not path.exists():
        return AppState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return AppState()
    return AppState(
        project_mode=data.get("project_mode", "js_ts"),
        graph_profile=data.get("graph_profile", "pragmatic"),
        trace_direction=data.get("trace_direction", "both"),
        trace_depth=int(data.get("trace_depth", 50)),
        trace_all_paths=bool(data.get("trace_all_paths", False)),
    )


def save_state(project_root: Path, state: AppState) -> None:
    cfg_dir = _config_dir(project_root)
    cfg_dir.mkdir(parents=True, exist_ok=True)
    path = cfg_dir / CONFIG_FILE
    payload = {
        "project_mode": state.project_mode,
        "graph_profile": state.graph_profile,
        "trace_direction": state.trace_direction,
        "trace_depth": state.trace_depth,
        "trace_all_paths": state.trace_all_paths,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
