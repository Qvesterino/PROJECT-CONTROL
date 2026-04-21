"""Dashboard for PROJECT_CONTROL - project overview and quick actions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from project_control.core.pre_flight import health_check, HealthReport, HealthStatus
from project_control.core.validator import validate_snapshot, validate_graph
from project_control.core.error_handler import Validator

logger = logging.getLogger(__name__)


# ── Dashboard Data Models ──────────────────────────────────────────────────

@dataclass
class DashboardWarning:
    """Warning message for dashboard."""
    level: str  # "info", "warning", "error"
    icon: str
    message: str
    suggestion: Optional[str] = None
    action_required: bool = False


@dataclass
class DashboardMetrics:
    """Key project metrics."""
    total_files: int = 0
    total_nodes: int = 0
    total_edges: int = 0
    orphans: int = 0
    cycles: int = 0
    dependents: int = 0
    entrypoints: int = 0
    max_fan_in: int = 0
    max_fan_out: int = 0


@dataclass
class DashboardState:
    """Complete dashboard state."""
    project_name: str
    project_path: Path
    mode: str
    metrics: DashboardMetrics
    warnings: List[DashboardWarning]
    health_status: str  # "healthy", "warning", "error"
    last_scan: Optional[datetime] = None
    last_build: Optional[datetime] = None
    snapshot_age: Optional[timedelta] = None
    graph_age: Optional[timedelta] = None


# ── Dashboard Builder ──────────────────────────────────────────────────────

class DashboardBuilder:
    """Builds dashboard state from project data."""

    def __init__(self, project_root: Path, mode: str = "js_ts"):
        self.project_root = project_root
        self.mode = mode
        self.snapshot_path = project_root / ".project-control" / "snapshot.json"
        self.graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"
        self.metrics_path = project_root / ".project-control" / "out" / "graph.metrics.json"

    def build(self) -> DashboardState:
        """Build complete dashboard state."""
        # Run health check
        health_report = health_check(self.project_root)

        # Load metrics
        metrics = self._load_metrics()

        # Collect warnings
        warnings = self._collect_warnings(health_report, metrics)

        # Determine overall status
        health_status = self._determine_health_status(warnings, health_report)

        # Calculate ages
        last_scan, last_build, snapshot_age, graph_age = self._calculate_ages()

        return DashboardState(
            project_name=self.project_root.name,
            project_path=self.project_root,
            mode=self.mode,
            metrics=metrics,
            warnings=warnings,
            health_status=health_status,
            last_scan=last_scan,
            last_build=last_build,
            snapshot_age=snapshot_age,
            graph_age=graph_age,
        )

    def _load_metrics(self) -> DashboardMetrics:
        """Load graph metrics if available."""
        metrics = DashboardMetrics()

        # Load snapshot file count
        if self.snapshot_path.exists():
            try:
                snapshot = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
                metrics.total_files = snapshot.get("file_count", 0)
            except Exception:
                pass

        # Load graph metrics
        if self.metrics_path.exists():
            try:
                graph_metrics = json.loads(self.metrics_path.read_text(encoding="utf-8"))
                totals = graph_metrics.get("totals", {})
                metrics.total_nodes = totals.get("nodeCount", 0)
                metrics.total_edges = totals.get("edgeCount", 0)
                metrics.cycles = len(graph_metrics.get("cycles", []))
                metrics.orphans = len(graph_metrics.get("orphanCandidates", []))
                metrics.max_fan_in = totals.get("maxFanIn", 0)
                metrics.max_fan_out = totals.get("maxFanOut", 0)

                # Calculate dependents and entrypoints
                if "graph.snapshot.json" in str(self.graph_path):
                    graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
                    metrics.entrypoints = len(graph.get("entrypoints", []))

                    # Count nodes with fan-in > 0
                    indegree = {node_id: 0 for node_id in range(1, metrics.total_nodes + 1)}
                    for edge in graph.get("edges", []):
                        to_id = edge.get("toId")
                        if to_id:
                            indegree[to_id] = indegree.get(to_id, 0) + 1
                    metrics.dependents = sum(1 for deg in indegree.values() if deg > 0)

            except Exception as e:
                logger.debug(f"Failed to load metrics: {e}")

        return metrics

    def _collect_warnings(self, health_report: HealthReport, metrics: DashboardMetrics) -> List[DashboardWarning]:
        """Collect all warnings from various sources."""
        warnings: List[DashboardWarning] = []

        # From health check
        for check in health_report.checks:
            if not check.is_healthy:
                warnings.append(DashboardWarning(
                    level="error",
                    icon="[FAIL]",
                    message=f"{check.name}: {check.message}",
                    suggestion=check.suggestion,
                    action_required=True,
                ))

        # Orphans warning
        if metrics.orphans > 0:
            warnings.append(DashboardWarning(
                level="warning",
                icon="[WARN]",
                message=f"{metrics.orphans} orphan file(s) detected",
                suggestion="Run 'Analyze -> Ghost' for details",
                action_required=False,
            ))

        # Cycles warning
        if metrics.cycles > 0:
            warnings.append(DashboardWarning(
                level="warning",
                icon="[WARN]",
                message=f"{metrics.cycles} circular dependenc(y/ies) detected",
                suggestion="Review cycle impact in graph report",
                action_required=False,
            ))

        # Snapshot age warning
        if self.snapshot_path.exists():
            try:
                snapshot = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
                if "generated_at" in snapshot:
                    created = datetime.fromisoformat(snapshot["generated_at"])
                    age = datetime.now(timezone.utc) - created
                    if age > timedelta(days=7):
                        warnings.append(DashboardWarning(
                            level="warning",
                            icon="[WARN]",
                            message=f"Snapshot is {age.days} days old",
                            suggestion="Run 'pc scan' to update",
                            action_required=False,
                        ))
            except Exception:
                pass

        # Graph age warning
        if self.graph_path.exists():
            try:
                graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
                meta = graph.get("meta", {})
                if "createdAt" in meta:
                    created = datetime.fromisoformat(meta["createdAt"])
                    age = datetime.now(timezone.utc) - created
                    if age > timedelta(days=3):
                        warnings.append(DashboardWarning(
                            level="info",
                            icon="[INFO]",
                            message=f"Graph is {age.days} day(s) old",
                            suggestion="Run 'Graph -> Build' to rebuild",
                            action_required=False,
                        ))
            except Exception:
                pass

        # No warnings info
        if len(warnings) == 0 and metrics.orphans == 0 and metrics.cycles == 0:
            warnings.append(DashboardWarning(
                level="info",
                icon="[OK]",
                message="No issues detected",
                suggestion="Project is in good shape!",
                action_required=False,
            ))

        return warnings

    def _determine_health_status(self, warnings: List[DashboardWarning], health_report: HealthReport) -> str:
        """Determine overall health status."""
        if health_report.overall_status == "error":
            return "error"
        elif health_report.overall_status == "warning":
            return "warning"
        elif any(w.level == "error" for w in warnings):
            return "error"
        elif any(w.level == "warning" for w in warnings):
            return "warning"
        else:
            return "healthy"

    def _calculate_ages(self) -> tuple[Optional[datetime], Optional[datetime], Optional[timedelta], Optional[timedelta]]:
        """Calculate last scan/build times and ages."""
        last_scan = None
        last_build = None
        snapshot_age = None
        graph_age = None

        # Snapshot age
        if self.snapshot_path.exists():
            try:
                snapshot = json.loads(self.snapshot_path.read_text(encoding="utf-8"))
                if "generated_at" in snapshot:
                    last_scan = datetime.fromisoformat(snapshot["generated_at"])
                    snapshot_age = datetime.now(timezone.utc) - last_scan
            except Exception:
                pass

        # Graph age
        if self.graph_path.exists():
            try:
                graph = json.loads(self.graph_path.read_text(encoding="utf-8"))
                meta = graph.get("meta", {})
                if "createdAt" in meta:
                    last_build = datetime.fromisoformat(meta["createdAt"])
                    graph_age = datetime.now(timezone.utc) - last_build
            except Exception:
                pass

        return last_scan, last_build, snapshot_age, graph_age


# ── Dashboard Renderer ─────────────────────────────────────────────────────

class DashboardRenderer:
    """Renders dashboard to console."""

    def __init__(self, width: int = 60):
        self.width = width

    def render(self, state: DashboardState) -> str:
        """Render dashboard to string."""
        lines = []

        # Header
        lines.extend(self._render_header(state))

        # Project Overview
        lines.extend(self._render_overview(state))

        # Warnings
        lines.extend(self._render_warnings(state.warnings))

        # Metrics
        lines.extend(self._render_metrics(state.metrics))

        # Quick Actions
        lines.extend(self._render_quick_actions())

        # Footer
        lines.append("")
        lines.append("=" * self.width)

        return "\n".join(lines)

    def _render_header(self, state: DashboardState) -> List[str]:
        """Render dashboard header."""
        lines = []

        # Status indicator
        if state.health_status == "healthy":
            status = "[OK]"
        elif state.health_status == "warning":
            status = "[WARN]"
        else:
            status = "[ERROR]"

        lines.append("=" * self.width)
        lines.append("  PROJECT CONTROL DASHBOARD")
        lines.append("=" * self.width)
        lines.append("")
        lines.append(f"Project:  {state.project_name}")
        lines.append(f"Mode:     {state.mode.upper()}")
        lines.append(f"Path:     {state.project_path}")
        lines.append(f"Status:   {status} {state.health_status.upper()}")
        lines.append("")

        return lines

    def _render_overview(self, state: DashboardState) -> List[str]:
        """Render project overview section."""
        lines = []
        lines.append("─" * self.width)
        lines.append("📊 PROJECT OVERVIEW")
        lines.append("─" * self.width)
        lines.append("")

        # Snapshot status
        if state.snapshot_path is not None and state.snapshot_path.exists():
            snapshot_status = "[OK]"
            if state.snapshot_age:
                days = state.snapshot_age.days
                if days == 0:
                    age_str = "today"
                elif days == 1:
                    age_str = "yesterday"
                else:
                    age_str = f"{days} days ago"
                if days > 7:
                    snapshot_status = "[WARN]"
                lines.append(f"Snapshot: {snapshot_status} {state.metrics.total_files} files ({age_str})")
            else:
                lines.append(f"Snapshot: {snapshot_status} {state.metrics.total_files} files")
        else:
            lines.append("Snapshot: [MISSING]")

        # Graph status
        if state.graph_path is not None and state.graph_path.exists():
            graph_status = "[OK]"
            if state.graph_age:
                days = state.graph_age.days
                if days == 0:
                    age_str = "today"
                elif days == 1:
                    age_str = "yesterday"
                else:
                    age_str = f"{days} days ago"
                if days > 3:
                    graph_status = "[WARN]"
                lines.append(f"Graph:    {graph_status} {state.metrics.total_nodes} nodes, {state.metrics.total_edges} edges ({age_str})")
            else:
                lines.append(f"Graph:    {graph_status} {state.metrics.total_nodes} nodes, {state.metrics.total_edges} edges")
        else:
            lines.append("Graph:    [MISSING]")

        # Config status
        control_dir = state.project_path / ".project-control"
        patterns_file = control_dir / "patterns.yaml"
        if patterns_file.exists():
            lines.append("Config:   [OK] Valid")
        else:
            lines.append("Config:   [MISSING]")

        lines.append("")
        return lines

    def _render_warnings(self, warnings: List[DashboardWarning]) -> List[str]:
        """Render warnings section."""
        lines = []

        # Filter out info warnings if there are more serious ones
        has_warnings = any(w.level in ("error", "warning") for w in warnings)
        if not has_warnings:
            return []

        lines.append("─" * self.width)
        lines.append("⚠️  WARNINGS")
        lines.append("─" * self.width)
        lines.append("")

        for warning in warnings:
            if warning.level == "info" and has_warnings:
                continue

            lines.append(f"{warning.icon} {warning.message}")
            if warning.suggestion:
                lines.append(f"   → {warning.suggestion}")

        lines.append("")
        return lines

    def _render_metrics(self, metrics: DashboardMetrics) -> List[str]:
        """Render metrics section."""
        lines = []

        lines.append("─" * self.width)
        lines.append("📈 METRICS")
        lines.append("─" * self.width)
        lines.append("")

        lines.append(f"Total Files:    {metrics.total_files}")
        lines.append(f"Total Nodes:    {metrics.total_nodes}")
        lines.append(f"Total Edges:    {metrics.total_edges}")

        # Orphans with warning
        if metrics.orphans > 0:
            lines.append(f"Orphans:        {metrics.orphans} [WARN]")
        else:
            lines.append(f"Orphans:        {metrics.orphans}")

        # Cycles with warning
        if metrics.cycles > 0:
            lines.append(f"Cycles:         {metrics.cycles} [WARN]")
        else:
            lines.append(f"Cycles:         {metrics.cycles}")

        lines.append(f"Dependents:     {metrics.dependents}")
        lines.append(f"Entrypoints:    {metrics.entrypoints}")

        if metrics.max_fan_in > 0 or metrics.max_fan_out > 0:
            lines.append("")
            lines.append(f"Max Fan-In:     {metrics.max_fan_in}")
            lines.append(f"Max Fan-Out:    {metrics.max_fan_out}")

        lines.append("")
        return lines

    def _render_quick_actions(self) -> List[str]:
        """Render quick actions section."""
        lines = []

        lines.append("─" * self.width)
        lines.append("⚡ QUICK ACTIONS")
        lines.append("─" * self.width)
        lines.append("")

        lines.append("[1] Scan project          [2] Run ghost analysis")
        lines.append("[3] Build/rebuild graph   [4] View health report")
        lines.append("[5] View orphans          [6] View cycles")
        lines.append("[7] View graph report     [8] Trace dependencies")
        lines.append("[0] Return to main menu")

        lines.append("")

        return lines


# ── Convenience Functions ─────────────────────────────────────────────────

def create_dashboard(project_root: Path, mode: str = "js_ts") -> DashboardState:
    """
    Create dashboard state.

    Args:
        project_root: Project root path
        mode: Project mode (js_ts, python, mixed)

    Returns:
        DashboardState with all project information
    """
    builder = DashboardBuilder(project_root, mode)
    return builder.build()


def render_dashboard(state: DashboardState, width: int = 60) -> str:
    """
    Render dashboard to string.

    Args:
        state: Dashboard state
        width: Dashboard width in characters

    Returns:
        Formatted dashboard string
    """
    renderer = DashboardRenderer(width)
    return renderer.render(state)


def show_dashboard(project_root: Path, mode: str = "js_ts") -> None:
    """
    Show dashboard to console.

    Args:
        project_root: Project root path
        mode: Project mode (js_ts, python, mixed)
    """
    state = create_dashboard(project_root, mode)
    dashboard_str = render_dashboard(state)
    print(dashboard_str)
