"""Ghost analysis execution (shallow only)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

from project_control.usecases.ghost_workflow import GhostWorkflow
from project_control.core.snapshot_service import load_snapshot
from project_control.core.dto import ResultValidationError
from project_control.core.exit_codes import EXIT_CONTRACT_ERROR, EXIT_VALIDATION_ERROR, EXIT_OK
from project_control.core.markdown_renderer import render_ghost_report, SEVERITY_MAP


SECTION_DISPLAY_NAMES = {
    "orphans": "Orphans",
    "legacy": "Legacy snippets",
    "session": "Session files",
    "duplicates": "Duplicates",
}

SECTION_LIMIT_ARGS = {
    "orphans": ("max-high", "max_high"),
    "legacy": ("max-medium", "max_medium"),
    "session": ("max-low", "max_low"),
    "duplicates": ("max-info", "max_info"),
}


class LimitViolation(TypedDict):
    message: str
    exit_code: int


class GhostResult(TypedDict):
    dto: Dict[str, Any]
    counts: Dict[str, int]
    limit_violation: Optional[LimitViolation]
    ghost_report_path: Path


def _ensure_control_dirs(project_root: Path) -> Path:
    control_dir = project_root / ".project-control"
    exports_dir = control_dir / "exports"
    control_dir.mkdir(exist_ok=True)
    exports_dir.mkdir(exist_ok=True)
    return exports_dir


def run_ghost(args, project_root: Path) -> Optional[GhostResult]:
    """Execute shallow ghost detectors."""
    _ensure_control_dirs(project_root)

    try:
        snapshot = load_snapshot(project_root)
    except FileNotFoundError:
        print("Run 'pc scan' first.")
        return None

    workflow = GhostWorkflow(project_root, debug=False)

    try:
        dto, _ = workflow.run(
            snapshot,
            compare_snapshot=None,
            deep=False,
            mode=getattr(args, "mode", "pragmatic"),
            history=None,
        )
    except ResultValidationError as exc:
        print("INTERNAL RESULT CONTRACT VIOLATION")
        print(str(exc))
        raise SystemExit(EXIT_CONTRACT_ERROR)

    validation_section = dto.get("validation") or {}
    counts = {key: len(validation_section.get(key, [])) for key in SECTION_DISPLAY_NAMES}

    limit_violation: Optional[LimitViolation] = None
    for key, label in SECTION_DISPLAY_NAMES.items():
        limit_label, attr_name = SECTION_LIMIT_ARGS[key]
        limit_value = getattr(args, attr_name, -1) if hasattr(args, attr_name) else -1
        if limit_value >= 0 and counts[key] > limit_value:
            severity = SEVERITY_MAP.get(key, "INFO")
            limit_violation = {
                "message": f"Ghost limits exceeded: {label}({severity})={counts[key]} > {limit_label}={limit_value}",
                "exit_code": EXIT_VALIDATION_ERROR,
            }
            break

    return {
        "dto": dto,
        "counts": counts,
        "limit_violation": limit_violation,
        "ghost_report_path": Path(".project-control") / "exports" / "ghost_candidates.md",
    }


def write_ghost_reports(result: GhostResult, project_root: Path, args) -> None:
    exports_dir = _ensure_control_dirs(project_root)
    dto = result["dto"]
    validation_section = dto.get("validation") or {}
    ghost_report_path = exports_dir / "ghost_candidates.md"
    render_ghost_report(validation_section, str(ghost_report_path))
    if result.get("limit_violation"):
        print(result["limit_violation"]["message"])
