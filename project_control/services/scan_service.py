from __future__ import annotations

from pathlib import Path

from project_control.config.patterns_loader import load_patterns
from project_control.core.snapshot_service import create_snapshot, save_snapshot


def run_scan(project_root: Path) -> None:
    patterns = load_patterns(project_root)
    snapshot = create_snapshot(
        project_root,
        patterns.get("ignore_dirs", []),
        patterns.get("extensions", []),
    )
    save_snapshot(snapshot, project_root)
    print(f"Scan complete. {snapshot.get('file_count', 0)} files indexed.")
