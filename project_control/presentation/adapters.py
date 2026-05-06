"""Shared workflow-to-text adapters used by desktop and text UIs."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from project_control.analysis.dead_analyzer import analyze_dead_code
from project_control.analysis.vfx_contract_audit import vfx_contract_result_to_dict
from project_control.cli.graph_cmd import (
    _find_symbol_usages,
    _load_or_build_graph,
    _render_trace,
    _resolve_target_node,
)
from project_control.config.graph_config import load_graph_config
from project_control.core.content_store import ContentStore
from project_control.core.ghost import ghost
from project_control.core.ghost_service import run_ghost, write_ghost_report, write_ghost_tree_report
from project_control.core.snapshot_service import load_snapshot
from project_control.render.dead_renderer import render_dead
from project_control.render.ui_verification_renderer import render_ui_verification_console_summary
from project_control.render.vfx_contract_renderer import render_vfx_contract_console
from project_control.services._config import config_with_state
from project_control.services.report_service import (
    get_graph_metrics_path,
    get_graph_report_path,
    get_ui_verification_data_path,
    get_ui_verification_html_path,
    get_ui_verification_report_path,
    get_vfx_contract_data_path,
    get_vfx_contract_report_path,
    list_all_reports,
)
from project_control.services.scan_service import ScanService
from project_control.services.ui_verification_service import run_ui_verification_profile
from project_control.services.vfx_contract_service import run_vfx_contract_audit
from project_control.ui.state import AppState


@dataclass
class PresentationResult:
    """Normalized output for GUI/TUI consumers."""

    workflow: str
    title: str
    summary: dict[str, Any]
    primary_text: str
    report_paths: dict[str, Path] = field(default_factory=dict)


def present_scan(project_root: Path) -> PresentationResult:
    """Run scan and return a normalized text result."""
    result = ScanService().execute(project_root)
    if not result.success:
        raise RuntimeError(result.message)

    snapshot = result.data.get("snapshot", {})
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    summary = {
        "file_count": snapshot.get("file_count", result.data.get("file_count", 0)),
        "snapshot_path": snapshot_path,
    }
    primary_text = "\n".join(
        [
            result.message,
            f"Snapshot: {snapshot_path}",
            f"Indexed files: {summary['file_count']}",
        ]
    )
    return PresentationResult(
        workflow="scan",
        title="Scan",
        summary=summary,
        primary_text=primary_text,
        report_paths={"snapshot": snapshot_path},
    )


def present_ghost(project_root: Path, *, mode: str = "pragmatic", tree: bool = True) -> PresentationResult:
    """Run ghost analysis and return markdown/tree aware output."""
    args = argparse.Namespace(
        mode=mode,
        max_high=-1,
        max_medium=-1,
        max_low=-1,
        max_info=-1,
        tree=tree,
    )
    ghost_data = run_ghost(args, project_root)
    if ghost_data is None:
        raise RuntimeError("Ghost analysis did not return data.")

    result = ghost_data["result"]
    counts = ghost_data["counts"]
    write_ghost_report(result, project_root)
    if tree:
        write_ghost_tree_report(result, project_root)

    exports_dir = project_root / ".project-control" / "exports"
    report_paths: dict[str, Path] = {
        "markdown": exports_dir / "ghost_candidates.md",
    }
    lines = [
        "Ghost Results",
        "-------------",
        f"Orphans:   {counts.get('orphans', 0)}",
        f"Legacy:    {counts.get('legacy', 0)}",
        f"Sessions:  {counts.get('sessions', 0)}",
        f"Duplicates:{counts.get('duplicates', 0)}",
        f"Semantic:  {counts.get('semantic', 0)}",
    ]

    if tree:
        tree_chunks: list[str] = []
        for key in ("orphans", "legacy", "sessions", "duplicates", "semantic"):
            tree_path = exports_dir / f"ghost_{key}_tree.txt"
            if tree_path.exists():
                report_paths[f"{key}_tree"] = tree_path
                tree_chunks.append(tree_path.read_text(encoding="utf-8"))
        if tree_chunks:
            lines.append("")
            lines.append("ASCII Trees")
            lines.append("-----------")
            lines.append("\n\n".join(tree_chunks))

    if ghost_data.get("limit_violation"):
        lines.append("")
        lines.append(ghost_data["limit_violation"]["message"])

    return PresentationResult(
        workflow="ghost",
        title="Ghost Analysis",
        summary=counts,
        primary_text="\n".join(lines),
        report_paths=report_paths,
    )


def present_dead(project_root: Path, *, threshold: int = 2) -> PresentationResult:
    """Run dead-code analysis using the canonical string-based renderer."""
    snapshot = load_snapshot(project_root)
    files = [entry.get("path") for entry in snapshot.get("files", []) if entry.get("path")]
    result = analyze_dead_code(files, low_usage_threshold=threshold)
    summary = {
        "total_files": result.get("stats", {}).get("total", 0),
        "dead_files": result.get("stats", {}).get("dead", 0),
        "low_usage_files": len(result.get("medium", [])),
    }
    return PresentationResult(
        workflow="dead",
        title="Dead Code Radar",
        summary=summary,
        primary_text=render_dead(result),
    )


def present_graph_report(project_root: Path, state: AppState) -> PresentationResult:
    """Ensure graph artifacts exist and return summary plus report body."""
    cfg = config_with_state(project_root, state)
    from project_control.graph.ensure import ensure_graph

    _, metrics_path, report_path = ensure_graph(project_root, cfg, force=False)
    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    report_text = report_path.read_text(encoding="utf-8")
    totals = metrics.get("totals", {})
    summary = {
        "nodes": totals.get("nodeCount", 0),
        "edges": totals.get("edgeCount", 0),
        "cycles": len(metrics.get("cycles", [])),
        "orphans": len(metrics.get("orphanCandidates", [])),
    }
    primary_text = "\n".join(
        [
            "Graph Report",
            "------------",
            f"Nodes:   {summary['nodes']}",
            f"Edges:   {summary['edges']}",
            f"Cycles:  {summary['cycles']}",
            f"Orphans: {summary['orphans']}",
            "",
            report_text,
        ]
    )
    return PresentationResult(
        workflow="graph_report",
        title="Graph Report",
        summary=summary,
        primary_text=primary_text,
        report_paths={
            "metrics": metrics_path,
            "report": report_path,
        },
    )


def present_graph_trace(
    project_root: Path,
    state: AppState,
    *,
    target: str,
    direction: str = "both",
) -> PresentationResult:
    """Trace graph paths without routing through CLI stdout parsing."""
    snapshot = load_snapshot(project_root)
    config = config_with_state(project_root, state)
    graph = _load_or_build_graph(project_root, snapshot, config)
    if graph is None:
        raise RuntimeError("Graph unavailable. Run scan first.")

    id_to_path = {node["id"]: node["path"] for node in graph.get("nodes", [])}
    target_id, symbol_defs = _resolve_target_node(project_root, target, id_to_path)
    if target_id is None:
        raise RuntimeError(f"Target '{target}' not found in graph nodes.")

    from project_control.graph.trace import trace_paths

    max_depth = None if state.trace_all_paths else state.trace_depth
    max_paths = None if state.trace_all_paths else 200
    traces = trace_paths(graph, target_id, direction=direction, max_depth=max_depth, max_paths=max_paths)
    symbol_usages = _find_symbol_usages(target, limit=50)
    lines = _render_trace(graph, traces, target, target_id, symbol_defs, symbol_usages, show_line=True)

    trace_path = project_root / ".project-control" / "out" / "graph.trace.txt"
    trace_path.parent.mkdir(parents=True, exist_ok=True)
    trace_path.write_text("\n".join(lines), encoding="utf-8")

    summary = {
        "target": id_to_path.get(target_id, target),
        "inbound_paths": len(traces.get("inbound", [])),
        "outbound_paths": len(traces.get("outbound", [])),
    }
    return PresentationResult(
        workflow="graph_trace",
        title="Graph Trace",
        summary=summary,
        primary_text="\n".join(lines),
        report_paths={"trace": trace_path},
    )


def present_vfx_audit(project_root: Path) -> PresentationResult:
    """Run the VFX contract audit."""
    result, markdown_path, json_path = run_vfx_contract_audit(project_root)
    data = vfx_contract_result_to_dict(result)
    return PresentationResult(
        workflow="vfx_audit",
        title="VFX Contract Audit",
        summary=data.get("summary", {}),
        primary_text=render_vfx_contract_console(result),
        report_paths={
            "markdown": markdown_path,
            "json": json_path,
        },
    )


def present_ui_verification(
    project_root: Path,
    *,
    profile_name: str | None = None,
    config_path: str | None = None,
    url: str | None = None,
    image_path: str | None = None,
    screenshots_dir: str | None = None,
    output_dir: str | None = None,
    headless: bool = True,
    include_html: bool = True,
) -> PresentationResult:
    """Run UI verification and normalize the outputs."""
    report, resolved_config_path, markdown_path, json_path, html_path = run_ui_verification_profile(
        project_root,
        config_path=config_path,
        profile_name=profile_name,
        url=url,
        image_path=image_path,
        screenshots_dir=screenshots_dir,
        headless=headless,
        output_dir=output_dir,
        include_html=include_html,
    )
    summary = {
        "profile": report.profile_name,
        "passed": report.passed,
        "failed": report.failed,
        "warned": report.warned,
        "pass_rate": report.summary.get("pass_rate", 0),
    }
    report_paths = {
        "config": resolved_config_path,
        "markdown": markdown_path,
        "json": json_path,
    }
    if html_path is not None:
        report_paths["html"] = html_path

    return PresentationResult(
        workflow="ui_verification",
        title="UI Verification",
        summary=summary,
        primary_text=render_ui_verification_console_summary(report),
        report_paths=report_paths,
    )


def present_report_registry(project_root: Path) -> PresentationResult:
    """Return a text-first view of all generated reports."""
    reports = list_all_reports(project_root)
    lines = ["Available Reports", "-----------------"]
    for report in reports:
        status = "OK" if report.get("exists") else "MISSING"
        lines.append(f"- {report['name']}: {status} ({report.get('size_kb', 'N/A')})")
        lines.append(f"  Path: {report['path']}")
    return PresentationResult(
        workflow="reports",
        title="Reports",
        summary={"report_count": len(reports), "available": sum(1 for report in reports if report.get("exists"))},
        primary_text="\n".join(lines),
        report_paths={
            "graph_report": get_graph_report_path(project_root),
            "graph_metrics": get_graph_metrics_path(project_root),
            "vfx_markdown": get_vfx_contract_report_path(project_root),
            "vfx_json": get_vfx_contract_data_path(project_root),
            "ui_markdown": get_ui_verification_report_path(project_root),
            "ui_json": get_ui_verification_data_path(project_root),
            "ui_html": get_ui_verification_html_path(project_root),
        },
    )


def present_overview(project_root: Path, state: AppState) -> PresentationResult:
    """Build a lightweight overview without depending on Rich/dashboard code."""
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"
    report_info = list_all_reports(project_root)

    summary = {
        "project": project_root.name,
        "mode": state.project_mode,
        "snapshot": snapshot_path.exists(),
        "graph": graph_path.exists(),
        "reports": sum(1 for report in report_info if report.get("exists")),
    }
    lines = [
        f"Project: {project_root.name}",
        f"Mode: {state.project_mode}",
        f"Snapshot: {'READY' if snapshot_path.exists() else 'MISSING'}",
        f"Graph: {'READY' if graph_path.exists() else 'MISSING'}",
        f"Reports available: {summary['reports']}",
        "",
        "Generated reports:",
    ]
    for report in report_info:
        lines.append(f"- {report['name']}: {'OK' if report.get('exists') else 'MISSING'}")
    return PresentationResult(
        workflow="overview",
        title="Overview",
        summary=summary,
        primary_text="\n".join(lines),
    )


def load_ghost_core_data(project_root: Path) -> dict[str, Any]:
    """Load canonical ghost data directly without service side effects."""
    snapshot = load_snapshot(project_root)
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    content_store = ContentStore(snapshot, snapshot_path)
    from project_control.config.patterns_loader import load_patterns

    patterns = load_patterns(project_root)
    return ghost(snapshot, patterns, content_store)
