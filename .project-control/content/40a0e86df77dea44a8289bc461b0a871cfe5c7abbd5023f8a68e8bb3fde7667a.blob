"""Graph metrics and analyses for JS/TS dependency graph."""

from __future__ import annotations

from collections import defaultdict, deque, Counter
from fnmatch import fnmatch
from typing import Dict, List, Set, Tuple

from project_control.config.graph_config import GraphConfig


def compute_metrics(graph: Dict, config: GraphConfig) -> Dict:
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    entrypoints = graph.get("entrypoints", [])

    id_to_path = {node["id"]: node["path"] for node in nodes}
    path_to_id = {node["path"]: node["id"] for node in nodes}

    adjacency: Dict[int, Set[int]] = defaultdict(set)
    incoming: Dict[int, Set[int]] = defaultdict(set)

    external_edge_count = 0
    external_spec_counter: Counter[str] = Counter()
    for edge in edges:
        if edge.get("isExternal"):
            external_edge_count += 1
            external_spec_counter[edge.get("specifier", "")] += 1
        if edge.get("toId") is None:
            continue
        if edge.get("kind") == "dynamic" and not config.treat_dynamic_imports_as_edges:
            continue
        src = edge["fromId"]
        dst = edge["toId"]
        adjacency[src].add(dst)
        incoming[dst].add(src)

    reachable = _reachable(entrypoints, adjacency)
    orphan_candidates = _orphans(id_to_path, reachable, config.orphan_allow_patterns)

    sccs, node_to_component = _tarjan(list(id_to_path.keys()), adjacency)
    component_graph = _build_component_graph(sccs, node_to_component, adjacency)
    component_depth = _longest_path(component_graph, entrypoints, node_to_component)
    depth_map = {id_to_path[node]: component_depth[node_to_component[node]] for node in id_to_path}

    fan_out = {id_to_path[node]: len(adjacency.get(node, set())) for node in id_to_path}
    fan_in = {id_to_path[node]: len(incoming.get(node, set())) for node in id_to_path}

    cycle_groups = [
        sorted([id_to_path[node] for node in component]) for component in sccs if len(component) > 1
    ]
    # self-loop cycles
    for node, neighbors in adjacency.items():
        if node in neighbors:
            cycle_groups.append([id_to_path[node]])
    cycle_groups = sorted(cycle_groups)

    return {
        "totals": {
            "nodeCount": len(nodes),
            "edgeCount": len(edges),
            "externalEdgeCount": external_edge_count,
        },
        "externals": {
            "bySpecifier": dict(sorted(external_spec_counter.items())),
        },
        "fanIn": dict(sorted(fan_in.items())),
        "fanOut": dict(sorted(fan_out.items())),
        "depth": depth_map,
        "cycles": cycle_groups,
        "orphanCandidates": orphan_candidates,
        "entrypoints": [id_to_path[i] for i in entrypoints],
    }


def _reachable(entrypoints: List[int], adjacency: Dict[int, Set[int]]) -> Set[int]:
    seen: Set[int] = set()
    stack: List[int] = list(entrypoints)
    while stack:
        node = stack.pop()
        if node in seen:
            continue
        seen.add(node)
        for neighbor in sorted(adjacency.get(node, set())):
            stack.append(neighbor)
    return seen


def _orphans(id_to_path: Dict[int, str], reachable: Set[int], allow_patterns: List[str]) -> List[Dict[str, str]]:
    orphans: List[Dict[str, str]] = []
    for node_id, path in sorted(id_to_path.items(), key=lambda kv: kv[1]):
        if node_id in reachable:
            continue
        reason = "unreachable"
        if any(fnmatch(path, pattern) for pattern in allow_patterns):
            reason = "allowlisted"
        orphans.append({"path": path, "reason": reason})
    return orphans


def _tarjan(nodes: List[int], adjacency: Dict[int, Set[int]]) -> Tuple[List[Set[int]], Dict[int, int]]:
    """Tarjan SCC; deterministic by sorted iteration."""
    index = 0
    stack: List[int] = []
    on_stack: Set[int] = set()
    indices: Dict[int, int] = {}
    lowlinks: Dict[int, int] = {}
    components: List[Set[int]] = []

    def strongconnect(v: int) -> None:
        nonlocal index
        indices[v] = index
        lowlinks[v] = index
        index += 1
        stack.append(v)
        on_stack.add(v)

        for w in sorted(adjacency.get(v, set())):
            if w not in indices:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])

        if lowlinks[v] == indices[v]:
            component: Set[int] = set()
            while True:
                w = stack.pop()
                on_stack.remove(w)
                component.add(w)
                if w == v:
                    break
            components.append(component)

    for v in sorted(nodes):
        if v not in indices:
            strongconnect(v)

    components.sort(key=lambda c: sorted(c))
    node_to_component = {node: idx for idx, comp in enumerate(components) for node in comp}
    return components, node_to_component


def _build_component_graph(
    components: List[Set[int]],
    node_to_component: Dict[int, int],
    adjacency: Dict[int, Set[int]],
) -> Dict[int, Set[int]]:
    comp_adj: Dict[int, Set[int]] = defaultdict(set)
    for src, neighbors in adjacency.items():
        src_comp = node_to_component[src]
        for dst in neighbors:
            dst_comp = node_to_component[dst]
            if src_comp != dst_comp:
                comp_adj[src_comp].add(dst_comp)
    # ensure keys exist
    for idx in range(len(components)):
        comp_adj.setdefault(idx, set())
    return comp_adj


def _longest_path(comp_graph: Dict[int, Set[int]], entrypoints: List[int], node_to_component: Dict[int, int]) -> Dict[int, int]:
    # entry components
    entry_comps = {node_to_component[ep] for ep in entrypoints if ep in node_to_component}
    indegree = {c: 0 for c in comp_graph}
    for neighbors in comp_graph.values():
        for n in neighbors:
            indegree[n] += 1
    queue = deque([c for c, deg in indegree.items() if deg == 0])
    topo: List[int] = []
    while queue:
        comp = queue.popleft()
        topo.append(comp)
        for neighbor in sorted(comp_graph.get(comp, set())):
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    depth = {comp: 0 for comp in comp_graph}
    for comp in topo:
        if comp in entry_comps:
            depth[comp] = max(depth.get(comp, 0), 0)
        for neighbor in sorted(comp_graph.get(comp, set())):
            depth[neighbor] = max(depth.get(neighbor, 0), depth[comp] + 1)
    return depth
