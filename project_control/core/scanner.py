"""Utilities for scanning a project directory."""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import List, TypedDict

from project_control.utils.progress import ProgressBar

logger = logging.getLogger(__name__)


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

    # Phase 1: Collect file paths
    logger.info("Collecting file paths...")
    file_paths: List[Path] = []

    for root, dirs, filenames in os.walk(root_path):
        dirs[:] = [d for d in dirs if d not in ignore_set]

        for name in filenames:
            path = Path(root) / name
            if ext_set and path.suffix not in ext_set:
                continue
            file_paths.append(path)

    # Phase 2: Process files with progress bar
    files: List[FileEntry] = []
    total_files = len(file_paths)

    if total_files > 0:
        print(f"Scanning {total_files} files...")
        progress = ProgressBar(total_files, "", show_eta=True)
        logger.info(f"Processing {total_files} files...")

        for idx, path in enumerate(file_paths, 1):
            try:
                rel_path = str(path.relative_to(root_path))
            except ValueError as e:
                logger.warning(f"Cannot get relative path for {path}: {e}")
                progress.update(idx)
                continue

            try:
                data = path.read_bytes()
            except (OSError, IOError) as e:
                logger.warning(f"Failed to read file {path}: {e}")
                progress.update(idx)
                continue

            digest = sha256(data).hexdigest()
            blob_path = content_dir / f"{digest}.blob"

            if not blob_path.exists():
                try:
                    blob_path.write_bytes(data)
                except (OSError, IOError) as e:
                    logger.warning(f"Failed to write blob {blob_path}: {e}")
                    # Continue anyway - we can still process the file

            try:
                stat = path.stat()
                files.append(
                    {
                        "path": rel_path,
                        "size": stat.st_size,
                        "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                        "sha256": digest,
                    }
                )
            except (OSError, IOError) as e:
                logger.warning(f"Failed to stat file {path}: {e}")

            # Update progress
            progress.update(idx)

        progress.finish(f"Scanned {len(files)} files")
    else:
        logger.info("No files found matching criteria")

    # Sort and create snapshot
    files.sort(key=lambda entry: entry["path"])
    concatenated = "".join(f"{entry['path']}{entry['sha256']}" for entry in files)
    snapshot_id = sha256(concatenated.encode("utf-8")).hexdigest()

    return {
        "snapshot_version": 1,
        "snapshot_id": snapshot_id,
        "file_count": len(files),
        "files": files,
    }
