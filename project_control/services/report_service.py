"""Report viewing service for PROJECT_CONTROL.

Provides centralized access to all project reports.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from project_control.core.error_handler import FileNotFoundError, OperationError
from project_control.utils.terminal import print_error, print_success, print_warning


# ── Report Paths ─────────────────────────────────────────────────────

def get_exports_dir(project_root: Path) -> Path:
    """Get the exports directory path."""
    return project_root / ".project-control" / "exports"


def get_out_dir(project_root: Path) -> Path:
    """Get the output directory path."""
    return project_root / ".project-control" / "out"


def get_ghost_report_path(project_root: Path) -> Path:
    """Get ghost report path."""
    return get_exports_dir(project_root) / "ghost_candidates.md"


def get_checklist_path(project_root: Path) -> Path:
    """Get checklist report path."""
    return get_exports_dir(project_root) / "checklist.md"


def get_writers_report_path(project_root: Path) -> Path:
    """Get writers report path."""
    return get_exports_dir(project_root) / "writers_report.md"


def get_graph_report_path(project_root: Path) -> Path:
    """Get graph report path."""
    return get_out_dir(project_root) / "graph.report.md"


def get_graph_metrics_path(project_root: Path) -> Path:
    """Get graph metrics path."""
    return get_out_dir(project_root) / "graph.metrics.json"


# ── Report Viewing Functions ───────────────────────────────────────────

def view_ghost_report(project_root: Path) -> None:
    """
    View the ghost report.

    Args:
        project_root: Project root directory
    """
    report_path = get_ghost_report_path(project_root)

    if not report_path.exists():
        print_warning("Ghost report not found. Run 'Analyze → Ghost' first.")
        return

    try:
        content = report_path.read_text(encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"  GHOST REPORT")
        print(f"{'='*60}")
        print(f"\nFile: {report_path}")
        print(f"Size: {len(content)} characters")
        print(f"{'='*60}\n")
        print(content)
    except Exception as e:
        print_error(f"Failed to read ghost report: {e}")


def view_graph_report(project_root: Path, show_content: bool = False) -> None:
    """
    View the graph report with summary.

    Args:
        project_root: Project root directory
        show_content: Whether to show full report content
    """
    report_path = get_graph_report_path(project_root)
    metrics_path = get_graph_metrics_path(project_root)

    if not report_path.exists():
        print_warning("Graph report not found. Run 'Graph → Build' first.")
        return

    try:
        # Load metrics for summary
        metrics = {}
        if metrics_path.exists():
            try:
                metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                pass

        totals = metrics.get("totals", {})

        print(f"\n{'='*60}")
        print(f"  GRAPH REPORT")
        print(f"{'='*60}")
        print(f"\nSummary:")
        print(f"  Nodes:   {totals.get('nodeCount', '?')}")
        print(f"  Edges:   {totals.get('edgeCount', '?')}")
        print(f"  Cycles:  {len(metrics.get('cycles', []))}")
        print(f"  Orphans: {len(metrics.get('orphanCandidates', []))}")
        print(f"\nFile: {report_path}")

        if show_content:
            content = report_path.read_text(encoding="utf-8")
            print(f"\n{'='*60}")
            print(f"FULL REPORT CONTENT")
            print(f"{'='*60}\n")
            print(content)
        else:
            print(f"\nUse 'View Full Report' to see complete content.")

    except Exception as e:
        print_error(f"Failed to read graph report: {e}")


def view_checklist(project_root: Path) -> None:
    """
    View the project checklist.

    Args:
        project_root: Project root directory
    """
    checklist_path = get_checklist_path(project_root)

    if not checklist_path.exists():
        print_warning("Checklist not found. Run 'pc checklist' first.")
        return

    try:
        content = checklist_path.read_text(encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"  PROJECT CHECKLIST")
        print(f"{'='*60}")
        print(f"\nFile: {checklist_path}")
        print(f"Size: {len(content)} characters")
        print(f"{'='*60}\n")
        print(content)
    except Exception as e:
        print_error(f"Failed to read checklist: {e}")


def view_writers_report(project_root: Path) -> None:
    """
    View the writers report.

    Args:
        project_root: Project root directory
    """
    report_path = get_writers_report_path(project_root)

    if not report_path.exists():
        print_warning("Writers report not found. Run 'pc writers' first.")
        return

    try:
        content = report_path.read_text(encoding="utf-8")
        print(f"\n{'='*60}")
        print(f"  WRITERS REPORT")
        print(f"{'='*60}")
        print(f"\nFile: {report_path}")
        print(f"Size: {len(content)} characters")
        print(f"{'='*60}\n")
        print(content)
    except Exception as e:
        print_error(f"Failed to read writers report: {e}")


# ── Report Listing ───────────────────────────────────────────────────

def list_all_reports(project_root: Path) -> list[dict]:
    """
    List all available reports in the project.

    Args:
        project_root: Project root directory

    Returns:
        List of report dictionaries with name, path, size, and exists status
    """
    reports = [
        {
            "name": "Ghost Report",
            "description": "Orphans, legacy, sessions, duplicates, semantic findings",
            "path": get_ghost_report_path(project_root),
            "type": "ghost"
        },
        {
            "name": "Graph Report",
            "description": "Dependency graph analysis and metrics",
            "path": get_graph_report_path(project_root),
            "type": "graph"
        },
        {
            "name": "Project Checklist",
            "description": "All project files as a checklist",
            "path": get_checklist_path(project_root),
            "type": "checklist"
        },
        {
            "name": "Writers Report",
            "description": "Writer pattern analysis",
            "path": get_writers_report_path(project_root),
            "type": "writers"
        }
    ]

    # Add metadata
    for report in reports:
        report["exists"] = report["path"].exists()
        if report["exists"]:
            report["size_bytes"] = report["path"].stat().st_size
            report["size_kb"] = f"{report['size_bytes'] / 1024:.1f} KB"
        else:
            report["size_bytes"] = 0
            report["size_kb"] = "N/A"

    return reports


def display_report_list(project_root: Path) -> None:
    """
    Display a formatted list of all available reports.

    Args:
        project_root: Project root directory
    """
    reports = list_all_reports(project_root)

    print(f"\n{'='*60}")
    print(f"  AVAILABLE REPORTS")
    print(f"{'='*60}\n")

    for i, report in enumerate(reports, 1):
        status = "✓" if report["exists"] else "✗"
        print(f"{i}) {report['name']} {status}")
        print(f"   {report['description']}")
        print(f"   Size: {report['size_kb']}")

        if report["exists"]:
            print(f"   Path: {report['path']}")

        print()


# ── Report Refreshing ───────────────────────────────────────────────

def refresh_report(project_root: Path, report_type: str) -> bool:
    """
    Refresh/regenerate a specific report.

    Args:
        project_root: Project root directory
        report_type: Type of report to refresh (ghost, graph, checklist, writers)

    Returns:
        True if refresh was successful, False otherwise
    """
    # This is a placeholder - actual refresh logic would call the respective services
    print_warning(f"Report refresh for '{report_type}' not yet implemented.")
    print(f"   Use the respective menu option to regenerate the report.")
    return False
