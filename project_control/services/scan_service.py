from __future__ import annotations

from pathlib import Path
from typing import Any

from project_control.config.patterns_loader import load_patterns
from project_control.core.snapshot_service import create_snapshot, save_snapshot
from project_control.services.base import Service, ServiceResult, with_error_handling


class ScanService:
    """Service for scanning project files and creating snapshot."""

    @with_error_handling
    def execute(self, project_root: Path, **kwargs) -> ServiceResult:
        """Execute scan and return structured result.

        Args:
            project_root: Root path of the project
            **kwargs: Additional parameters (not used for scan)

        Returns:
            ServiceResult with scan results
        """
        patterns = load_patterns(project_root)
        snapshot = create_snapshot(
            project_root,
            patterns.get("ignore_dirs", []),
            patterns.get("extensions", []),
        )
        save_snapshot(snapshot, project_root)

        file_count = snapshot.get("file_count", 0)

        return ServiceResult(
            success=True,
            message=f"Scan complete. {file_count} files indexed.",
            data={
                "snapshot": snapshot,
                "file_count": file_count,
                "patterns": patterns
            },
            exit_code=0
        )


# Backward compatibility
def run_scan(project_root: Path) -> None:
    """Legacy function for backward compatibility.

    Deprecated: Use ScanService().execute() instead.
    """
    service = ScanService()
    result = service.execute(project_root)
    if result.success:
        print(result.message)
    else:
        raise Exception(result.message)
