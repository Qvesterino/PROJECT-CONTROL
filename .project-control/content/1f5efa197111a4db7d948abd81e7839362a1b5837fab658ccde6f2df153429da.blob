"""Compute deterministic structural metrics for import graphs."""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Set


class GraphMetrics:
    def __init__(self, graph: Dict[str, Set[str]], entry_modules: List[str]):
        self.graph = {node: set(neighbors) for node, neighbors in sorted(graph.items())}
        self.entry_modules = sorted(entry_modules)

    def _undirected_neighbors(self, node: str) -> Set[str]:
        neighbors = set(self.graph.get(node, []))
        for src, targets in self.graph.items():
            if node in targets:
                neighbors.add(src)
        return neighbors

    def _reachable_nodes(self) -> Set[str]:
        reachable = set()
        for entry in self.entry_modules:
            if entry not in self.graph:
                continue
            stack = [entry]
            while stack:
                current = stack.pop()
                if current in reachable:
                    continue
                reachable.add(current)
                for neighbor in sorted(self.graph.get(current, [])):
                    stack.append(neighbor)
        return reachable

    def _weak_components(self) -> List[Set[str]]:
        visited = set()
        components: List[Set[str]] = []
        for node in self.graph:
            if node in visited:
                continue
            component = set()
            queue = deque([node])
            while queue:
                current = queue.popleft()
                if current in component:
                    continue
                component.add(current)
                for neighbor in sorted(self._undirected_neighbors(current)):
                    queue.append(neighbor)
            visited.update(component)
            components.append(component)
        return components

    def _has_cycle(self) -> int:
        visited: Set[str] = set()
        stack: Set[str] = set()

        def dfs(node: str) -> int:
            if node in stack:
                return 1
            if node in visited:
                return 0
            visited.add(node)
            stack.add(node)
            count = 0
            for neighbor in sorted(self.graph.get(node, [])):
                count += dfs(neighbor)
            stack.remove(node)
            return count

        total = 0
        for node in sorted(self.graph):
            total += dfs(node)
        return total

    def compute(self) -> Dict[str, Any]:
        node_list = sorted(self.graph.keys())
        node_count = len(node_list)
        edge_count = sum(len(self.graph[node]) for node in node_list)
        reachable = self._reachable_nodes()
        unreachable_count = node_count - len(reachable)
        if node_count < 2:
            density = 0.0
        else:
            max_possible_edges = node_count * (node_count - 1)
            if max_possible_edges <= 0:
                density = 0.0
            else:
                density = edge_count / max_possible_edges
            density = max(0.0, min(1.0, density))
        out_degrees = [len(self.graph[node]) for node in node_list]
        in_degrees = {node: 0 for node in node_list}
        for node in node_list:
            for neighbor in self.graph[node]:
                if neighbor in in_degrees:
                    in_degrees[neighbor] += 1
        components = self._weak_components()
        largest_component_size = max((len(c) for c in components), default=0)
        cycle_count = self._has_cycle()
        root_nodes = sorted([node for node, deg in in_degrees.items() if deg == 0])
        leaf_nodes = sorted([node for node in node_list if not self.graph[node]])

        return {
            "node_count": node_count,
            "edge_count": edge_count,
            "reachable_count": len(reachable),
            "unreachable_count": unreachable_count,
            "density": density,
            "avg_out_degree": sum(out_degrees) / max(1, node_count),
            "avg_in_degree": sum(in_degrees.values()) / max(1, node_count),
            "max_out_degree": max(out_degrees, default=0),
            "max_in_degree": max(in_degrees.values(), default=0),
            "weakly_connected_components_count": len(components),
            "largest_component_size": largest_component_size,
            "is_dag": cycle_count == 0,
            "cycle_count": cycle_count,
            "root_nodes": root_nodes,
            "leaf_nodes": leaf_nodes,
            "entry_modules": self.entry_modules,
            "reachable_nodes": sorted(reachable),
            "unreachable_nodes": sorted(set(node_list) - reachable),
        }
