"""Unified import graph detector that composes language-specific engines."""

from __future__ import annotations

from typing import Any, Dict, List, Set, Tuple

from project_control.analysis.entrypoint_policy import EntryPointPolicy
from project_control.analysis.graph_anomaly import GraphAnomalyAnalyzer
from project_control.analysis.graph_metrics import GraphMetrics
from project_control.analysis.import_graph_engine import ImportGraphEngine
from project_control.analysis.js_import_graph_engine import JSImportGraphEngine
from project_control.analysis.python_import_graph_engine import PythonImportGraphEngine
from project_control.core.content_store import ContentStore


def detect_graph_orphans(
    snapshot: Dict[str, Any],
    patterns: Dict[str, Any],
    content_store: ContentStore,
    apply_ignore: bool = True,
) -> List[str]:
    entrypoints = patterns.get("entrypoints", [])
    ignore_patterns = patterns.get("graph_ignore_patterns", []) if apply_ignore else []
    policy = EntryPointPolicy(snapshot, content_store, patterns)
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
            )
        else:
            orphans, engine_graph = engine.build_graph(
                snapshot, content_store, entrypoints, ignore_patterns
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

    print("PY FILE COUNT:", py_file_count)
    print("JS FILE COUNT:", js_file_count)
    print("TOTAL GRAPH NODES:", total_nodes)
    print("UNREACHABLE:", len(result))
    metrics = GraphMetrics(aggregated_graph, entry_modules).compute()
    from project_control.analysis.graph_anomaly import GraphAnomalyAnalyzer
    anomalies = GraphAnomalyAnalyzer(aggregated_graph, metrics).analyze()
    return {
        "orphans": result,
        "graph": aggregated_graph,
        "metrics": metrics,
        "anomalies": anomalies,
    }
