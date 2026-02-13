"""Utilities for scanning a project directory."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, TypedDict


class FileEntry(TypedDict):
    path: str
    size: int
    modified: str


class Snapshot(TypedDict):
    file_count: int
    files: List[FileEntry]


def scan_project(project_root: str, ignore_dirs: List[str], extensions: List[str]) -> Snapshot:
    """
    Walk the project tree and collect file metadata.

    Args:
        project_root: Absolute or relative root directory to scan.
        ignore_dirs: Directory names to exclude (non-recursive filter applied during walk).
        extensions: File extensions to include (dot-prefixed). If empty, include all files.

    Returns:
        Snapshot dictionary containing file_count and a list of files with path, size, modified.
    """
    root_path = Path(project_root).resolve()
    ignore_set = set(ignore_dirs or [])
    ext_set = set(extensions or [])

    snapshot: Snapshot = {"file_count": 0, "files": []}

    for root, dirs, files in os.walk(root_path):
        # In-place filter to prevent walking ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_set]

        for name in files:
            path = Path(root) / name

            if ext_set and path.suffix not in ext_set:
                continue

            stat = path.stat()

            snapshot["files"].append(
                {
                    "path": str(path.relative_to(root_path)),
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                }
            )

    snapshot["file_count"] = len(snapshot["files"])
    return snapshot
