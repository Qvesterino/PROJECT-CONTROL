"""CLI handlers for graph build/report/trace commands."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

from project_control.config.graph_config import GraphConfig, load_graph_config, hash_config
from project_control.graph.builder import GraphBuilder, compute_snapshot_hash
from project_control.graph.metrics import compute_metrics
from project_control.graph.artifacts import write_artifacts, ensure_output_dir
from project_control.graph.trace import trace_paths
from project_control.core.content_store import ContentStore
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR
from project_control.core.snapshot_service import load_snapshot
from project_control.utils.fs_helpers import run_rg


def _load_snapshot_or_fail(project_root: Path):
    try:
        return load_snapshot(project_root)
    except FileNotFoundError:
        print("Snapshot not found. Run 'pc scan' first.")
        return None


def graph_build(project_root: Path, config_path: Optional[Path]) -> int:
    snapshot = _load_snapshot_or_fail(project_root)
    if snapshot is None:
        return EXIT_VALIDATION_ERROR

    config = load_graph_config(project_root, config_path)
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    content_store = ContentStore(snapshot, snapshot_path)

    builder = GraphBuilder(project_root, snapshot, content_store, config)
    graph = builder.build()
    metrics = compute_metrics(graph, config)

    snapshot_path_out, metrics_path_out, report_path = write_artifacts(project_root, graph, metrics)
    print(f"Graph snapshot written to: {snapshot_path_out}")
    print(f"Graph metrics written to:  {metrics_path_out}")
    print(f"Graph report written to:   {report_path}")
    return EXIT_OK


def graph_report(project_root: Path, config_path: Optional[Path]) -> int:
    # Report regenerates artifacts to remain deterministic
    return graph_build(project_root, config_path)


def graph_trace(
    project_root: Path,
    config_path: Optional[Path],
    target: str,
    direction: str,
    max_depth: Optional[int],
    max_paths: Optional[int],
    show_line: bool,
    config_override: Optional[GraphConfig] = None,
) -> int:
    snapshot = _load_snapshot_or_fail(project_root)
    if snapshot is None:
        return EXIT_VALIDATION_ERROR

    config = config_override if config_override is not None else load_graph_config(project_root, config_path)
    graph = _load_or_build_graph(project_root, snapshot, config)
    if graph is None:
        return EXIT_VALIDATION_ERROR

    id_to_path = {n["id"]: n["path"] for n in graph.get("nodes", [])}
    target_id, symbol_defs = _resolve_target_node(project_root, target, id_to_path)
    if target_id is None:
        print(f"Target '{target}' not found in graph nodes.")
        return EXIT_VALIDATION_ERROR

    traces = trace_paths(graph, target_id, direction=direction, max_depth=max_depth, max_paths=max_paths)
    output_lines = _render_trace(graph, traces, target, target_id, symbol_defs, show_line)

    for line in output_lines:
        print(line)

    out_dir = ensure_output_dir(project_root)
    trace_path = out_dir / "graph.trace.txt"
    trace_path.write_text("\n".join(output_lines), encoding="utf-8")
    return EXIT_OK


def _load_or_build_graph(project_root: Path, snapshot: Dict, config: GraphConfig) -> Optional[Dict]:
    graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"
    current_hash = compute_snapshot_hash(snapshot)
    config_hash = hash_config(config)

    if graph_path.exists():
        try:
            data = json.loads(graph_path.read_text(encoding="utf-8"))
            meta = data.get("meta", {})
            if meta.get("snapshotHash") == current_hash and meta.get("configHash") == config_hash:
                return data
        except Exception:
            pass

    content_store = ContentStore(snapshot, project_root / ".project-control" / "snapshot.json")
    builder = GraphBuilder(project_root, snapshot, content_store, config)
    graph = builder.build()
    metrics = compute_metrics(graph, config)
    write_artifacts(project_root, graph, metrics)
    return graph


def _resolve_target_node(project_root: Path, target: str, id_to_path: Dict[int, str]) -> tuple[Optional[int], List[Dict]]:
    symbol_defs: List[Dict] = []
    normalized_target = Path(target)

    # Path resolution
    candidates: List[str] = []
    if normalized_target.is_absolute():
        try:
            candidates.append(str(normalized_target.relative_to(project_root).as_posix()))
        except ValueError:
            pass
    candidates.append(normalized_target.as_posix())
    candidates.append(normalized_target.as_posix().lstrip("./"))

    for cand in candidates:
        for node_id, path in id_to_path.items():
            if path == cand:
                return node_id, symbol_defs

    # Symbol resolution via ripgrep
    symbol_defs = _find_symbol_definitions(target, limit=3)
    for match in symbol_defs:
        path = match.get("path")
        if path:
            for node_id, node_path in id_to_path.items():
                if node_path == path:
                    return node_id, symbol_defs
    return None, symbol_defs


def _find_symbol_definitions(symbol: str, limit: int = 3) -> List[Dict]:
    raw = run_rg(symbol)
    results: List[Dict] = []
    for line in raw.splitlines():
        if len(results) >= limit:
            break
        parts = line.split(":", 2)
        if len(parts) < 3:
            continue
        path, lineno, snippet = parts[0], parts[1], parts[2]
        try:
            line_no_int = int(lineno)
        except ValueError:
            line_no_int = 0
        results.append({"path": path.replace("\\", "/"), "line": line_no_int, "lineText": snippet})
    return results


def _edges_by_pair(edges: List[Dict]) -> Dict[tuple, List[Dict]]:
    mapping: Dict[tuple, List[Dict]] = {}
    for edge in edges:
        key = (edge.get("fromId"), edge.get("toId"))
        mapping.setdefault(key, []).append(edge)
    for key in mapping:
        mapping[key].sort(key=lambda e: (e.get("line", 0), e.get("specifier", "")))
    return mapping


def _render_trace(graph: Dict, traces: Dict[str, List], target_label: str, target_id: int, symbol_defs: List[Dict], show_line: bool) -> List[str]:
    id_to_path = {n["id"]: n["path"] for n in graph.get("nodes", [])}
    edges_map = _edges_by_pair(graph.get("edges", []))

    lines: List[str] = []
    lines.append(f"Graph trace for {target_label} -> {id_to_path.get(target_id, '(unknown)')}")
    if symbol_defs:
        lines.append("Definition candidates:")
        for match in symbol_defs:
            lines.append(f"- {match.get('path')}:{match.get('line', '?')} {match.get('lineText', '').strip()}")

    if not traces:
        lines.append("No paths found.")
        return lines

    for direction in ["inbound", "outbound"]:
        if direction not in traces:
            continue
        paths = traces[direction]
        header = "Inbound paths (roots -> target)" if direction == "inbound" else "Outbound paths (target -> leaves)"
        lines.append(header + ":")
        if not paths:
            lines.append("  (none)")
            continue
        for idx, path_obj in enumerate(paths, start=1):
            node_ids = getattr(path_obj, "nodes", path_obj)
            cycle = getattr(path_obj, "ended_by_cycle", False)
            label = " -> ".join(id_to_path.get(n, str(n)) for n in node_ids)
            if cycle:
                label += " (cycle)"
            lines.append(f"  Path {idx}: {label}")
            if show_line and len(node_ids) > 1:
                for a, b in zip(node_ids, node_ids[1:]):
                    edge_list = edges_map.get((a, b), [])
                    edge = edge_list[0] if edge_list else {}
                    line_no = edge.get("line")
                    text = edge.get("lineText", "")
                    lines.append(f"    {id_to_path.get(a, a)}:{line_no or '?'} {text.strip()}")
    return lines
