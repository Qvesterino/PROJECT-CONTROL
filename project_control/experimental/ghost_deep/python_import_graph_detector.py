"""Snapshot-only analyzer for Python import reachability."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from project_control.core.content_store import ContentStore
from project_control.core.debug import debug_print


def _path_to_module(path: str) -> str:
    normalized = Path(path).with_suffix("").as_posix()
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
            module = node.module or ""
            level = node.level
            if module:
                name = ".".join(["" for _ in range(level)] + [module])
            else:
                name = ".".join(["" for _ in range(level)])
            for alias in node.names:
                if module:
                    yield f"{'.' * level}{module}.{alias.name}"
                else:
                    yield f"{'.' * level}{alias.name}"


def _resolve_relative(module: str, current: str) -> str | None:
    dots = len(module) - len(module.lstrip("."))
    target = module.lstrip(".")
    parts = current.split(".")
    if dots:
        base = ".".join(parts[: max(0, len(parts) - dots)])
    else:
        base = current
    return f"{base}.{target}".strip(".") if target else base


def detect_python_import_graph_orphans(
    snapshot: Dict[str, Any],
    patterns: Dict[str, Any],
    content_store: ContentStore,
    debug: bool = False,
) -> List[str]:
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
            if imp.startswith("."):
                resolved = _resolve_relative(imp, module)
            else:
                resolved = imp
            if resolved in module_map:
                graph[module].add(resolved)

    entry_points = [
        _path_to_module(ep) for ep in patterns.get("entrypoints", []) if ep.endswith(".py")
    ]

    debug_print(debug, "PY MODULE COUNT:", len(module_map))
    debug_print(debug, "PY GRAPH NODES:", len(graph))
    debug_print(debug, "PY ENTRYPOINTS:", entry_points)

    reachable: Set[str] = set()

    def dfs(node: str) -> None:
        if node in reachable:
            return
        reachable.add(node)
        for neighbor in sorted(graph.get(node, [])):
            dfs(neighbor)

    for entry in sorted(entry_points):
        if entry in graph:
            dfs(entry)

    orphans = sorted(
        module_map[module] for module in module_map if module not in reachable
    )
    return orphans
