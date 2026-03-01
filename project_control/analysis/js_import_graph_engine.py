"""DEPRECATED/UNUSED: Legacy JavaScript/TypeScript import graph engine."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Set

from project_control.analysis.import_graph_engine import ImportGraphEngine
from project_control.core.content_store import ContentStore
from project_control.core.debug import debug_print

EXTENSIONS = [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]


IMPORT_RE = re.compile(
    r"""(?:import\s+(?:[\w{}\s*,]+)\s+from\s+|import\s+)(["'])(.+?)\1|require\(\s*(["'])(.+?)\3\s*\)"""
)


def _norm_path(path: str) -> str:
    return Path(path).as_posix()


def _resolve_relative(path: str, specifier: str, all_paths: Set[str]) -> str | None:
    base_dir = Path(path).parent
    candidate_base = base_dir.joinpath(specifier).as_posix()
    candidates = {candidate_base}
    root = Path(candidate_base)
    root_no_suffix = str(root.with_suffix(""))

    for ext in EXTENSIONS:
        candidates.add(f"{root_no_suffix}{ext}")
        candidates.add(f"{root_no_suffix}/index{ext}")

    for candidate in sorted(candidates):
        normalized = Path(candidate).as_posix()
        if normalized in all_paths:
            return normalized
    return None


def _parse_imports(content: str) -> Iterable[str]:
    for match in IMPORT_RE.finditer(content):
        spec = match.group(2) or match.group(4)
        if spec:
            yield spec


class JSImportGraphEngine(ImportGraphEngine):
    def build_graph(
        self,
        snapshot: Dict[str, Any],
        content_store: ContentStore,
        entrypoints: List[str],
        ignore_patterns: List[str],
        debug: bool = False,
    ) -> Set[str]:
        files = snapshot.get("files", [])
        js_files = sorted(
            _norm_path(f["path"])
            for f in files
            if _norm_path(f["path"]).endswith(tuple(EXTENSIONS))
        )
        graph: Dict[str, Set[str]] = {path: set() for path in js_files}
        debug_print(debug, "JS FILE COUNT:", len(js_files))

        for path in js_files:
            try:
                content = content_store.get_text(path)
            except Exception:
                continue
            for spec in sorted(_parse_imports(content)):
                if not spec.startswith("."):
                    continue
                resolved = _resolve_relative(path, spec, set(js_files))
                if resolved:
                    graph[path].add(resolved)

        entry_paths = [
            _norm_path(ep)
            for ep in entrypoints
            if _norm_path(ep).endswith(tuple(EXTENSIONS))
        ]
        debug_print(debug, "JS ENTRYPOINTS:", entry_paths)

        reachable: Set[str] = set()

        def dfs(node: str) -> None:
            if node in reachable:
                return
            reachable.add(node)
            for neighbor in sorted(graph.get(node, [])):
                dfs(neighbor)

        for entry in sorted(entry_paths):
            dfs(entry)

        return (
            {path for path in js_files if path not in reachable},
            graph,
        )
