"""Ghost analysis execution — shallow only, uses canonical ghost core."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from project_control.core.ghost import ghost
from project_control.core.snapshot_service import load_snapshot
from project_control.core.content_store import ContentStore
from project_control.core.markdown_renderer import render_ghost_report, SEVERITY_MAP
from project_control.core.error_handler import (
    FileNotFoundError,
    ValidationError,
    OperationError,
)
from project_control.core.pre_flight import pre_flight_ghost
from project_control.config.patterns_loader import load_patterns
from project_control.utils.tree_formatter import format_file_tree

logger = logging.getLogger(__name__)


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
    """Execute shallow ghost detectors via canonical ghost core.

    Raises:
        FileNotFoundError: If snapshot doesn't exist
        ValidationError: If pre-flight checks fail
        OperationError: If analysis fails
    """
    try:
        # Pre-flight checks
        pre_flight_ghost(project_root)

        # Ensure export directories exist
        _ensure_control_dirs(project_root)

        # Load snapshot
        snapshot = load_snapshot(project_root)
        snapshot_path = project_root / ".project-control" / "snapshot.json"
        content_store = ContentStore(snapshot, snapshot_path)
        patterns = load_patterns(project_root)

        # Call canonical ghost core — pure function, no side effects
        logger.info("Running ghost analysis")
        result = ghost(snapshot, patterns, content_store)

        # Build counts from canonical keys
        counts = {key: len(result.get(key, [])) for key in SECTION_KEYS}
        logger.info(f"Ghost analysis complete: {counts}")

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

    except Exception as e:
        if isinstance(e, (FileNotFoundError, ValidationError, OperationError)):
            raise
        raise OperationError(f"Ghost analysis failed: {e}")


def write_ghost_report(result: Dict[str, Any], project_root: Path) -> None:
    """Write ghost report to markdown file.

    Raises:
        OperationError: If report writing fails
    """
    try:
        exports_dir = _ensure_control_dirs(project_root)
        ghost_report_path = exports_dir / "ghost_candidates.md"
        render_ghost_report(result, str(ghost_report_path))
        logger.info(f"Ghost report written to {ghost_report_path}")
    except (OSError, IOError) as e:
        raise OperationError(f"Failed to write ghost report: {e}")


def write_ghost_tree_report(result: Dict[str, Any], project_root: Path) -> None:
    """Write ghost results as ASCII tree files.

    Creates separate tree files for each ghost category (orphans, legacy, etc.)
    in the exports directory.

    Args:
        result: Ghost analysis result dictionary
        project_root: Root directory of the project

    Raises:
        OperationError: If tree report writing fails
    """
    try:
        exports_dir = _ensure_control_dirs(project_root)

        # Write tree for each category
        for key in SECTION_KEYS:
            items = result.get(key, [])
            if not items:
                continue

            # Convert items to list of strings (handle both string and dict items)
            paths: List[str] = []
            for item in items:
                if isinstance(item, str):
                    paths.append(item)
                elif isinstance(item, dict):
                    # For dict items, try to get 'path' or similar field
                    path = item.get("path") or item.get("file") or str(item)
                    paths.append(path)
                else:
                    paths.append(str(item))

            # Format as tree
            display_name = SECTION_DISPLAY_NAMES.get(key, key)
            tree_text = format_file_tree(
                paths,
                root_label=display_name,
                show_counts=True
            )

            # Write to file
            filename = f"ghost_{key}_tree.txt"
            tree_path = exports_dir / filename
            tree_path.write_text(tree_text, encoding="utf-8")
            logger.info(f"Ghost tree report written to {tree_path}")

    except (OSError, IOError) as e:
        raise OperationError(f"Failed to write ghost tree report: {e}")
