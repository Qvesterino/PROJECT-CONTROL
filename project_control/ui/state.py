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
    favorites: list[str] = None  # List of frequently traced targets
    history: list[str] = None  # List of recent actions
    onboarding_seen: bool = False  # Whether user has seen onboarding

    def __post_init__(self):
        if self.favorites is None:
            self.favorites = []
        if self.history is None:
            self.history = []


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
        favorites=data.get("favorites", []),
        history=data.get("history", []),
        onboarding_seen=data.get("onboarding_seen", False),
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
        "favorites": state.favorites,
        "history": state.history,
        "onboarding_seen": state.onboarding_seen,
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def add_to_history(state: AppState, action: str) -> AppState:
    """Add action to history, keeping only last 10."""
    new_history = [action] + state.history[:9]  # Keep last 10
    return AppState(
        project_mode=state.project_mode,
        graph_profile=state.graph_profile,
        trace_direction=state.trace_direction,
        trace_depth=state.trace_depth,
        trace_all_paths=state.trace_all_paths,
        favorites=state.favorites,
        history=new_history,
        onboarding_seen=state.onboarding_seen,
    )


def add_to_favorites(state: AppState, target: str) -> AppState:
    """Add target to favorites if not already present."""
    if target in state.favorites:
        return state
    new_favorites = state.favorites + [target]
    return AppState(
        project_mode=state.project_mode,
        graph_profile=state.graph_profile,
        trace_direction=state.trace_direction,
        trace_depth=state.trace_depth,
        trace_all_paths=state.trace_all_paths,
        favorites=new_favorites,
        history=state.history,
        onboarding_seen=state.onboarding_seen,
    )


def remove_from_favorites(state: AppState, target: str) -> AppState:
    """Remove target from favorites."""
    new_favorites = [f for f in state.favorites if f != target]
    return AppState(
        project_mode=state.project_mode,
        graph_profile=state.graph_profile,
        trace_direction=state.trace_direction,
        trace_depth=state.trace_depth,
        trace_all_paths=state.trace_all_paths,
        favorites=new_favorites,
        history=state.history,
        onboarding_seen=state.onboarding_seen,
    )