"""Audit retention execution and export helpers."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from project_control.analysis.audit_retention_detector import analyze
from project_control.config.patterns_loader import load_patterns
from project_control.core.audit_retention_report_renderer import render_audit_retention_report
from project_control.core.content_store import ContentStore
from project_control.core.error_handler import FileNotFoundError, OperationError, ValidationError
from project_control.core.pre_flight import require_healthy_snapshot
from project_control.core.snapshot_service import load_snapshot

logger = logging.getLogger(__name__)


def _ensure_exports_dir(project_root: Path) -> Path:
    exports_dir = project_root / ".project-control" / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    return exports_dir


def _apply_cli_overrides(patterns: dict[str, Any], args: Any) -> dict[str, Any]:
    merged = dict(patterns)
    audit_retention = dict(merged.get("audit_retention", {}))
    older_than = getattr(args, "older_than", None)
    min_score = getattr(args, "min_score", None)
    keep_latest = getattr(args, "keep_latest", None)
    if older_than is not None:
        audit_retention["older_than_days"] = older_than
    if min_score is not None:
        audit_retention["min_score"] = min_score
    if keep_latest is not None:
        audit_retention["keep_latest_per_family"] = keep_latest
    merged["audit_retention"] = audit_retention
    return merged


def run_audit_retention(args: Any, project_root: Path) -> dict[str, Any]:
    """Run audit retention analysis and return structured results plus export paths."""
    try:
        require_healthy_snapshot(project_root, operation="audit retention")
        exports_dir = _ensure_exports_dir(project_root)

        snapshot = load_snapshot(project_root)
        snapshot_path = project_root / ".project-control" / "snapshot.json"
        content_store = ContentStore(snapshot, snapshot_path)
        patterns = _apply_cli_overrides(load_patterns(project_root), args)

        result = analyze(snapshot, patterns, content_store)

        markdown_path = exports_dir / "audit_retention_candidates.md"
        json_path = exports_dir / "audit_retention_candidates.json"
        delete_list_path = exports_dir / "audit_delete_candidates.txt"

        render_audit_retention_report(result, markdown_path)
        json_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        delete_list_path.write_text(
            "\n".join(result.get("delete_candidates", [])) + ("\n" if result.get("delete_candidates") else ""),
            encoding="utf-8",
        )

        logger.info("Audit retention report written to %s", markdown_path)
        return {
            "result": result,
            "paths": {
                "markdown": markdown_path,
                "json": json_path,
                "delete_list": delete_list_path,
            },
        }
    except Exception as error:
        if isinstance(error, (FileNotFoundError, ValidationError, OperationError)):
            raise
        raise OperationError(f"Audit retention analysis failed: {error}")
