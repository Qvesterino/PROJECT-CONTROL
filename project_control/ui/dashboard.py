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

# Rich library for enhanced UI
try:
    from rich.console import Console
    from rich.table import Table as RichTable
    from rich.panel import Panel
    from rich.text import Text
    from rich.layout import Layout
    from rich.columns import Columns
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    from rich.style import Style
    from rich.align import Align
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

# Readchar library for keyboard input
try:
    from readchar import readkey, key
    READCHAR_AVAILABLE = True
except ImportError:
    READCHAR_AVAILABLE = False

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
    # Interactive state
    selected_tab: str = "overview"  # "overview", "metrics", "warnings", "actions"
    auto_refresh: bool = False
    refresh_interval: int = 30  # seconds


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
    """Renders dashboard to console using Rich library."""

    def __init__(self, width: int = 80, use_rich: bool = True):
        self.width = width
        self.use_rich = use_rich and RICH_AVAILABLE
        if self.use_rich:
            self.console = Console(width=width)

    def render(self, state: DashboardState) -> str:
        """Render dashboard to string."""
        if self.use_rich:
            return self._render_rich(state)
        else:
            return self._render_plain(state)

    def _get_status_indicator(self, age: Optional[timedelta], warning_days: int) -> str:
        """Get status indicator based on age.

        Args:
            age: Age of the data
            warning_days: Days after which to show warning

        Returns:
            Rich-formatted status string
        """
        if age is None:
            return "[red]?[/red]"
        elif age.days == 0:
            return "[green]✓[/green]"
        elif age.days <= warning_days:
            return "[yellow]~[/yellow]"
        else:
            return "[red]✗[/red]"

    def _format_age(self, age: Optional[timedelta]) -> str:
        """Format age as human-readable string.

        Args:
            age: Age to format

        Returns:
            Formatted age string
        """
        if age is None:
            return "unknown"
        elif age.days == 0:
            return "today"
        elif age.days == 1:
            return "yesterday"
        elif age.days < 7:
            return f"{age.days} days ago"
        else:
            return f"{age.days} days ago [red](old)[/red]"

    def _render_rich(self, state: DashboardState) -> str:
        """Render dashboard using Rich library."""
        # Create main layout
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=7),
            Layout(name="content"),
            Layout(name="footer", size=3),
        )

        # Header
        layout["header"].update(self._render_header_rich(state))

        # Content based on selected tab
        if state.selected_tab == "overview":
            layout["content"].update(self._render_content_overview_rich(state))
        elif state.selected_tab == "metrics":
            layout["content"].update(self._render_content_metrics_rich(state))
        elif state.selected_tab == "warnings":
            layout["content"].update(self._render_content_warnings_rich(state))
        elif state.selected_tab == "actions":
            layout["content"].update(self._render_content_actions_rich(state))
        else:
            layout["content"].update(self._render_content_overview_rich(state))

        # Footer
        layout["footer"].update(self._render_footer_rich(state))

        # Capture output
        from io import StringIO
        buffer = StringIO()
        console = Console(file=buffer, width=self.width)
        console.print(layout)
        return buffer.getvalue()

    def _render_header_rich(self, state: DashboardState) -> Panel:
        """Render dashboard header using Rich."""
        # Status color
        status_colors = {
            "healthy": "green",
            "warning": "yellow",
            "error": "red"
        }
        status_color = status_colors.get(state.health_status, "white")

        # Status icon
        status_icons = {
            "healthy": "✓",
            "warning": "⚠",
            "error": "✗"
        }
        status_icon = status_icons.get(state.health_status, "?")

        # Create header text
        header_text = Text()
        header_text.append("PROJECT CONTROL DASHBOARD", style="bold blue")
        header_text.append("\n\n")
        header_text.append(f"Project: ", style="dim")
        header_text.append(state.project_name, style="bold cyan")
        header_text.append("  |  ", style="dim")
        header_text.append(f"Mode: ", style="dim")
        header_text.append(state.mode.upper(), style="bold magenta")
        header_text.append("  |  ", style="dim")
        header_text.append(f"Status: ", style="dim")
        header_text.append(f"{status_icon} {state.health_status.upper()}", style=f"bold {status_color}")

        # Path on next line
        header_text.append(f"\nPath: {state.project_path}", style="dim")

        return Panel(
            header_text,
            style=f"bold {status_color}",
            padding=(1, 2),
            box=box.SQUARE
        )

    def _render_content_overview_rich(self, state: DashboardState) -> Panel:
        """Render overview content using Rich."""
        # Create two columns: snapshot/graph status and quick metrics
        left_panel = self._render_status_panel_rich(state)
        right_panel = self._render_quick_metrics_panel_rich(state.metrics)

        # Combine columns
        columns = Columns([left_panel, right_panel], equal=True)

        return Panel(
            columns,
            title="[bold cyan]Project Overview[/bold cyan]",
            border_style="cyan",
            box=box.SQUARE
        )

    def _render_status_panel_rich(self, state: DashboardState) -> Panel:
        """Render status panel using Rich."""
        lines = []

        # Snapshot status
        snapshot_status = self._get_status_indicator(state.snapshot_age, 7)
        if state.last_scan:
            age_str = self._format_age(state.snapshot_age)
            lines.append(f"Snapshot: {snapshot_status} {state.metrics.total_files} files ({age_str})")
        else:
            lines.append("Snapshot: [red]MISSING[/red]")

        # Graph status
        graph_status = self._get_status_indicator(state.graph_age, 3)
        if state.last_build:
            age_str = self._format_age(state.graph_age)
            lines.append(f"Graph:    {graph_status} {state.metrics.total_nodes} nodes, {state.metrics.total_edges} edges ({age_str})")
        else:
            lines.append("Graph:    [red]MISSING[/red]")

        # Config status
        control_dir = state.project_path / ".project-control"
        patterns_file = control_dir / "patterns.yaml"
        if patterns_file.exists():
            lines.append("Config:   [green]✓ Valid[/green]")
        else:
            lines.append("Config:   [red]✗ Missing[/red]")

        # Warnings summary
        error_count = sum(1 for w in state.warnings if w.level == "error")
        warning_count = sum(1 for w in state.warnings if w.level == "warning")

        lines.append("")
        if error_count > 0:
            lines.append(f"Errors:   [red]{error_count}[/red]")
        if warning_count > 0:
            lines.append(f"Warnings: [yellow]{warning_count}[/yellow]")
        if error_count == 0 and warning_count == 0:
            lines.append("Issues:   [green]None[/green]")

        status_text = "\n".join(lines)
        return Panel(
            Text.from_markup(status_text),
            title="[bold]Status[/bold]",
            border_style="blue",
            box=box.SQUARE
        )

    def _render_quick_metrics_panel_rich(self, metrics: DashboardMetrics) -> Panel:
        """Render quick metrics panel using Rich."""
        # Create a compact table
        table = RichTable(show_header=False, box=None)
        table.add_column("Metric", style="dim")
        table.add_column("Value", justify="right")

        table.add_row("Total Files", str(metrics.total_files))
        table.add_row("Total Nodes", str(metrics.total_nodes))
        table.add_row("Total Edges", str(metrics.total_edges))

        if metrics.orphans > 0:
            table.add_row("Orphans", f"[red]{metrics.orphans}[/red]")
        else:
            table.add_row("Orphans", str(metrics.orphans))

        if metrics.cycles > 0:
            table.add_row("Cycles", f"[red]{metrics.cycles}[/red]")
        else:
            table.add_row("Cycles", str(metrics.cycles))

        table.add_row("Dependents", str(metrics.dependents))
        table.add_row("Entrypoints", str(metrics.entrypoints))

        return Panel(
            table,
            title="[bold]Quick Metrics[/bold]",
            border_style="green",
            box=box.SQUARE
        )

    def _render_content_metrics_rich(self, state: DashboardState) -> Panel:
        """Render detailed metrics using Rich."""
        m = state.metrics

        # Create main metrics table
        table = RichTable(title="Project Metrics", box=box.SQUARE)
        table.add_column("Metric", style="cyan", width=20)
        table.add_column("Value", justify="right", style="bold")
        table.add_column("Notes", style="dim")

        # File metrics
        table.add_row("Total Files", str(m.total_files), "All files in snapshot")
        table.add_row("Total Nodes", str(m.total_nodes), "Files in dependency graph")
        table.add_row("Total Edges", str(m.total_edges), "Import dependencies")

        # Problem metrics with styling
        if m.orphans > 0:
            table.add_row("Orphans", f"[red]{m.orphans}[/red]", "Files with no references")
        else:
            table.add_row("Orphans", f"[green]{m.orphans}[/green]", "All files referenced")

        if m.cycles > 0:
            table.add_row("Cycles", f"[red]{m.cycles}[/red]", "Circular dependencies")
        else:
            table.add_row("Cycles", f"[green]{m.cycles}[/green]", "No circular dependencies")

        table.add_row("Dependents", str(m.dependents), "Files that are imported")
        table.add_row("Entrypoints", str(m.entrypoints), "Root files (no imports)")

        # Advanced metrics
        table.add_section()
        table.add_row("Max Fan-In", str(m.max_fan_in), "Highest incoming dependencies")
        table.add_row("Max Fan-Out", str(m.max_fan_out), "Highest outgoing dependencies")

        return Panel(
            table,
            title="[bold magenta]Detailed Metrics[/bold magenta]",
            border_style="magenta",
            box=box.SQUARE
        )

    def _render_content_warnings_rich(self, state: DashboardState) -> Panel:
        """Render warnings using Rich."""
        if not state.warnings:
            return Panel(
                Text("[green]✓ No warnings or errors detected![/green]\n\n[dim]Project is in good shape.[/dim]", justify="center"),
                title="[bold green]All Clear[/bold green]",
                border_style="green"
            )

        # Group warnings by level
        errors = [w for w in state.warnings if w.level == "error"]
        warnings = [w for w in state.warnings if w.level == "warning"]
        infos = [w for w in state.warnings if w.level == "info"]

        content = Text()

        if errors:
            content.append("\n[bold red]ERRORS[/bold red]\n", style="bold")
            for w in errors:
                content.append(f"{w.icon} {w.message}\n", style="red")
                if w.suggestion:
                    content.append(f"   → {w.suggestion}\n", style="dim")
                if w.action_required:
                    content.append("   [bold red]Action required![/bold red]\n")
                content.append("\n")

        if warnings:
            content.append("[bold yellow]WARNINGS[/bold yellow]\n", style="bold")
            for w in warnings:
                content.append(f"{w.icon} {w.message}\n", style="yellow")
                if w.suggestion:
                    content.append(f"   → {w.suggestion}\n", style="dim")
                content.append("\n")

        if infos and not errors and not warnings:
            for w in infos:
                content.append(f"{w.icon} {w.message}\n", style="cyan")
                if w.suggestion:
                    content.append(f"   → {w.suggestion}\n", style="dim")

        return Panel(
            content,
            title=f"[bold yellow]Warnings ({len(state.warnings)})[/bold yellow]",
            border_style="yellow",
            box=box.SQUARE
        )

    def _render_content_actions_rich(self, state: DashboardState) -> Panel:
        """Render quick actions using Rich."""
        actions_table = RichTable(show_header=True, box=box.SQUARE)
        actions_table.add_column("Key", style="bold cyan", width=5)
        actions_table.add_column("Action", style="white")
        actions_table.add_column("Description", style="dim")

        actions = [
            ("1", "Scan project", "Update snapshot with current files"),
            ("2", "Run ghost analysis", "Find orphans, legacy code, duplicates"),
            ("3", "Build/rebuild graph", "Create or update dependency graph"),
            ("4", "View health report", "Check project health status"),
            ("5", "View orphans", "List all orphan files"),
            ("6", "View cycles", "List circular dependencies"),
            ("7", "View graph report", "Full graph analysis report"),
            ("8", "Trace dependencies", "Trace imports for a file"),
            ("0", "Return to menu", "Exit dashboard"),
        ]

        for key, action, desc in actions:
            actions_table.add_row(key, action, desc)

        return Panel(
            actions_table,
            title="[bold green]Quick Actions[/bold green]",
            border_style="green",
            box=box.SQUARE
        )

    def _render_footer_rich(self, state: DashboardState) -> Panel:
        """Render footer with tabs using Rich."""
        tabs = [
            ("overview", "Overview"),
            ("metrics", "Metrics"),
            ("warnings", "Warnings"),
            ("actions", "Actions"),
        ]

        tab_text = Text()
        for i, (tab_id, tab_name) in enumerate(tabs):
            if i > 0:
                tab_text.append(" | ", style="dim")

            if tab_id == state.selected_tab:
                tab_text.append(f"[{i+1}] {tab_name}", style="bold cyan")
            else:
                tab_text.append(f"[{i+1}] {tab_name}", style="dim")

        # Add quit hint
        tab_text.append("     [q]uit", style="dim")

        return Panel(
            Align.center(tab_text),
            style="dim",
            box=box.SQUARE,
            padding=(0, 1)
        )

    def _render_plain_header(self, state: DashboardState) -> List[str]:
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

    def _render_plain_overview(self, state: DashboardState) -> List[str]:
        """Render project overview section."""
        lines = []
        lines.append("─" * self.width)
        lines.append("📊 PROJECT OVERVIEW")
        lines.append("─" * self.width)
        lines.append("")

        # Snapshot status
        if state.snapshot_age is not None:
            snapshot_status = "[OK]"
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
            lines.append("Snapshot: [MISSING]")

        # Graph status
        if state.graph_age is not None:
            graph_status = "[OK]"
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

    def _render_plain_warnings(self, warnings: List[DashboardWarning]) -> List[str]:
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

    def _render_plain_metrics(self, metrics: DashboardMetrics) -> List[str]:
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

    def _render_plain_quick_actions(self) -> List[str]:
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

    def _render_plain(self, state: DashboardState) -> str:
        """Render dashboard to string (plain text fallback)."""
        lines = []

        # Header
        lines.extend(self._render_plain_header(state))

        # Project Overview
        lines.extend(self._render_plain_overview(state))

        # Warnings
        lines.extend(self._render_plain_warnings(state.warnings))

        # Metrics
        lines.extend(self._render_plain_metrics(state.metrics))

        # Quick Actions
        lines.extend(self._render_plain_quick_actions())

        # Footer
        lines.append("")
        lines.append("=" * self.width)

        return "\n".join(lines)


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


def render_dashboard(state: DashboardState, width: int = 80, use_rich: bool = True) -> str:
    """
    Render dashboard to string.

    Args:
        state: Dashboard state
        width: Dashboard width in characters
        use_rich: Use Rich library for enhanced UI (default: True)

    Returns:
        Formatted dashboard string
    """
    renderer = DashboardRenderer(width, use_rich=use_rich)
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


# ── Interactive Dashboard with Keyboard Navigation ───────────────────────────

if RICH_AVAILABLE and READCHAR_AVAILABLE:
    class InteractiveDashboard:
        """Fully interactive dashboard with keyboard navigation."""

        def __init__(self, project_root: Path, mode: str = "js_ts", width: int = 80):
            """Initialize interactive dashboard.

            Args:
                project_root: Root path of the project
                mode: Project mode (js_ts, python, mixed)
                width: Dashboard width in characters
            """
            self.project_root = project_root
            self.mode = mode
            self.width = width

            # Create initial state
            self.state = create_dashboard(project_root, mode)

            # Interactive state
            self.running = True

            # Available tabs
            self.tabs = ["overview", "metrics", "warnings", "actions"]
            self.tab_names = {
                "overview": "Overview",
                "metrics": "Metrics",
                "warnings": "Warnings",
                "actions": "Actions",
            }

        def run(self) -> None:
            """Run the interactive dashboard loop."""
            self._render()
            while self.running:
                try:
                    ch = readkey()
                    self._handle_input(ch)
                    if self.running:
                        self._render()
                except KeyboardInterrupt:
                    self.running = False
                    print("\nExiting...")
                except EOFError:
                    self.running = False

        def _handle_input(self, key_char: str) -> None:
            """Handle keyboard input.

            Args:
                key_char: The character read from stdin
            """
            # Tab navigation
            if key_char == '1':
                self.state.selected_tab = "overview"
            elif key_char == '2':
                self.state.selected_tab = "metrics"
            elif key_char == '3':
                self.state.selected_tab = "warnings"
            elif key_char == '4':
                self.state.selected_tab = "actions"
            # Arrow keys for tab navigation
            elif key_char == key.RIGHT:
                current_index = self.tabs.index(self.state.selected_tab)
                next_index = (current_index + 1) % len(self.tabs)
                self.state.selected_tab = self.tabs[next_index]
            elif key_char == key.LEFT:
                current_index = self.tabs.index(self.state.selected_tab)
                prev_index = (current_index - 1) % len(self.tabs)
                self.state.selected_tab = self.tabs[prev_index]
            # Refresh
            elif key_char == 'r':
                self._refresh()
            # Help
            elif key_char == 'h':
                self._show_help()
            # Quit
            elif key_char in ('q', key.ESC):
                self.running = False

        def _refresh(self) -> None:
            """Refresh dashboard data."""
            self.state = create_dashboard(self.project_root, self.mode)

        def _show_help(self) -> None:
            """Show help screen."""
            console = Console()
            console.clear()

            help_text = Text()
            help_text.append("\n[bold cyan]Keyboard Shortcuts[/bold cyan]\n\n")
            help_text.append("[bold]Tab Navigation:[/bold]\n", style="yellow")
            help_text.append("  [1-4]       - Switch to tab (1=Overview, 2=Metrics, 3=Warnings, 4=Actions)\n")
            help_text.append("  ←/→         - Navigate between tabs\n\n")
            help_text.append("[bold]Actions:[/bold]\n", style="yellow")
            help_text.append("  [r]         - Refresh dashboard data\n")
            help_text.append("  [h]         - Show this help\n")
            help_text.append("  [q] or ESC  - Quit\n")

            help_panel = Panel(
                help_text,
                title="[bold cyan]Help[/bold cyan]",
                border_style="cyan",
                padding=(1, 2)
            )
            console.print(help_panel)
            console.print("\n[dim]Press any key to continue...[/dim]")

            readkey()

        def _render(self) -> None:
            """Render the dashboard UI."""
            console = Console(width=self.width)
            console.clear()

            dashboard_str = render_dashboard(self.state, width=self.width, use_rich=True)
            console.print(dashboard_str)


def run_interactive_dashboard(project_root: Path, mode: str = "js_ts", width: int = 80) -> None:
    """
    Run interactive dashboard with keyboard navigation.

    Args:
        project_root: Root path of the project
        mode: Project mode (js_ts, python, mixed)
        width: Dashboard width in characters

    Raises:
        ImportError: If rich or readchar libraries are not available
    """
    if not RICH_AVAILABLE or not READCHAR_AVAILABLE:
        raise ImportError(
            "Interactive dashboard requires 'rich' and 'readchar' packages. "
            "Install them with: pip install rich readchar"
        )

    dashboard = InteractiveDashboard(project_root, mode, width)
    dashboard.run()

