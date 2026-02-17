"""Python import graph engine using the content store."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, Any, Iterable, List, Set

from project_control.analysis.import_graph_engine import ImportGraphEngine
from project_control.core.content_store import ContentStore


def _path_to_module(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


def _parse_imports(source: str) -> Iterable[str]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return ()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield alias.name
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            for alias in node.names:
                if base:
                    yield f"{base}.{alias.name}"
                else:
                    yield f"{'.' * node.level}{alias.name}"


def _resolve_relative(module: str, current: str) -> str | None:
    dots = len(module) - len(module.lstrip("."))
    target = module.lstrip(".")
    parts = current.split(".")
    base_parts = parts[: max(0, len(parts) - dots)]
    prefix = ".".join(base_parts)
    return f"{prefix}.{target}".strip(".") if target else prefix


class PythonImportGraphEngine(ImportGraphEngine):
    def build_graph(
        self,
        snapshot: Dict[str, Any],
        content_store: ContentStore,
        entrypoints: List[str],
        ignore_patterns: List[str],
        entry_modules: List[str] | None = None,
    ) -> Set[str]:
        files = snapshot.get("files", [])
        module_map: Dict[str, str] = {}
        for entry in sorted(files, key=lambda e: e["path"]):
            path = entry["path"]
            if not path.endswith(".py"):
                continue
            module_map[_path_to_module(path)] = path

        graph: Dict[str, Set[str]] = {module: set() for module in module_map}
        for module in sorted(module_map):
            path = module_map[module]
            try:
                source = content_store.get_text(path)
            except Exception:
                continue
            for imp in sorted(_parse_imports(source)):
                resolved_module = (
                    _resolve_relative(imp, module) if imp.startswith(".") else imp
                )
                if resolved_module in module_map:
                    graph[module].add(resolved_module)

        if entry_modules is None:
            entry_modules = [
                _path_to_module(ep) for ep in entrypoints if ep.endswith(".py")
            ]
            entry_modules = [mod for mod in entry_modules if mod in module_map]
        all_paths = set(module_map.keys())

        reachable: Set[str] = set()

        def dfs(node: str) -> None:
            if node in reachable or node not in graph:
                return
            reachable.add(node)
            for neighbor in sorted(graph[node]):
                dfs(neighbor)

        normalized_eps = sorted(set(entry_modules))
        print("ENTRYPOINTS RAW:", entrypoints)
        print("MODULE MAP SAMPLE:", list(module_map.keys())[:5])
        print("ENTRYPOINTS NORMALIZED:", normalized_eps)

        for entry in normalized_eps:
            if entry in graph:
                dfs(entry)

        print("PY FILE COUNT:", len(all_paths))
        print(
            "GRAPH EDGE COUNT:",
            sum(len(neighbors) for neighbors in graph.values()),
        )
        print("ENTRYPOINTS:", entry_modules)

        return (
            {
                module_map[module]
                for module in module_map
                if module not in reachable
            },
            graph,
        )
