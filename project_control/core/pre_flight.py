"""Pre-flight checks and health monitoring for PROJECT_CONTROL."""

from __future__ import annotations

import json
import logging
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from project_control.core.error_handler import (
    FileNotFoundError,
    DependencyError,
    ValidationError,
    Validator,
)
from project_control.core.validator import (
    validate_snapshot,
    validate_graph,
    validate_patterns_config,
    validate_graph_config,
)

logger = logging.getLogger(__name__)


# ── Health Check Results ───────────────────────────────────────────────────

@dataclass
class HealthStatus:
    """Status of a single health check."""
    name: str
    is_healthy: bool
    message: str
    details: Optional[str] = None
    suggestion: Optional[str] = None


@dataclass
class HealthReport:
    """Complete health report for a project."""
    project_root: Path
    overall_status: str  # "healthy", "warning", "error"
    checks: List[HealthStatus]
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]

    def is_healthy(self) -> bool:
        return self.overall_status == "healthy"

    def has_errors(self) -> bool:
        return self.overall_status == "error"

    def has_warnings(self) -> bool:
        return self.overall_status in ("warning", "error")


# ── Dependency Checks ──────────────────────────────────────────────────────

def check_ripgrep_available() -> HealthStatus:
    """Check if ripgrep (rg) is available."""
    try:
        result = subprocess.run(
            ["rg", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            version = result.stdout.split("\n")[0]
            return HealthStatus(
                name="ripgrep",
                is_healthy=True,
                message=f"Ripgrep available: {version}",
            )
        else:
            return HealthStatus(
                name="ripgrep",
                is_healthy=False,
                message="Ripgrep command failed",
                suggestion="Install ripgrep: https://github.com/BurntSushi/ripgrep#installation",
            )
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        return HealthStatus(
            name="ripgrep",
            is_healthy=False,
            message="Ripgrep not found on PATH",
            suggestion="Install ripgrep: https://github.com/BurntSushi/ripgrep#installation",
        )


def check_ollama_available() -> HealthStatus:
    """Check if Ollama is running (optional dependency)."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return HealthStatus(
                name="ollama",
                is_healthy=True,
                message="Ollama is running",
            )
        else:
            return HealthStatus(
                name="ollama",
                is_healthy=False,
                message="Ollama command failed",
                suggestion="Start Ollama: 'ollama serve'",
            )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return HealthStatus(
            name="ollama",
            is_healthy=False,
            message="Ollama not found (optional)",
            suggestion="Embedding features disabled. Install Ollama for semantic analysis: https://ollama.ai",
        )


def check_disk_space(path: Path, min_mb: int = 100) -> HealthStatus:
    """Check if there's enough disk space."""
    try:
        stat = path.statvfs if hasattr(path, 'statvfs') else None
        if stat is None:
            # Windows fallback
            import ctypes
            free_bytes = ctypes.c_ulonglong(0)
            ctypes.windll.kernel32.GetDiskFreeSpaceExW(
                ctypes.c_wchar_p(str(path)),
                None,
                None,
                ctypes.pointer(free_bytes)
            )
            free_mb = free_bytes.value / (1024 * 1024)
        else:
            # Unix-like systems
            usage = stat()
            free_mb = (usage.f_bavail * usage.f_frsize) / (1024 * 1024)

        if free_mb >= min_mb:
            return HealthStatus(
                name="disk_space",
                is_healthy=True,
                message=f"Sufficient disk space: {free_mb:.1f} MB free",
            )
        else:
            return HealthStatus(
                name="disk_space",
                is_healthy=False,
                message=f"Low disk space: {free_mb:.1f} MB free",
                suggestion=f"Free up at least {min_mb} MB of disk space",
            )
    except Exception as e:
        return HealthStatus(
            name="disk_space",
            is_healthy=False,
            message=f"Could not check disk space: {e}",
            suggestion="Ensure sufficient disk space is available",
        )


# ── Project Structure Checks ───────────────────────────────────────────────

def check_project_initialized(project_root: Path) -> HealthStatus:
    """Check if .project-control directory exists and is initialized."""
    control_dir = project_root / ".project-control"

    if not control_dir.exists():
        return HealthStatus(
            name="project_initialized",
            is_healthy=False,
            message="PROJECT_CONTROL not initialized",
            suggestion="Run 'pc init' to initialize",
        )

    if not control_dir.is_dir():
        return HealthStatus(
            name="project_initialized",
            is_healthy=False,
            message=".project-control exists but is not a directory",
            suggestion="Remove .project-control and run 'pc init'",
        )

    # Check for required files
    patterns_file = control_dir / "patterns.yaml"
    if not patterns_file.exists():
        return HealthStatus(
            name="project_initialized",
            is_healthy=False,
            message=".project-control exists but missing patterns.yaml",
            suggestion="Run 'pc init' to reinitialize",
        )

    return HealthStatus(
        name="project_initialized",
        is_healthy=True,
        message="PROJECT_CONTROL initialized",
    )


def check_snapshot_exists(project_root: Path) -> HealthStatus:
    """Check if snapshot.json exists."""
    snapshot_path = project_root / ".project-control" / "snapshot.json"

    if not snapshot_path.exists():
        return HealthStatus(
            name="snapshot_exists",
            is_healthy=False,
            message="Snapshot not found",
            suggestion="Run 'pc scan' to create a snapshot",
        )

    return HealthStatus(
        name="snapshot_exists",
        is_healthy=True,
        message="Snapshot exists",
    )


def check_snapshot_valid(project_root: Path) -> HealthStatus:
    """Check if snapshot is valid (exists, valid JSON, correct structure)."""
    snapshot_path = project_root / ".project-control" / "snapshot.json"

    if not snapshot_path.exists():
        return HealthStatus(
            name="snapshot_valid",
            is_healthy=False,
            message="Snapshot not found",
            suggestion="Run 'pc scan' to create a snapshot",
        )

    try:
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        result = validate_snapshot(snapshot, snapshot_path)

        if not result.is_valid:
            return HealthStatus(
                name="snapshot_valid",
                is_healthy=False,
                message="Snapshot is invalid",
                details=f"Errors: {'; '.join(result.errors)}",
                suggestion="Run 'pc scan' to recreate the snapshot",
            )

        if result.has_warnings():
            return HealthStatus(
                name="snapshot_valid",
                is_healthy=True,
                message="Snapshot valid with warnings",
                details=f"Warnings: {'; '.join(result.warnings)}",
            )

        # Check freshness (warn if > 7 days old)
        if "meta" in snapshot and "createdAt" in snapshot.get("meta", {}):
            try:
                created = datetime.fromisoformat(snapshot["meta"]["createdAt"])
                age = (datetime.now(timezone.utc) - created).days
                if age > 7:
                    return HealthStatus(
                        name="snapshot_valid",
                        is_healthy=True,
                        message=f"Snapshot valid but stale ({age} days old)",
                        suggestion="Run 'pc scan' to update the snapshot",
                    )
            except (ValueError, KeyError):
                pass

        return HealthStatus(
            name="snapshot_valid",
            is_healthy=True,
            message="Snapshot is valid and fresh",
        )

    except json.JSONDecodeError as e:
        return HealthStatus(
            name="snapshot_valid",
            is_healthy=False,
            message="Snapshot contains invalid JSON",
            details=f"JSON error: {e}",
            suggestion="Run 'pc scan' to recreate the snapshot",
        )
    except Exception as e:
        return HealthStatus(
            name="snapshot_valid",
            is_healthy=False,
            message=f"Error reading snapshot: {e}",
            suggestion="Run 'pc scan' to recreate the snapshot",
        )


def check_graph_exists(project_root: Path) -> HealthStatus:
    """Check if graph.snapshot.json exists."""
    graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"

    if not graph_path.exists():
        return HealthStatus(
            name="graph_exists",
            is_healthy=False,
            message="Graph not found",
            suggestion="Run 'pc graph build' to build the dependency graph",
        )

    return HealthStatus(
        name="graph_exists",
        is_healthy=True,
            message="Graph exists",
        )


def check_graph_valid(project_root: Path) -> HealthStatus:
    """Check if graph is valid."""
    graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"

    if not graph_path.exists():
        return HealthStatus(
            name="graph_valid",
            is_healthy=False,
            message="Graph not found",
            suggestion="Run 'pc graph build' to build the dependency graph",
        )

    try:
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
        result = validate_graph(graph, graph_path)

        if not result.is_valid:
            return HealthStatus(
                name="graph_valid",
                is_healthy=False,
                message="Graph is invalid",
                details=f"Errors: {'; '.join(result.errors)}",
                suggestion="Run 'pc graph build' to rebuild the graph",
            )

        if result.has_warnings():
            return HealthStatus(
                name="graph_valid",
                is_healthy=True,
                message="Graph valid with warnings",
                details=f"Warnings: {'; '.join(result.warnings)}",
            )

        return HealthStatus(
            name="graph_valid",
            is_healthy=True,
            message="Graph is valid",
        )

    except json.JSONDecodeError as e:
        return HealthStatus(
            name="graph_valid",
            is_healthy=False,
            message="Graph contains invalid JSON",
            details=f"JSON error: {e}",
            suggestion="Run 'pc graph build' to rebuild the graph",
        )
    except Exception as e:
        return HealthStatus(
            name="graph_valid",
            is_healthy=False,
            message=f"Error reading graph: {e}",
            suggestion="Run 'pc graph build' to rebuild the graph",
        )


def check_config_valid(project_root: Path) -> HealthStatus:
    """Check if configuration files are valid."""
    control_dir = project_root / ".project-control"
    errors: List[str] = []

    # Check patterns.yaml
    patterns_file = control_dir / "patterns.yaml"
    if patterns_file.exists():
        try:
            import yaml
            config = yaml.safe_load(patterns_file.read_text(encoding="utf-8")) or {}
            result = validate_patterns_config(config)
            if not result.is_valid:
                errors.append(f"patterns.yaml: {'; '.join(result.errors)}")
        except Exception as e:
            errors.append(f"patterns.yaml: {e}")
    else:
        errors.append("patterns.yaml not found")

    # Check graph.config.yaml (optional)
    graph_config_file = control_dir / "graph.config.yaml"
    if graph_config_file.exists():
        try:
            import yaml
            config = yaml.safe_load(graph_config_file.read_text(encoding="utf-8")) or {}
            result = validate_graph_config(config)
            if not result.is_valid:
                errors.append(f"graph.config.yaml: {'; '.join(result.errors)}")
        except Exception as e:
            errors.append(f"graph.config.yaml: {e}")

    if errors:
        return HealthStatus(
            name="config_valid",
            is_healthy=False,
            message="Configuration issues found",
            details="; ".join(errors),
            suggestion="Check configuration files in .project-control/",
        )

    return HealthStatus(
        name="config_valid",
        is_healthy=True,
        message="Configuration is valid",
    )


# ── Pre-flight Checks ───────────────────────────────────────────────────────

def pre_flight_scan(project_root: Path) -> None:
    """Pre-flight checks before scanning."""
    # Check project is initialized
    status = check_project_initialized(project_root)
    if not status.is_healthy:
        raise FileNotFoundError(status.message, details=status.suggestion)

    # Check disk space
    status = check_disk_space(project_root, min_mb=50)
    if not status.is_healthy:
        raise ValidationError(status.message, details=status.suggestion)

    logger.info("Pre-flight checks passed for scan")


def pre_flight_ghost(project_root: Path) -> None:
    """Pre-flight checks before ghost analysis."""
    # Check snapshot exists
    status = check_snapshot_exists(project_root)
    if not status.is_healthy:
        raise FileNotFoundError(status.message, details=status.suggestion)

    # Check snapshot is valid
    status = check_snapshot_valid(project_root)
    if not status.is_healthy:
        raise ValidationError(status.message, details=status.suggestion)

    # Check ripgrep for orphan detection
    status = check_ripgrep_available()
    if not status.is_healthy:
        logger.warning(f"Ripgrep not available: {status.suggestion}")
        logger.warning("Orphan detection will be limited")

    logger.info("Pre-flight checks passed for ghost analysis")


def pre_flight_graph_build(project_root: Path) -> None:
    """Pre-flight checks before building graph."""
    # Check snapshot exists
    status = check_snapshot_exists(project_root)
    if not status.is_healthy:
        raise FileNotFoundError(status.message, details=status.suggestion)

    # Check snapshot is valid
    status = check_snapshot_valid(project_root)
    if not status.is_healthy:
        raise ValidationError(status.message, details=status.suggestion)

    # Check disk space
    status = check_disk_space(project_root, min_mb=50)
    if not status.is_healthy:
        raise ValidationError(status.message, details=status.suggestion)

    logger.info("Pre-flight checks passed for graph build")


def pre_flight_graph_operation(project_root: Path) -> None:
    """Pre-flight checks before graph operations (report, trace)."""
    # Check graph exists
    status = check_graph_exists(project_root)
    if not status.is_healthy:
        raise FileNotFoundError(status.message, details=status.suggestion)

    # Check graph is valid
    status = check_graph_valid(project_root)
    if not status.is_healthy:
        raise ValidationError(status.message, details=status.suggestion)

    logger.info("Pre-flight checks passed for graph operation")


# ── Complete Health Check ──────────────────────────────────────────────────

def health_check(project_root: Path) -> HealthReport:
    """
    Perform complete health check on project.

    Returns:
        HealthReport with all checks and suggestions
    """
    checks: List[HealthStatus] = []
    errors: List[str] = []
    warnings: List[str] = []
    suggestions: List[str] = []

    # Project structure
    checks.append(check_project_initialized(project_root))
    checks.append(check_snapshot_exists(project_root))
    checks.append(check_snapshot_valid(project_root))
    checks.append(check_graph_exists(project_root))
    checks.append(check_graph_valid(project_root))
    checks.append(check_config_valid(project_root))

    # Dependencies
    checks.append(check_ripgrep_available())
    checks.append(check_ollama_available())
    checks.append(check_disk_space(project_root))

    # Aggregate results
    has_errors = any(not check.is_healthy for check in checks)
    has_warnings = any(
        check.is_healthy and check.suggestion
        for check in checks
    )

    # Extract errors, warnings, and suggestions
    for check in checks:
        if not check.is_healthy:
            errors.append(f"{check.name}: {check.message}")
            if check.suggestion:
                suggestions.append(f"• {check.suggestion}")
        elif check.suggestion:
            warnings.append(f"{check.name}: {check.message}")
            suggestions.append(f"• {check.suggestion}")

    # Determine overall status
    if has_errors:
        overall_status = "error"
    elif has_warnings:
        overall_status = "warning"
    else:
        overall_status = "healthy"

    return HealthReport(
        project_root=project_root,
        overall_status=overall_status,
        checks=checks,
        errors=errors,
        warnings=warnings,
        suggestions=suggestions,
    )


# ── Convenient Functions ───────────────────────────────────────────────────

def require_healthy_snapshot(project_root: Path, operation: str = "operation") -> None:
    """
    Require a healthy snapshot, raising exception if not.

    Args:
        project_root: Project root path
        operation: Name of the operation (for error messages)

    Raises:
        FileNotFoundError: If snapshot doesn't exist
        ValidationError: If snapshot is invalid
    """
    pre_flight_ghost(project_root)


def require_healthy_graph(project_root: Path, operation: str = "operation") -> None:
    """
    Require a healthy graph, raising exception if not.

    Args:
        project_root: Project root path
        operation: Name of the operation (for error messages)

    Raises:
        FileNotFoundError: If graph doesn't exist
        ValidationError: If graph is invalid
    """
    pre_flight_graph_operation(project_root)


def ensure_initialized(project_root: Path) -> None:
    """
    Ensure project is initialized, raise exception if not.

    Args:
        project_root: Project root path

    Raises:
        FileNotFoundError: If .project-control doesn't exist
    """
    status = check_project_initialized(project_root)
    if not status.is_healthy:
        raise FileNotFoundError(status.message, details=status.suggestion)
