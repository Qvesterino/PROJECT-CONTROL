"""Graph builder that uses snapshot + content store to produce deterministic structures."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List
import importlib.metadata

from fnmatch import fnmatch

from project_control.config.graph_config import GraphConfig, hash_config
from project_control.graph.extractors.registry import build_registry
from project_control.graph.resolver import DEFAULT_JS_EXTENSIONS, PythonResolver, SpecifierResolver
from project_control.core.content_store import ContentStore


class GraphBuilder:
    def __init__(self, project_root: Path, snapshot: Dict, content_store: ContentStore, config: GraphConfig):
        self.project_root = project_root
        self.snapshot = snapshot
        self.content_store = content_store
        self.config = config
        self.extractor_registry = build_registry(config)

    def build(self) -> Dict:
        nodes = self._collect_nodes()
        path_to_id = {node["path"]: node["id"] for node in nodes}

        resolver = SpecifierResolver(self.project_root, path_to_id.keys(), self.config.alias, extension_order=self.config.languages.get("js_ts", {}).get("include_exts", DEFAULT_JS_EXTENSIONS))
        py_resolver = PythonResolver(self.project_root, path_to_id.keys())
        edges = self._collect_edges(nodes, path_to_id, resolver, py_resolver)

        entrypoints = self._resolve_entrypoints(path_to_id, edges)

        meta = {
            "projectRoot": str(self.project_root.resolve().as_posix()),
            "createdAt": datetime.now(timezone.utc).isoformat(),
            "toolVersion": _tool_version(),
            "configHash": hash_config(self.config),
            "snapshotHash": compute_snapshot_hash(self.snapshot),
        }

        graph = {
            "meta": meta,
            "nodes": nodes,
            "edges": edges,
            "entrypoints": entrypoints,
        }
        return graph

    def _collect_nodes(self) -> List[Dict]:
        include = self.config.include_globs
        exclude = self.config.exclude_globs
        allowed_exts = set(self.config.enabled_extensions())
        result: List[Dict] = []

        for entry in sorted(self.snapshot.get("files", []), key=lambda e: Path(e["path"]).as_posix()):
            path_posix = Path(entry["path"]).as_posix()
            if not any(fnmatch(path_posix, pattern) for pattern in include):
                continue
            if any(fnmatch(path_posix, pattern) for pattern in exclude):
                continue
            ext = Path(path_posix).suffix
            if allowed_exts and ext not in allowed_exts:
                continue
            result.append(
                {
                    "path": path_posix,
                    "ext": ext,
                    "sizeBytes": entry.get("size", 0),
                }
            )

        result.sort(key=lambda n: n["path"])
        for idx, node in enumerate(result, start=1):
            node["id"] = idx
        return result

    def _collect_edges(
        self,
        nodes: List[Dict],
        path_to_id: Dict[str, int],
        resolver: SpecifierResolver,
        py_resolver: PythonResolver,
    ) -> List[Dict]:
        edges: List[Dict] = []
        node_paths = [n["path"] for n in nodes]
        extractor_by_ext = self.extractor_registry
        js_exts = set(self.config.languages.get("js_ts", {}).get("include_exts", []))
        py_exts = set(self.config.languages.get("python", {}).get("include_exts", []))

        for path in node_paths:
            ext = Path(path).suffix
            extractor = extractor_by_ext.get(ext)
            if extractor is None:
                continue
            try:
                content = self.content_store.get_text(path)
            except Exception:
                continue
            records = extractor.extract(path, content)
            from_id = path_to_id[path]
            for record in records:
                if ext in py_exts:
                    resolved_path, is_external = py_resolver.resolve(path, record.specifier)
                else:
                    resolved_path, is_external = resolver.resolve(path, record.specifier)
                to_id = path_to_id.get(resolved_path) if resolved_path else None
                edge = {
                    "fromId": from_id,
                    "toId": to_id,
                    "specifier": record.specifier,
                    "kind": record.kind,
                    "line": record.line,
                    "lineText": record.lineText,
                    "isExternal": is_external or to_id is None,
                    "isDynamic": record.kind == "dynamic",
                    "resolvedPath": resolved_path if resolved_path else None,
                }
                edges.append(edge)

        id_to_path = {node["id"]: node["path"] for node in nodes}
        edges.sort(
            key=lambda e: (
                id_to_path.get(e["fromId"], ""),
                id_to_path.get(e["toId"], "") if e["toId"] else e["specifier"],
                e.get("kind", ""),
                e.get("line", 0),
                e["specifier"],
            )
        )
        return edges

    def _resolve_entrypoints(self, path_to_id: Dict[str, int], edges: List[Dict]) -> List[int]:
        """Resolve entrypoints; if none configured, use all nodes with zero fan-in."""
        if self.config.entrypoints:
            ids: List[int] = []
            for raw in self.config.entrypoints:
                candidate = Path(raw).as_posix()
                if candidate in path_to_id:
                    ids.append(path_to_id[candidate])
            return sorted(set(ids))

        # No explicit entrypoints: derive from zero fan-in.
        indegree = {node_id: 0 for node_id in path_to_id.values()}
        for edge in edges:
            to_id = edge.get("toId")
            if to_id is None:
                continue
            if edge.get("isDynamic") and not self.config.treat_dynamic_imports_as_edges:
                continue
            indegree[to_id] = indegree.get(to_id, 0) + 1
        return sorted(node_id for node_id, deg in indegree.items() if deg == 0)


def _tool_version() -> str | None:
    try:
        return importlib.metadata.version("project_control")
    except importlib.metadata.PackageNotFoundError:
        return None


def compute_snapshot_hash(snapshot: Dict) -> str:
    """Compute deterministic hash from snapshot file paths + sha256 values."""
    import hashlib

    files = snapshot.get("files", [])
    concatenated = "".join(
        f"{entry.get('path','')}{entry.get('sha256','')}" for entry in sorted(files, key=lambda e: e.get("path", ""))
    )
    return hashlib.sha256(concatenated.encode("utf-8")).hexdigest()
