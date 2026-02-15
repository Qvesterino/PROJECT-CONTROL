"""Snapshot creation and persistence services."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from core.scanner import scan_project


def create_snapshot(project_root: Path, ignore_dirs, extensions) -> Dict[str, Any]:
    """Create a scan snapshot and attach generation metadata."""
    snapshot = scan_project(str(project_root), ignore_dirs, extensions)
    snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()
    return snapshot


def save_snapshot(snapshot: Dict[str, Any], project_root: Path) -> None:
    """Persist snapshot JSON under .project-control/snapshot.json."""
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    with snapshot_path.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)


def load_snapshot(project_root: Path) -> Dict[str, Any]:
    """Load snapshot JSON or raise when missing."""
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    if not snapshot_path.exists():
        raise FileNotFoundError("Snapshot not found. Run scan first.")

    with snapshot_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def get_snapshot_files(project_root: Path) -> List[Dict[str, Any]]:
    """Return file entries from the current snapshot."""
    snapshot = load_snapshot(project_root)
    return snapshot.get("files", [])
