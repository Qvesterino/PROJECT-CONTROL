"""Ghost analysis execution — shallow only, uses canonical ghost core."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from project_control.core.ghost import ghost
from project_control.core.snapshot_service import load_snapshot
from project_control.core.content_store import ContentStore
from project_control.core.markdown_renderer import render_ghost_report, SEVERITY_MAP
from project_control.config.patterns_loader import load_patterns


# Canonical section keys from ghost core
SECTION_KEYS = ("orphans", "legacy", "duplicates", "sessions", "semantic")

SECTION_DISPLAY_NAMES = {
    "orphans": "Orphans",
    "legacy": "Legacy snippets",
    "sessions": "Session files",
    "duplicates": "Duplicates",
    "semantic": "Semantic findings",
}

SEVERITY_LIMIT_ARGS = {
    "orphans": ("max-high", "max_high"),
    "legacy": ("max-medium", "max_medium"),
    "sessions": ("max-low", "max_low"),
    "duplicates": ("max-info", "max_info"),
}


def _ensure_control_dirs(project_root: Path) -> Path:
    control_dir = project_root / ".project-control"
    exports_dir = control_dir / "exports"
    control_dir.mkdir(exist_ok=True)
    exports_dir.mkdir(exist_ok=True)
    return exports_dir


def run_ghost(args: Any, project_root: Path) -> Optional[Dict[str, Any]]:
    """Execute shallow ghost detectors via canonical ghost core."""
    _ensure_control_dirs(project_root)

    try:
        snapshot = load_snapshot(project_root)
    except FileNotFoundError:
        print("Run 'pc scan' first.")
        return None

    snapshot_path = project_root / ".project-control" / "snapshot.json"
    content_store = ContentStore(snapshot, snapshot_path)
    patterns = load_patterns(project_root)

    # Call canonical ghost core — pure function, no side effects
    result = ghost(snapshot, patterns, content_store)

    # Build counts from canonical keys
    counts = {key: len(result.get(key, [])) for key in SECTION_KEYS}

    # Check limit violations
    limit_violation: Optional[Dict[str, Any]] = None
    for key, label in SECTION_DISPLAY_NAMES.items():
        if key not in SEVERITY_LIMIT_ARGS:
            continue
        limit_label, attr_name = SEVERITY_LIMIT_ARGS[key]
        limit_value = getattr(args, attr_name, -1) if hasattr(args, attr_name) else -1
        if limit_value >= 0 and counts[key] > limit_value:
            severity = SEVERITY_MAP.get(key, "INFO")
            limit_violation = {
                "message": f"Ghost limits exceeded: {label}({severity})={counts[key]} > {limit_label}={limit_value}",
                "exit_code": 1,
            }
            break

    return {
        "result": result,
        "counts": counts,
        "limit_violation": limit_violation,
    }


def write_ghost_report(result: Dict[str, Any], project_root: Path) -> None:
    """Write ghost report to markdown file."""
    exports_dir = _ensure_control_dirs(project_root)
    ghost_report_path = exports_dir / "ghost_candidates.md"
    render_ghost_report(result, str(ghost_report_path))
