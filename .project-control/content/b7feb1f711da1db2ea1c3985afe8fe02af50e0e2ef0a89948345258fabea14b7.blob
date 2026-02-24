"""Graph trace engine: enumerate paths with cycle detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Set


@dataclass
class TracePath:
    nodes: List[int]
    ended_by_cycle: bool = False


def trace_paths(
    graph: Dict,
    target_node_id: int,
    direction: str = "both",
    max_depth: int | None = 10,
    max_paths: int | None = 50,
) -> Dict[str, List[TracePath]]:
    """
    Enumerate all paths involving target node.
    direction: inbound | outbound | both.
    Returns dict with keys present per direction.
    """
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    entrypoints = graph.get("entrypoints", [])

    id_to_path = {n["id"]: n["path"] for n in nodes}
    adjacency: Dict[int, Set[int]] = {}
    incoming: Dict[int, Set[int]] = {}
    for edge in edges:
        src = edge.get("fromId")
        dst = edge.get("toId")
        if not src or not dst:
            continue
        adjacency.setdefault(src, set()).add(dst)
        incoming.setdefault(dst, set()).add(src)

    roots = _resolve_roots(entrypoints, id_to_path.keys(), incoming)
    leaves = _resolve_leaves(adjacency, id_to_path.keys())

    result: Dict[str, List[TracePath]] = {}
    if direction in ("inbound", "both"):
        inbound_paths = _enumerate_paths(
            start_nodes=[target_node_id],
            neighbor_fn=lambda node: sorted(incoming.get(node, set()), key=lambda nid: id_to_path.get(nid, "")),
            stop_fn=lambda path: path[-1] in roots,
            max_depth=max_depth,
            max_paths=max_paths,
            reverse_output=True,  # present root -> ... -> target
        )
        result["inbound"] = inbound_paths

    if direction in ("outbound", "both"):
        outbound_paths = _enumerate_paths(
            start_nodes=[target_node_id],
            neighbor_fn=lambda node: sorted(adjacency.get(node, set()), key=lambda nid: id_to_path.get(nid, "")),
            stop_fn=lambda path: path[-1] in leaves,
            max_depth=max_depth,
            max_paths=max_paths,
            reverse_output=False,
        )
        result["outbound"] = outbound_paths

    return result


def _enumerate_paths(
    start_nodes: Iterable[int],
    neighbor_fn: Callable[[int], List[int]],
    stop_fn: Callable[[List[int]], bool],
    max_depth: int | None,
    max_paths: int | None,
    reverse_output: bool,
) -> List[TracePath]:
    stack: List[TracePath] = [TracePath(nodes=[n]) for n in start_nodes]
    results: List[TracePath] = []

    while stack:
        current = stack.pop()
        path = current.nodes
        if max_paths is not None and len(results) >= max_paths:
            break

        if max_depth is not None and len(path) - 1 >= max_depth:
            results.append(TracePath(nodes=list(reversed(path)) if reverse_output else path, ended_by_cycle=False))
            continue

        neighbors = neighbor_fn(path[-1])
        if not neighbors or stop_fn(path):
            results.append(TracePath(nodes=list(reversed(path)) if reverse_output else path, ended_by_cycle=current.ended_by_cycle))
            continue

        for neighbor in reversed(neighbors):
            if neighbor in path:
                cycle_path = path + [neighbor]
                results.append(
                    TracePath(
                        nodes=list(reversed(cycle_path)) if reverse_output else cycle_path,
                        ended_by_cycle=True,
                    )
                )
                continue
            new_path = TracePath(nodes=path + [neighbor])
            stack.append(new_path)

    results.sort(key=lambda tp: [str(n) for n in tp.nodes])
    return results


def _resolve_roots(entrypoints: List[int], node_ids: Iterable[int], incoming: Dict[int, Set[int]]) -> Set[int]:
    if entrypoints:
        return set(entrypoints)
    roots: Set[int] = set()
    for nid in node_ids:
        if not incoming.get(nid):
            roots.add(nid)
    return roots


def _resolve_leaves(adjacency: Dict[int, Set[int]], node_ids: Iterable[int]) -> Set[int]:
    leaves: Set[int] = set()
    for nid in node_ids:
        if not adjacency.get(nid):
            leaves.add(nid)
    return leaves
