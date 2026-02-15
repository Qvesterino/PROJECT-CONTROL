"""Utilities for scanning a project directory."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import List, TypedDict


class FileEntry(TypedDict):
    path: str
    size: int
    modified: str
    sha256: str


class Snapshot(TypedDict):
    snapshot_version: int
    snapshot_id: str
    file_count: int
    files: List[FileEntry]


def scan_project(project_root: str, ignore_dirs: List[str], extensions: List[str]) -> Snapshot:
    """
    Walk the project tree, capture file contents, and build deterministic snapshot metadata.

    Args:
        project_root: Absolute or relative root directory to scan.
        ignore_dirs: Directory names to exclude (non-recursive filter applied during walk).
        extensions: File extensions to include (dot-prefixed). If empty, include all files.

    Returns:
        Snapshot dictionary containing file metadata and deterministic ID.
    """
    root_path = Path(project_root).resolve()
    ignore_set = set(ignore_dirs or [])
    ext_set = set(extensions or [])
    content_dir = root_path / ".project-control" / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    files: List[FileEntry] = []

    for root, dirs, filenames in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ignore_set]

        for name in filenames:
            path = Path(root) / name
            if ext_set and path.suffix not in ext_set:
                continue

            rel_path = str(path.relative_to(root_path))
            data = path.read_bytes()
            digest = sha256(data).hexdigest()
            blob_path = content_dir / f"{digest}.blob"
            if not blob_path.exists():
                blob_path.write_bytes(data)

            stat = path.stat()
            files.append(
                {
                    "path": rel_path,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "sha256": digest,
                }
            )

    files.sort(key=lambda entry: entry["path"])
    concatenated = "".join(f"{entry['path']}{entry['sha256']}" for entry in files)
    snapshot_id = sha256(concatenated.encode("utf-8")).hexdigest()

    return {
        "snapshot_version": 1,
        "snapshot_id": snapshot_id,
        "file_count": len(files),
        "files": files,
    }
