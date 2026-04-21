"""Snapshot creation and persistence services."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from project_control.core.scanner import scan_project
from project_control.core.error_handler import (
    FileNotFoundError,
    CorruptedDataError,
    OperationError,
    Validator,
)
from project_control.core.pre_flight import pre_flight_scan

logger = logging.getLogger(__name__)


def create_snapshot(project_root: Path, ignore_dirs, extensions) -> Dict[str, Any]:
    """Create a scan snapshot and attach generation metadata.

    Raises:
        OperationError: If scan fails
        ValidationError: If pre-flight checks fail
    """
    try:
        # Pre-flight checks
        pre_flight_scan(project_root)

        # Perform scan
        snapshot = scan_project(str(project_root), ignore_dirs, extensions)
        snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()

        logger.info(f"Created snapshot with {snapshot.get('file_count', 0)} files")
        return snapshot
    except Exception as e:
        if isinstance(e, (FileNotFoundError, OperationError)):
            raise
        raise OperationError(f"Failed to create snapshot: {e}")


def save_snapshot(snapshot: Dict[str, Any], project_root: Path) -> None:
    """Persist snapshot JSON under .project-control/snapshot.json.

    Raises:
        OperationError: If save fails
    """
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    
    try:
        # Ensure parent directory exists
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        
        with snapshot_path.open("w", encoding="utf-8") as f:
            json.dump(snapshot, f, indent=2)
        
        logger.info(f"Saved snapshot to {snapshot_path}")
    except (OSError, IOError) as e:
        raise OperationError(f"Failed to save snapshot: {e}")


def load_snapshot(project_root: Path) -> Dict[str, Any]:
    """Load snapshot JSON or raise when missing.

    Raises:
        FileNotFoundError: If snapshot file doesn't exist
        CorruptedDataError: If snapshot is invalid
    """
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    
    # Check file exists
    Validator.require_file_exists(snapshot_path, "Snapshot file")
    
    # Validate JSON is loadable
    Validator.validate_json_loadable(snapshot_path, "Snapshot file")
    
    try:
        with snapshot_path.open("r", encoding="utf-8") as f:
            snapshot = json.load(f)
        
        logger.info(f"Loaded snapshot from {snapshot_path}")
        return snapshot
    except json.JSONDecodeError as e:
        raise CorruptedDataError(
            f"Snapshot contains invalid JSON: {e}",
            details=f"File: {snapshot_path}"
        )
    except Exception as e:
        if isinstance(e, (FileNotFoundError, CorruptedDataError)):
            raise
        raise OperationError(f"Failed to load snapshot: {e}")


def get_snapshot_files(project_root: Path) -> List[Dict[str, Any]]:
    """Return file entries from the current snapshot.

    Raises:
        FileNotFoundError: If snapshot doesn't exist
        CorruptedDataError: If snapshot is invalid
    """
    snapshot = load_snapshot(project_root)
    files = snapshot.get("files", [])
    
    if not isinstance(files, list):
        raise CorruptedDataError(
            "Snapshot 'files' is not a list",
            details=f"Got type: {type(files).__name__}"
        )
    
    return files
