from __future__ import annotations

from pathlib import Path
from typing import Any

from project_control.config.patterns_loader import get_scan_extensions, load_patterns
from project_control.core.project_initializer import InitializationResult, ensure_project_initialized
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
        auto_init = bool(kwargs.get("auto_init", False))
        initialization: InitializationResult | None = None
        if auto_init:
            initialization = ensure_project_initialized(project_root)

        patterns = load_patterns(project_root)
        snapshot = create_snapshot(
            project_root,
            patterns.get("ignore_dirs", []),
            get_scan_extensions(patterns),
        )
        save_snapshot(snapshot, project_root)

        file_count = snapshot.get("file_count", 0)

        return ServiceResult(
            success=True,
            message=f"Scan complete. {file_count} files indexed.",
            data={
                "snapshot": snapshot,
                "file_count": file_count,
                "patterns": patterns,
                "initialization": initialization,
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


def run_interactive_scan(project_root: Path) -> ServiceResult:
    """Scan with first-run bootstrap for GUI/TUI flows."""
    return ScanService().execute(project_root, auto_init=True)
