"""Deterministic architectural drift tracking for import graphs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple


def compare_snapshots(
    old_graph: Dict[str, Set[str]],
    new_graph: Dict[str, Set[str]],
    old_metrics: Dict[str, Any],
    new_metrics: Dict[str, Any],
    old_entrypoints: List[str],
    new_entrypoints: List[str],
    old_cycle_groups: List[List[str]],
    new_cycle_groups: List[List[str]],
) -> Dict[str, Any]:
    """
    Compare two graph snapshots and detect structural drift.
    
    Args:
        old_graph: Previous graph structure (dict of node -> set of neighbors)
        new_graph: Current graph structure
        old_metrics: Previous metrics dict
        new_metrics: Current metrics dict
        old_entrypoints: Previous entrypoint list
        new_entrypoints: Current entrypoint list
        old_cycle_groups: Previous cycle groups from anomalies
        new_cycle_groups: Current cycle groups from anomalies
    
    Returns:
        Dict containing node_drift, edge_drift, entrypoint_drift, metric_deltas, and severity
    """
    # Node drift
    old_nodes = set(old_graph.keys())
    new_nodes = set(new_graph.keys())
    added_nodes = sorted(new_nodes - old_nodes)
    removed_nodes = sorted(old_nodes - new_nodes)
    
    # Edge drift
    old_edges: Set[Tuple[str, str]] = set()
    for src, targets in old_graph.items():
        for tgt in targets:
            old_edges.add((src, tgt))
    
    new_edges: Set[Tuple[str, str]] = set()
    for src, targets in new_graph.items():
        for tgt in targets:
            new_edges.add((src, tgt))
    
    added_edges = sorted(new_edges - old_edges)
    removed_edges = sorted(old_edges - new_edges)
    
    # Entrypoint drift
    old_entry_set = set(old_entrypoints)
    new_entry_set = set(new_entrypoints)
    added_entrypoints = sorted(new_entry_set - old_entry_set)
    removed_entrypoints = sorted(old_entry_set - new_entry_set)
    
    # Metric deltas
    metric_deltas = {}
    
    # Node count delta
    metric_deltas["nodes"] = new_metrics.get("node_count", 0) - old_metrics.get("node_count", 0)
    
    # Edge count delta
    metric_deltas["edges"] = new_metrics.get("edge_count", 0) - old_metrics.get("edge_count", 0)
    
    # Density delta
    metric_deltas["density"] = new_metrics.get("density", 0) - old_metrics.get("density", 0)
    
    # Cycle groups delta (count-based)
    metric_deltas["cycle_groups"] = len(new_cycle_groups) - len(old_cycle_groups)
    
    # Smell score delta
    old_smell = old_metrics.get("smell_score", 0)
    new_smell = new_metrics.get("smell_score", 0)
    metric_deltas["smell_score"] = round(new_smell - old_smell, 2)
    
    # Build result
    result = {
        "node_drift": {
            "added": added_nodes,
            "removed": removed_nodes,
        },
        "edge_drift": {
            "added": added_edges,
            "removed": removed_edges,
        },
        "entrypoint_drift": {
            "added": added_entrypoints,
            "removed": removed_entrypoints,
        },
        "metric_deltas": metric_deltas,
    }
    
    # Classify severity
    result["severity"] = classify_drift(result)
    
    return result


def classify_drift(result: Dict[str, Any]) -> str:
    """
    Classify drift severity based on changes.
    
    Rules:
    - HIGH: >10% node change OR smell_score delta > 0.1
    - MEDIUM: Only edge changes (no node/entrypoint changes) OR other structural changes not meeting HIGH criteria
    - LOW: Minor changes not meeting other criteria
    - NONE: No changes detected
    
    Args:
        result: Drift comparison result from compare_snapshots()
    
    Returns:
        Severity level: "HIGH", "MEDIUM", "LOW", or "NONE"
    """
    node_drift = result["node_drift"]
    edge_drift = result["edge_drift"]
    entrypoint_drift = result["entrypoint_drift"]
    metric_deltas = result["metric_deltas"]
    
    # Count total nodes in old snapshot for percentage calculation
    total_nodes = len(node_drift["added"]) + len(node_drift["removed"])
    old_node_count = len(node_drift["removed"]) + (total_nodes - len(node_drift["added"]))
    
    # Check for HIGH severity
    if old_node_count > 0:
        node_change_ratio = (len(node_drift["added"]) + len(node_drift["removed"])) / old_node_count
        if node_change_ratio > 0.10:  # >10% node change
            return "HIGH"
    
    # Check smell score delta
    if abs(metric_deltas.get("smell_score", 0)) > 0.1:
        return "HIGH"
    
    # Check for ANY changes
    has_node_changes = bool(node_drift["added"] or node_drift["removed"])
    has_entrypoint_changes = bool(entrypoint_drift["added"] or entrypoint_drift["removed"])
    has_edge_changes = bool(edge_drift["added"] or edge_drift["removed"])
    has_metric_changes = any(v != 0 for v in metric_deltas.values())
    
    if not has_node_changes and not has_entrypoint_changes and not has_edge_changes and not has_metric_changes:
        return "NONE"
    
    # MEDIUM: Only edge changes or other structural changes not meeting HIGH criteria
    if has_edge_changes and not has_node_changes and not has_entrypoint_changes:
        return "MEDIUM"
    
    # If there are any changes (node, entrypoint, or metric), it's at least MEDIUM
    if has_node_changes or has_entrypoint_changes or has_metric_changes:
        return "MEDIUM"
    
    # LOW: Minor edge-only changes not meeting other criteria
    if has_edge_changes:
        return "LOW"
    
    return "NONE"


def load_snapshot_for_comparison(snapshot_path: Path) -> Dict[str, Any]:
    """
    Load a snapshot JSON file for drift comparison.
    
    This is the only place in the drift layer that accesses the filesystem,
    and it only reads from the explicitly provided path.
    
    Args:
        snapshot_path: Path to the snapshot JSON file
    
    Returns:
        The loaded snapshot dictionary
    """
    with snapshot_path.open("r", encoding="utf-8") as f:
        return json.load(f)