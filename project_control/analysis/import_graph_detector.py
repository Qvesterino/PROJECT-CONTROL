"""DEPRECATED/UNUSED: Legacy import graph detector (retained for reference)."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Tuple

from project_control.analysis.entrypoint_policy import EntryPointPolicy
from project_control.analysis.graph_anomaly import GraphAnomalyAnalyzer
from project_control.analysis.graph_drift import compare_snapshots
from project_control.analysis.graph_metrics import GraphMetrics
from project_control.analysis.import_graph_engine import ImportGraphEngine
from project_control.analysis.js_import_graph_engine import JSImportGraphEngine
from project_control.analysis.python_import_graph_engine import PythonImportGraphEngine
from project_control.core.content_store import ContentStore
from project_control.core.debug import debug_print


def detect_graph_orphans(
    snapshot: Dict[str, Any],
    patterns: Dict[str, Any],
    content_store: ContentStore,
    apply_ignore: bool = True,
    compare_snapshot: Optional[Dict[str, Any]] = None,
    debug: bool = False,
) -> Dict[str, Any]:
    entrypoints = patterns.get("entrypoints", [])
    ignore_patterns = patterns.get("graph_ignore_patterns", []) if apply_ignore else []
    policy = EntryPointPolicy(snapshot, content_store, patterns, debug=debug)
    entry_modules = policy.resolve()

    engines: List[ImportGraphEngine] = [
        PythonImportGraphEngine(),
        JSImportGraphEngine(),
    ]

    aggregated_orphans: Set[str] = set()
    aggregated_graph: Dict[str, Set[str]] = {}
    py_file_count = 0
    js_file_count = 0

    for engine in engines:
        if isinstance(engine, PythonImportGraphEngine):
            orphans, engine_graph = engine.build_graph(
                snapshot,
                content_store,
                entrypoints,
                ignore_patterns,
                entry_modules=entry_modules,
                debug=debug,
            )
        else:
            orphans, engine_graph = engine.build_graph(
                snapshot,
                content_store,
                entrypoints,
                ignore_patterns,
                debug=debug,
            )
        aggregated_orphans.update(orphans)
        if isinstance(engine, PythonImportGraphEngine):
            py_file_count = len(orphans)
        elif isinstance(engine, JSImportGraphEngine):
            js_file_count = len(orphans)
        for node, neighbors in engine_graph.items():
            aggregated_graph.setdefault(node, set()).update(neighbors)

    total_nodes = len(aggregated_orphans)
    result = sorted(aggregated_orphans)

    debug_print(debug, "PY FILE COUNT:", py_file_count)
    debug_print(debug, "JS FILE COUNT:", js_file_count)
    debug_print(debug, "TOTAL GRAPH NODES:", total_nodes)
    debug_print(debug, "UNREACHABLE:", len(result))
    metrics = GraphMetrics(aggregated_graph, entry_modules).compute()
    anomalies = GraphAnomalyAnalyzer(aggregated_graph, metrics).analyze()
    
    # Build result with entrypoints
    analysis_result = {
        "orphans": result,
        "graph": aggregated_graph,
        "metrics": metrics,
        "anomalies": anomalies,
        "entrypoints": entry_modules,
    }
    
    # Compute drift if comparison snapshot provided
    if compare_snapshot is not None:
        old_graph = compare_snapshot.get("graph", {})
        old_metrics = compare_snapshot.get("metrics", {})
        old_anomalies = compare_snapshot.get("anomalies", {})
        old_entrypoints = compare_snapshot.get("entrypoints", [])
        old_cycle_groups = old_anomalies.get("cycle_groups", [])

        new_cycle_groups = anomalies.get("cycle_groups", [])

        drift = compare_snapshots(
            old_graph=old_graph,
            new_graph=aggregated_graph,
            old_metrics=old_metrics,
            new_metrics=metrics,
            old_entrypoints=old_entrypoints,
            new_entrypoints=entry_modules,
            old_cycle_groups=old_cycle_groups,
            new_cycle_groups=new_cycle_groups,
        )

        analysis_result["drift"] = drift
    
    return analysis_result
