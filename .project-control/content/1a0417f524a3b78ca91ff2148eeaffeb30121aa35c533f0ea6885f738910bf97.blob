"""Content-addressable file storage layer for PHASE 1 separation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple


class ContentStore:
    """
    Provides filesystem-independent access to file contents.
    Reads from snapshot.json and .project-control/content/<sha256>.blob files.
    """

    def __init__(self, snapshot_path: Path):
        """
        Initialize with path to snapshot.json.
        Loads snapshot data and prepares content directory.
        """
        self.snapshot_path = snapshot_path
        self.snapshot = self._load_snapshot()
        self.content_dir = snapshot_path.parent / "content"

    def _load_snapshot(self) -> Dict:
        """Load and parse snapshot.json."""
        with open(self.snapshot_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _find_file_entry(self, path: str) -> Optional[Dict]:
        """Find file entry by path in snapshot."""
        for file in self.snapshot.get("files", []):
            if file.get("path") == path:
                return file
        return None

    def get_text(self, path: str) -> str:
        """
        Get file content by path.
        Looks up SHA256 from snapshot and reads from blob storage.
        """
        entry = self._find_file_entry(path)
        if not entry:
            raise FileNotFoundError(f"Path not found in snapshot: {path}")

        sha256 = entry.get("sha256")
        if not sha256:
            raise ValueError(f"No SHA256 for path: {path}")

        blob_path = self.content_dir / f"{sha256}.blob"
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {blob_path}")

        return blob_path.read_text(encoding="utf-8", errors="ignore")

    def get_blob(self, sha256: str) -> str:
        """Get content directly by SHA256 hash."""
        blob_path = self.content_dir / f"{sha256}.blob"
        if not blob_path.exists():
            raise FileNotFoundError(f"Blob not found: {blob_path}")
        return blob_path.read_text(encoding="utf-8", errors="ignore")

    def has_blob(self, sha256: str) -> bool:
        """Check if blob exists."""
        return (self.content_dir / f"{sha256}.blob").exists()

    def iter_files(self) -> Iterator[Tuple[str, str]]:
        """Iterate over all files with their paths and contents."""
        for file in self.snapshot.get("files", []):
            path = file.get("path")
            if path:
                try:
                    content = self.get_text(path)
                    yield path, content
                except Exception:
                    continue