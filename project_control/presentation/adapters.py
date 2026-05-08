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
from project_control.core.artifact_service import run_artifact_hygiene
from project_control.core.audit_retention_service import run_audit_retention
from project_control.core.content_store import ContentStore
from project_control.core.ghost import ghost
from project_control.core.ghost_service import run_ghost, write_ghost_report, write_ghost_tree_report
from project_control.core.snapshot_service import load_snapshot
from project_control.render.dead_renderer import render_dead
from project_control.render.ui_verification_renderer import render_ui_verification_console_summary
from project_control.render.vfx_contract_renderer import render_vfx_contract_console
from project_control.services._config import config_with_state
from project_control.services.report_service import (
    get_artifact_data_path,
    get_artifact_delete_list_path,
    get_artifact_report_path,
    get_audit_delete_list_path,
    get_audit_retention_data_path,
    get_audit_retention_report_path,
    get_ecosystem_health_data_path,
    get_ecosystem_health_report_path,
    get_graph_metrics_path,
    get_graph_report_path,
    get_patron_path_data_path,
    get_patron_path_report_path,
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


def _control_dir(project_root: Path) -> Path:
    return project_root / ".project-control"


def _snapshot_path(project_root: Path) -> Path:
    return _control_dir(project_root) / "snapshot.json"


def _graph_snapshot_path(project_root: Path) -> Path:
    return _control_dir(project_root) / "out" / "graph.snapshot.json"


def _is_initialized(project_root: Path) -> bool:
    return (_control_dir(project_root) / "patterns.yaml").exists()


def _has_snapshot(project_root: Path) -> bool:
    return _snapshot_path(project_root).exists()


def _has_graph(project_root: Path) -> bool:
    return _graph_snapshot_path(project_root).exists()


def _guided_result(
    project_root: Path,
    *,
    workflow: str,
    title: str,
    requires_graph: bool = False,
) -> PresentationResult:
    initialized = _is_initialized(project_root)
    snapshot_ready = _has_snapshot(project_root)
    graph_ready = _has_graph(project_root)

    if not initialized:
        message = "This project is not set up yet."
        action = "Run Scan to initialize PROJECT CONTROL and create the first snapshot."
        status = "Setup required"
    elif not snapshot_ready:
        message = "PROJECT CONTROL is ready, but this project has not been scanned yet."
        action = "Run Scan to create the first snapshot."
        status = "Scan required"
    elif requires_graph and not graph_ready:
        message = "Snapshot data is ready, but the dependency graph is not built yet."
        action = "Run Graph Report to build the graph and open the report."
        status = "Graph required"
    else:
        message = "This workflow is not ready yet."
        action = "Run the prerequisite steps below."
        status = "Not ready"

    steps = ["1. Run Scan"]
    if requires_graph:
        steps.append("2. Run Graph Report")
        steps.append("3. Use Graph Trace or return to other audits")
    else:
        steps.append("2. Run Graph Report")
        steps.append("3. Run Ghost / Artifacts / Audit Retention")

    primary_text = "\n".join(
        [
            title,
            "-" * len(title),
            message,
            action,
            "",
            "Next steps:",
            *steps,
        ]
    )
    return PresentationResult(
        workflow=workflow,
        title=title,
        summary={
            "status": status,
            "setup": "Ready" if initialized else "Needed",
            "snapshot": "Ready" if snapshot_ready else "Missing",
            "graph": "Ready" if graph_ready else "Missing",
        },
        primary_text=primary_text,
        report_paths={
            "snapshot": _snapshot_path(project_root),
            "graph": _graph_snapshot_path(project_root),
        },
    )


def present_graph_status(project_root: Path, state: AppState) -> PresentationResult:
    """Return a no-side-effect graph onboarding/status view."""
    if not _is_initialized(project_root) or not _has_snapshot(project_root) or not _has_graph(project_root):
        return _guided_result(project_root, workflow="graph_report", title="Graph", requires_graph=True)
    return present_graph_report(project_root, state, build_if_missing=False)


def present_workflow_status(
    project_root: Path,
    *,
    workflow: str,
    title: str,
    requires_graph: bool = False,
) -> PresentationResult:
    """Return a no-side-effect onboarding state for a workflow tab."""
    initialized = _is_initialized(project_root)
    snapshot_ready = _has_snapshot(project_root)
    graph_ready = _has_graph(project_root)
    if initialized and snapshot_ready and (graph_ready or not requires_graph):
        lines = [
            title,
            "-" * len(title),
            "This workflow is ready.",
        ]
        if requires_graph:
            lines.extend(
                [
                    "Run Graph Report to refresh metrics, or use Graph Trace to inspect a dependency path.",
                    "",
                    "Next steps:",
                    "1. Run Graph Report",
                    "2. Enter a trace target",
                    "3. Use Graph Trace",
                ]
            )
        else:
            lines.extend(
                [
                    "Use the actions in this tab when you want to inspect cleanup, risk, or dead-code candidates.",
                    "",
                    "Next steps:",
                    "1. Run Ghost or Run Dead",
                    "2. Run Artifacts or Audit Retention",
                    "3. Open Reports",
                ]
            )
        return PresentationResult(
            workflow=workflow,
            title=title,
            summary={
                "status": "Ready",
                "setup": "Ready",
                "snapshot": "Ready",
                "graph": "Ready" if graph_ready else "Optional",
            },
            primary_text="\n".join(lines),
            report_paths={
                "snapshot": _snapshot_path(project_root),
                "graph": _graph_snapshot_path(project_root),
            },
        )
    return _guided_result(project_root, workflow=workflow, title=title, requires_graph=requires_graph)


def present_scan(project_root: Path, *, interactive: bool = False) -> PresentationResult:
    """Run scan and return a normalized text result."""
    result = ScanService().execute(project_root, auto_init=interactive)
    if not result.success:
        raise RuntimeError(result.message)

    snapshot = result.data.get("snapshot", {})
    initialization = result.data.get("initialization")
    snapshot_path = _snapshot_path(project_root)
    summary = {
        "file_count": snapshot.get("file_count", result.data.get("file_count", 0)),
        "snapshot_path": snapshot_path,
        "setup": "Ready",
    }
    lines = []
    if initialization and getattr(initialization, "initialized_now", False):
        lines.extend(
            [
                "PROJECT CONTROL was not set up for this project yet.",
                "PROJECT CONTROL initialized this project and created the first snapshot.",
                "",
            ]
        )
    lines.extend(
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
        primary_text="\n".join(lines),
        report_paths={"snapshot": snapshot_path},
    )


def present_ghost(project_root: Path, *, mode: str = "pragmatic", tree: bool = True) -> PresentationResult:
    """Run ghost analysis and return markdown/tree aware output."""
    if not _is_initialized(project_root) or not _has_snapshot(project_root):
        return _guided_result(project_root, workflow="ghost", title="Ghost / Dead")

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
    if not _is_initialized(project_root) or not _has_snapshot(project_root):
        return _guided_result(project_root, workflow="dead", title="Ghost / Dead")

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


def present_artifacts(
    project_root: Path,
    *,
    older_than: int | None = None,
    min_score: int | None = None,
    by_resolution: bool = False,
) -> PresentationResult:
    """Run artifact hygiene and normalize the result for GUI/TUI consumers."""
    if not _is_initialized(project_root) or not _has_snapshot(project_root):
        return _guided_result(project_root, workflow="artifacts", title="Audits")

    args = argparse.Namespace(
        older_than=older_than,
        min_score=min_score,
        by_resolution=by_resolution,
        json=False,
        delete_list=False,
    )
    artifact_data = run_artifact_hygiene(args, project_root)
    result = artifact_data["result"]
    summary = result.get("summary", {})
    safe_candidates = result.get("safe_to_delete_candidates", [])
    top_safe_candidates = safe_candidates[:10]
    lines = [
        "Artifact Hygiene",
        "----------------",
        f"Safe to delete now: {summary.get('safe_to_delete', 0)}",
        f"Reclaimable space: {summary.get('safe_to_delete_mb', 0)} MB",
        f"Duplicate groups: {summary.get('duplicate_groups', 0)}",
        f"High confidence: {summary.get('high_confidence_cleanup_candidates', 0)}",
    ]
    if top_safe_candidates:
        lines.append("")
        lines.append("Top Safe Delete Candidates")
        lines.append("-------------------------")
        lines.extend(
            f"- {candidate['path']} ({candidate.get('size_bytes', 0)} B)"
            for candidate in top_safe_candidates
        )

    return PresentationResult(
        workflow="artifacts",
        title="Artifact Hygiene",
        summary={
            "safe_to_delete": summary.get("safe_to_delete", 0),
            "reclaimable_mb": summary.get("safe_to_delete_mb", 0),
            "duplicate_groups": summary.get("duplicate_groups", 0),
            "high_confidence": summary.get("high_confidence_cleanup_candidates", 0),
        },
        primary_text="\n".join(lines),
        report_paths={
            "markdown": artifact_data["paths"]["markdown"],
            "json": artifact_data["paths"]["json"],
            "delete_list": artifact_data["paths"]["delete_list"],
        },
    )


def present_audit_retention(
    project_root: Path,
    *,
    older_than: int | None = None,
    min_score: int | None = None,
    keep_latest: int | None = None,
    by_family: bool = False,
) -> PresentationResult:
    """Run audit retention and normalize the result for GUI/TUI consumers."""
    if not _is_initialized(project_root) or not _has_snapshot(project_root):
        return _guided_result(project_root, workflow="audit_retention", title="Audits")

    args = argparse.Namespace(
        older_than=older_than,
        min_score=min_score,
        keep_latest=keep_latest,
        by_family=by_family,
        json=False,
        delete_list=False,
    )
    retention_data = run_audit_retention(args, project_root)
    result = retention_data["result"]
    summary = result.get("summary", {})
    safe_candidates = result.get("safe_to_delete_candidates", [])
    top_safe_candidates = safe_candidates[:10]
    lines = [
        "Audit Retention",
        "---------------",
        f"Safe to delete now: {summary.get('safe_to_delete', 0)}",
        f"Reclaimable space: {summary.get('safe_to_delete_mb', 0)} MB",
        f"Duplicate groups: {summary.get('duplicate_groups', 0)}",
        f"High confidence: {summary.get('high_confidence_cleanup_candidates', 0)}",
        f"Families detected: {summary.get('families_detected', 0)}",
    ]
    if top_safe_candidates:
        lines.append("")
        lines.append("Top Safe Delete Candidates")
        lines.append("-------------------------")
        lines.extend(
            f"- {candidate['path']} ({candidate.get('size_bytes', 0)} B)"
            for candidate in top_safe_candidates
        )

    return PresentationResult(
        workflow="audit_retention",
        title="Audit Retention",
        summary={
            "safe_to_delete": summary.get("safe_to_delete", 0),
            "reclaimable_mb": summary.get("safe_to_delete_mb", 0),
            "duplicate_groups": summary.get("duplicate_groups", 0),
            "high_confidence": summary.get("high_confidence_cleanup_candidates", 0),
            "families_detected": summary.get("families_detected", 0),
        },
        primary_text="\n".join(lines),
        report_paths={
            "markdown": retention_data["paths"]["markdown"],
            "json": retention_data["paths"]["json"],
            "delete_list": retention_data["paths"]["delete_list"],
        },
    )


def present_graph_report(project_root: Path, state: AppState, *, build_if_missing: bool = True) -> PresentationResult:
    """Ensure graph artifacts exist and return summary plus report body."""
    if not _is_initialized(project_root) or not _has_snapshot(project_root):
        return _guided_result(project_root, workflow="graph_report", title="Graph", requires_graph=True)

    if not build_if_missing and not _has_graph(project_root):
        return _guided_result(project_root, workflow="graph_report", title="Graph", requires_graph=True)

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
    if not _is_initialized(project_root) or not _has_snapshot(project_root) or not _has_graph(project_root):
        return _guided_result(project_root, workflow="graph_trace", title="Graph", requires_graph=True)

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
    if not _is_initialized(project_root) or not _has_snapshot(project_root):
        return _guided_result(project_root, workflow="vfx_audit", title="Audits")

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
    available = sum(1 for report in reports if report.get("exists"))
    lines = ["Reports", "-------"]
    if available == 0:
        lines.extend(
            [
                "No reports are generated yet.",
                "Run Scan first, then use Graph, Ghost, or the audit workflows to populate this workspace.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"{available} of {len(reports)} report artifacts are available right now.",
                "",
            ]
        )
    for report in reports:
        status = "OK" if report.get("exists") else "MISSING"
        lines.append(f"- {report['name']}: {status} ({report.get('size_kb', 'N/A')})")
        lines.append(f"  Path: {report['path']}")
    return PresentationResult(
        workflow="reports",
        title="Reports",
        summary={"report_count": len(reports), "available": available},
        primary_text="\n".join(lines),
        report_paths={
            "artifact_markdown": get_artifact_report_path(project_root),
            "artifact_json": get_artifact_data_path(project_root),
            "artifact_delete_list": get_artifact_delete_list_path(project_root),
            "audit_retention_markdown": get_audit_retention_report_path(project_root),
            "audit_retention_json": get_audit_retention_data_path(project_root),
            "audit_retention_delete_list": get_audit_delete_list_path(project_root),
            "graph_report": get_graph_report_path(project_root),
            "graph_metrics": get_graph_metrics_path(project_root),
            "vfx_markdown": get_vfx_contract_report_path(project_root),
            "vfx_json": get_vfx_contract_data_path(project_root),
            "patron_path_markdown": get_patron_path_report_path(project_root),
            "patron_path_json": get_patron_path_data_path(project_root),
            "ecosystem_health_markdown": get_ecosystem_health_report_path(project_root),
            "ecosystem_health_json": get_ecosystem_health_data_path(project_root),
            "ui_markdown": get_ui_verification_report_path(project_root),
            "ui_json": get_ui_verification_data_path(project_root),
            "ui_html": get_ui_verification_html_path(project_root),
        },
    )


def present_overview(project_root: Path, state: AppState) -> PresentationResult:
    """Build a lightweight overview without depending on Rich/dashboard code."""
    snapshot_path = _snapshot_path(project_root)
    graph_path = _graph_snapshot_path(project_root)
    report_info = list_all_reports(project_root)
    initialized = _is_initialized(project_root)
    snapshot_ready = snapshot_path.exists()
    graph_ready = graph_path.exists()

    summary = {
        "setup": "Ready" if initialized else "Needed",
        "snapshot": "Ready" if snapshot_ready else "Missing",
        "graph": "Ready" if graph_ready else "Missing",
        "reports": sum(1 for report in report_info if report.get("exists")),
    }
    lines = [
        f"Project: {project_root.name}",
        f"Mode: {state.project_mode}",
        f"Setup: {summary['setup']}",
        f"Snapshot: {summary['snapshot']}",
        f"Graph: {summary['graph']}",
        f"Reports available: {summary['reports']}",
        "",
    ]
    if not initialized:
        lines.extend(
            [
                "This project is not set up yet.",
                "Run Scan to create the workspace metadata and the first snapshot.",
                "",
                "Next steps:",
                "1. Run Scan",
                "2. Run Graph Report",
                "3. Run Ghost / Artifacts / Audit Retention",
                "",
            ]
        )
    elif not snapshot_ready:
        lines.extend(
            [
                "PROJECT CONTROL is ready, but this project has not been scanned yet.",
                "Run Scan to create the first snapshot and unlock the analysis workflows.",
                "",
                "Next steps:",
                "1. Run Scan",
                "2. Run Graph Report",
                "3. Run Ghost / Artifacts / Audit Retention",
                "",
            ]
        )
    elif not graph_ready:
        lines.extend(
            [
                "Snapshot data is ready. The dependency graph is not built yet.",
                "Run Graph Report to map imports, metrics, and trace paths.",
                "",
                "Next steps:",
                "1. Run Graph Report",
                "2. Use Graph Trace",
                "3. Open Reports",
                "",
            ]
        )
    else:
        lines.extend(
            [
                "The project is ready for audits and report review.",
                "Use Ghost, Graph, Artifacts, or Audit Retention depending on what you need to inspect next.",
                "",
            ]
        )
    lines.extend(
        [
        "Generated reports:",
        ]
    )
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
