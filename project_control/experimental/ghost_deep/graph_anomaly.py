"""Detect architecture anomalies from import graph topology."""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Set


class GraphAnomalyAnalyzer:
    def __init__(self, graph: Dict[str, Set[str]], metrics: Dict[str, Any]):
        self.graph = {node: set(neighbors) for node, neighbors in sorted(graph.items())}
        self.metrics = metrics
        self.nodes = sorted(self.graph.keys())

    def _strongly_connected_components(self) -> List[List[str]]:
        index = {}
        lowlink = {}
        stack = []
        on_stack = set()
        result: List[List[str]] = []
        current_index = 0

        def strongconnect(node: str):
            nonlocal current_index
            index[node] = current_index
            lowlink[node] = current_index
            current_index += 1
            stack.append(node)
            on_stack.add(node)

            for neighbor in sorted(self.graph.get(node, [])):
                if neighbor not in index:
                    strongconnect(neighbor)
                    lowlink[node] = min(lowlink[node], lowlink[neighbor])
                elif neighbor in on_stack:
                    lowlink[node] = min(lowlink[node], index[neighbor])

            if lowlink[node] == index[node]:
                component = []
                while stack:
                    w = stack.pop()
                    on_stack.remove(w)
                    component.append(w)
                    if w == node:
                        break
                if len(component) > 1:
                    result.append(sorted(component))

        for node in self.nodes:
            if node not in index:
                strongconnect(node)
        return sorted(result)

    def _god_modules(self) -> List[str]:
        avg_out = self.metrics.get("avg_out_degree", 0)
        avg_in = self.metrics.get("avg_in_degree", 0)
        result = []
        ratios = {}
        in_degrees = {node: 0 for node in self.nodes}
        for node in self.nodes:
            for neighbor in self.graph[node]:
                in_degrees[neighbor] = in_degrees.get(neighbor, 0) + 1
        for node in self.nodes:
            out_deg = len(self.graph[node])
            in_deg = in_degrees.get(node, 0)
            out_ratio = out_deg / max(1, avg_out) if avg_out else 0
            in_ratio = in_deg / max(1, avg_in) if avg_in else 0
            ratio = max(out_ratio, in_ratio)
            if out_deg > avg_out * 3 or in_deg > avg_in * 3:
                result.append(node)
                ratios[node] = ratio
        return sorted(result), ratios

    def _dead_clusters(self, reachable: Set[str]) -> List[List[str]]:
        unreachable = sorted(set(self.nodes) - reachable)
        visited = set()
        clusters: List[List[str]] = []

        def neighbors(node: str) -> Set[str]:
            return set(self.graph.get(node, []))

        for node in unreachable:
            if node in visited:
                continue
            component = []
            queue = deque([node])
            while queue:
                current = queue.popleft()
                if current in component:
                    continue
                component.append(current)
                visited.add(current)
                for neighbor in sorted(neighbors(current)):
                    if neighbor in unreachable:
                        queue.append(neighbor)
                for src, targets in self.graph.items():
                    if current in targets and src in unreachable:
                        queue.append(src)
            if len(component) > 1:
                clusters.append(sorted(component))
        return sorted(clusters)

    def _isolated_nodes(self) -> List[str]:
        return sorted([node for node in self.nodes if not self.graph[node] and all(node not in self.graph[src] for src in self.nodes)])

    def _smell_score(self, metrics: Dict[str, Any], cycle_groups: List[List[str]], god_ratios: Dict[str, float]) -> Dict[str, Any]:
        node_count = metrics.get("node_count", 1)
        density = metrics.get("density", 0)
        cycle_ratio = sum(len(group) for group in cycle_groups) / max(1, node_count)
        god_ratio = len(god_ratios) / max(1, node_count)
        unreachable_ratio = metrics.get("unreachable_count", 0) / max(1, node_count)
        score = min(100, 100 * (0.25 * density + 0.25 * cycle_ratio + 0.25 * god_ratio + 0.25 * unreachable_ratio))
        if score <= 25:
            level = "CLEAN"
        elif score <= 50:
            level = "WARNING"
        else:
            level = "CRITICAL"
        return {"smell_score": round(score, 2), "smell_level": level}

    def analyze(self) -> Dict[str, Any]:
        reachable = set(self.metrics.get("reachable_nodes", []))
        cycle_groups = self._strongly_connected_components()
        god_modules, god_ratios = self._god_modules()
        dead_clusters = self._dead_clusters(reachable)
        isolated = self._isolated_nodes()
        smell = self._smell_score(self.metrics, cycle_groups, god_ratios)

        return {
            "cycle_groups": cycle_groups,
            "largest_cycle_size": max((len(group) for group in cycle_groups), default=0),
            "cycle_density_score": len(cycle_groups) / max(1, len(self.nodes)) if self.nodes else 0,
            "god_modules": god_modules,
            "worst_offender": max(god_ratios, key=god_ratios.get) if god_ratios else None,
            "max_degree_ratio": max(god_ratios.values(), default=0),
            "dead_clusters": dead_clusters,
            "total_dead_nodes": sum(len(cluster) for cluster in dead_clusters),
            "isolated_nodes": isolated,
            **smell,
        }
