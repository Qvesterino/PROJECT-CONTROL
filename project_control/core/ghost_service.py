"""Ghost analysis execution and report writing services."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, TypedDict

from project_control.analysis import graph_exporter
from project_control.analysis.graph_trend import GraphTrendAnalyzer
from project_control.analysis.tree_renderer import render_tree
from project_control.analysis.layer_boundary_validator import validate_boundaries
from project_control.analysis.self_architecture_validator import validate_architecture
from project_control.persistence.drift_history_repository import DriftHistoryRepository
from project_control.usecases.ghost_workflow import GhostWorkflow
from project_control.core.markdown_renderer import SEVERITY_MAP, render_ghost_report
from project_control.core.snapshot_service import load_snapshot
from project_control.core.dto import ResultValidationError
from project_control.core.exit_codes import (
    EXIT_CONTRACT_ERROR,
    EXIT_LAYER_VIOLATION,
    EXIT_VALIDATION_ERROR,
    EXIT_OK,
)


SECTION_DISPLAY_NAMES = {
    "orphans": "Orphans",
    "legacy": "Legacy snippets",
    "session": "Session files",
    "duplicates": "Duplicates",
}

SECTION_LIMIT_ARGS = {
    "orphans": ("max-high", "max_high"),
    "legacy": ("max-medium", "max_medium"),
    "session": ("max-low", "max_low"),
    "duplicates": ("max-info", "max_info"),
}


class LimitViolation(TypedDict):
    message: str
    exit_code: int


class GhostResult(TypedDict):
    dto: Dict[str, Any]
    counts: Dict[str, int]
    limit_violation: Optional[LimitViolation]
    deep_report_path: Optional[Path]
    ghost_report_path: Path


def _ensure_control_dirs(project_root: Path) -> None:
    control_dir = project_root / ".project-control"
    exports_dir = control_dir / "exports"
    control_dir.mkdir(exist_ok=True)
    exports_dir.mkdir(exist_ok=True)


def _load_compare_snapshot(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def run_ghost(args, project_root: Path) -> Optional[GhostResult]:
    """Execute ghost analysis flow and limit checks."""
    _ensure_control_dirs(project_root)

    if getattr(args, "validate_architecture", False):
        violations = validate_architecture()
        if violations:
            print("ARCHITECTURE VIOLATION:")
            for v in violations:
                print(f"{v.file}:{v.line} → {v.target}")
                print(f"Rule: {v.rule}")
            raise SystemExit(EXIT_LAYER_VIOLATION)
        print("ARCHITECTURE VALIDATION PASSED")
        print("No layer violations detected.")
        return None

    try:
        snapshot = load_snapshot(project_root)
    except FileNotFoundError:
        print("Run 'pc scan' first.")
        return None

    if args.deep:
        print("Running deep import graph analysis... this may take a while.")

    if args.deep:
        violations = validate_boundaries()
        if violations:
            print("ARCHITECTURE LAYER VIOLATION DETECTED")
            for v in violations:
                print(f"{v.file}:{v.line} imports {v.import_path}")
            raise SystemExit(EXIT_LAYER_VIOLATION)

    compare_snapshot: Optional[Dict[str, Any]] = None
    if getattr(args, "compare_snapshot", None):
        compare_snapshot = _load_compare_snapshot(Path(args.compare_snapshot))

    workflow = GhostWorkflow(project_root, debug=getattr(args, "debug", False))
    repo = DriftHistoryRepository(project_root)
    history_data = repo.load()
    history_list = repo.current_history() if history_data is not None else None

    try:
        dto, updated_history = workflow.run(
            snapshot,
            compare_snapshot=compare_snapshot,
            deep=args.deep,
            mode=args.mode,
            history=history_list,
        )
    except ResultValidationError as exc:
        print("INTERNAL RESULT CONTRACT VIOLATION")
        print(str(exc))
        raise SystemExit(EXIT_CONTRACT_ERROR)

    if args.deep and history_data is not None and updated_history is not None:
        repo.data["history"] = updated_history
        repo.save()

    validation_section = dto.get("validation") or {}
    counts = {key: len(validation_section.get(key, [])) for key in SECTION_DISPLAY_NAMES}

    limit_violation: Optional[LimitViolation] = None
    for key, label in SECTION_DISPLAY_NAMES.items():
        limit_label, attr_name = SECTION_LIMIT_ARGS[key]
        limit_value = getattr(args, attr_name, -1)
        if limit_value >= 0 and counts[key] > limit_value:
            severity = SEVERITY_MAP.get(key, "INFO")
            limit_violation = {
                "message": f"Ghost limits exceeded: {label}({severity})={counts[key]} > {limit_label}={limit_value}",
                "exit_code": EXIT_VALIDATION_ERROR,
            }
            break

    return {
        "dto": dto,
        "counts": counts,
        "limit_violation": limit_violation,
        "deep_report_path": Path(".project-control") / "exports" / "import_graph_orphans.md" if args.deep else None,
        "ghost_report_path": Path(".project-control") / "exports" / "ghost_candidates.md",
    }


def write_ghost_reports(result: GhostResult, project_root: Path, args) -> None:
    """Write ghost markdown outputs according to CLI options."""
    exports_dir = project_root / ".project-control" / "exports"
    dto = result["dto"]
    validation_section = dto.get("validation") or {}
    analysis_section = dto.get("analysis") or {}
    graph_section = dto.get("graph") or {}

    if args.deep:
        graph_report_path = exports_dir / "import_graph_orphans.md"
        graph_orphans = validation_section.get("graph_orphans", [])
        graph_lines = [
            "# Import Graph Orphans",
            "",
            "## Legend",
            "(Directory tree based on import graph reachability)",
            "",
            "# NOTE",
            "This report is static-import based.",
            "Dynamic runtime wiring (FrameScheduler, registries, side-effects) is not detected.",
            "",
        ]
        if not args.tree_only:
            for path in graph_orphans:
                graph_lines.append(f"- {path}")
        graph_report_path.write_text("\n".join(graph_lines).rstrip() + "\n", encoding="utf-8")

        if graph_orphans:
            tree_output = render_tree(graph_orphans)
            with graph_report_path.open("a", encoding="utf-8") as f:
                f.write("\n## Tree View\n\n")
                f.write(f"Total import graph orphans: {len(graph_orphans)}\n\n")
                f.write(tree_output)

    ghost_report_path = exports_dir / "ghost_candidates.md"
    render_ghost_report(validation_section, str(ghost_report_path))

    metrics = analysis_section.get("metrics", {})
    if args.deep and metrics:
        print("GRAPH SUMMARY:")
        print(f"Nodes: {metrics['node_count']}")
        print(f"Edges: {metrics['edge_count']}")
        print(f"Reachable: {metrics['reachable_count']}")
        print(f"Unreachable: {metrics['unreachable_count']}")
        print(f"Density: {metrics['density']:.4f}")
        print(f"Is DAG: {metrics['is_dag']}")
        print(f"Largest Component: {metrics['largest_component_size']}")
        anomalies = analysis_section.get("anomalies", {})
        if anomalies:
            print("ARCHITECTURE ANOMALY REPORT")
            print(f"Cycle Groups: {anomalies.get('cycle_groups')}")
            print(f"God Modules: {anomalies.get('god_modules')}")
            print(f"Dead Clusters: {anomalies.get('dead_clusters')}")
            print(f"Isolated Nodes: {anomalies.get('isolated_nodes')}")
            print(f"Smell Score: {anomalies.get('smell_score')} ({anomalies.get('smell_level')})")
        
        drift = dto.get("drift")
        if drift and hasattr(args, "compare_snapshot") and args.compare_snapshot:
            print("=== ARCHITECTURAL DRIFT REPORT ===")
            node_drift = drift.get("node_drift", {})
            edge_drift = drift.get("edge_drift", {})
            entrypoint_drift = drift.get("entrypoint_drift", {})
            metric_deltas = drift.get("metric_deltas", {})
            
            print(f"Nodes added: {len(node_drift.get('added', []))}")
            print(f"Nodes removed: {len(node_drift.get('removed', []))}")
            print(f"Edges added: {len(edge_drift.get('added', []))}")
            print(f"Edges removed: {len(edge_drift.get('removed', []))}")
            print(f"Entrypoints added: {len(entrypoint_drift.get('added', []))}")
            print(f"Entrypoints removed: {len(entrypoint_drift.get('removed', []))}")
            
            print("Metric deltas:")
            for metric, delta in metric_deltas.items():
                prefix = "+" if delta > 0 else ""
                print(f"  {metric}: {prefix}{delta}")
            
            print(f"Drift severity: {drift.get('severity', 'UNKNOWN')}")
            repo = DriftHistoryRepository(project_root)
            history_data = repo.load()
            if history_data is not None:
                before_count = len(repo.current_history())
                repo.append({"timestamp": datetime.now(timezone.utc).isoformat(), "drift": drift})
                repo.save()
                after_history = repo.current_history()
                trimmed = max(0, before_count + 1 - repo.max_entries)
                if getattr(args, "debug", False):
                    print(f"Drift history entries: {len(after_history)}")
                    print(f"Trimmed: {trimmed}")
                    print(f"Version: {history_data.get('version', 'unknown')}")
                if len(after_history) >= 2:
                    trend = GraphTrendAnalyzer([entry["drift"] for entry in after_history]).compute()
                    if trend:
                        dto["trend"] = trend
                        print("=== STABILITY TREND REPORT ===")
                        print(f"Average Intensity: {trend.get('avg_intensity')}")
                        print(f"Volatility: {trend.get('volatility')}")
                        print(f"Stability Index: {trend.get('stability_index')}")
                        print(f"Classification: {trend.get('classification')}")

    if args.deep and getattr(args, "export_graph", False):
        graph_map = graph_section.get("edges", {})
        if graph_map:
            dot_path = exports_dir / "import_graph.dot"
            mermaid_path = exports_dir / "import_graph.mmd"
            graph_exporter.export_dot(graph_map, dot_path)
            graph_exporter.export_mermaid(graph_map, mermaid_path)
            print(f"GRAPH EXPORTED: {dot_path}")
