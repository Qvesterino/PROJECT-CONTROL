"""UI Result DTO v1 builder and validator."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

ENGINE_RESULT_VERSION = "ui_result_dto_v1"


def _iso_utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _require_keys(mapping: Dict[str, Any], keys: Iterable[str], label: str) -> None:
    for key in keys:
        _ensure(key in mapping, f"{label} missing key: {key}")


def _normalize_edges(adjacency: Dict[str, Any]) -> Dict[str, List[str]]:
    nodes: set[str] = set(adjacency.keys())
    normalized: Dict[str, List[str]] = {}
    for neighbors in adjacency.values():
        nodes.update(neighbors)
    for node in sorted(nodes):
        raw_neighbors = adjacency.get(node, [])
        if isinstance(raw_neighbors, set):
            raw_neighbors = list(raw_neighbors)
        normalized[node] = sorted(raw_neighbors)
    return normalized


def _build_graph_section(
    graph_payload: Optional[Dict[str, Any]],
    metrics_payload: Optional[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    if not graph_payload or not metrics_payload:
        return None

    adjacency = graph_payload.get("graph", graph_payload)
    adjacency = adjacency or {}

    edges = _normalize_edges(adjacency)

    entrypoints = metrics_payload.get("entry_modules") or graph_payload.get("entrypoints") or []
    reachable = metrics_payload.get("reachable_nodes", [])
    unreachable = metrics_payload.get("unreachable_nodes", [])

    nodes = set(edges.keys())
    nodes.update(entrypoints)
    nodes.update(reachable)
    nodes.update(unreachable)
    nodes = sorted(nodes)

    # Ensure every node is represented in edges even if isolated.
    for node in nodes:
        edges.setdefault(node, [])

    return {
        "nodes": nodes,
        "edges": edges,
        "entrypoints": sorted(entrypoints),
        "reachable": sorted(reachable),
        "unreachable": sorted(unreachable),
    }


def build_ui_result_dto(
    *,
    mode: str,
    deep: bool,
    debug: bool,
    engine_version: Optional[str],
    graph_payload: Optional[Dict[str, Any]],
    metrics_payload: Optional[Dict[str, Any]],
    anomalies_payload: Optional[Dict[str, Any]],
    drift_payload: Optional[Dict[str, Any]],
    trend_payload: Optional[Dict[str, Any]],
    validation_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    meta = {
        "timestamp": _iso_utc_timestamp(),
        "mode": mode,
        "deep": bool(deep),
        "debug": bool(debug),
        "version": ENGINE_RESULT_VERSION,
        "engine_version": engine_version,
    }

    graph_section = _build_graph_section(graph_payload, metrics_payload) if deep else None
    analysis_section = None
    if deep:
        analysis_section = {
            "metrics": metrics_payload or {},
            "anomalies": anomalies_payload or {},
        }

    dto = {
        "meta": meta,
        "graph": graph_section,
        "analysis": analysis_section,
        "drift": drift_payload if deep else None,
        "trend": trend_payload if deep else None,
        "validation": validation_payload if validation_payload is not None else None,
    }

    validate_ui_result_dto(dto)
    return dto


def validate_ui_result_dto(dto: Dict[str, Any]) -> None:
    _ensure(isinstance(dto, dict), "DTO must be a dict")
    _require_keys(dto, ["meta", "graph", "analysis", "drift", "trend", "validation"], "dto")

    meta = dto["meta"]
    _ensure(isinstance(meta, dict), "meta must be a dict")
    _require_keys(meta, ["timestamp", "mode", "deep", "debug", "version", "engine_version"], "meta")
    _ensure(meta["version"] == ENGINE_RESULT_VERSION, "meta.version mismatch")

    graph = dto["graph"]
    if graph is not None:
        _ensure(isinstance(graph, dict), "graph must be a dict or None")
        _require_keys(graph, ["nodes", "edges", "entrypoints", "reachable", "unreachable"], "graph")
        _ensure(isinstance(graph["nodes"], list), "graph.nodes must be a list")
        _ensure(isinstance(graph["edges"], dict), "graph.edges must be a dict")
        _ensure(isinstance(graph["entrypoints"], list), "graph.entrypoints must be a list")
        _ensure(isinstance(graph["reachable"], list), "graph.reachable must be a list")
        _ensure(isinstance(graph["unreachable"], list), "graph.unreachable must be a list")

    analysis = dto["analysis"]
    if analysis is not None:
        _ensure(isinstance(analysis, dict), "analysis must be a dict or None")
        _require_keys(analysis, ["metrics", "anomalies"], "analysis")

    validation = dto["validation"]
    if validation is not None:
        _ensure(isinstance(validation, dict), "validation must be a dict or None")
