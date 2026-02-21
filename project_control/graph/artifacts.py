"""Artifact writers for graph snapshot, metrics, and human report."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple


def ensure_output_dir(project_root: Path) -> Path:
    out_dir = project_root / ".project-control" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def write_artifacts(project_root: Path, graph: Dict, metrics: Dict) -> Tuple[Path, Path, Path]:
    out_dir = ensure_output_dir(project_root)
    snapshot_path = out_dir / "graph.snapshot.json"
    metrics_path = out_dir / "graph.metrics.json"
    report_path = out_dir / "graph.report.md"

    snapshot_path.write_text(json.dumps(_sort_json(graph), indent=2), encoding="utf-8")
    metrics_path.write_text(json.dumps(_sort_json(metrics), indent=2), encoding="utf-8")
    report_path.write_text(_render_report(graph, metrics), encoding="utf-8")
    return snapshot_path, metrics_path, report_path


def write_report_only(project_root: Path, graph: Dict, metrics: Dict) -> Path:
    out_dir = ensure_output_dir(project_root)
    report_path = out_dir / "graph.report.md"
    report_path.write_text(_render_report(graph, metrics), encoding="utf-8")
    return report_path


def _sort_json(obj):
    if isinstance(obj, dict):
        return {k: _sort_json(obj[k]) for k in sorted(obj)}
    if isinstance(obj, list):
        return [_sort_json(v) for v in obj]
    return obj


def _render_report(graph: Dict, metrics: Dict) -> str:
    lines: List[str] = []
    totals = metrics.get("totals", {})
    fan_in = metrics.get("fanIn", {})
    fan_out = metrics.get("fanOut", {})
    depth = metrics.get("depth", {})
    cycles = metrics.get("cycles", [])
    orphans = metrics.get("orphanCandidates", [])

    lines.append("# Dependency Graph Report\n")
    lines.append("## Summary")
    lines.append(f"- Nodes: {totals.get('nodeCount', 0)}")
    lines.append(f"- Edges: {totals.get('edgeCount', 0)} (external: {totals.get('externalEdgeCount', 0)})")
    lines.append(f"- Entry points: {len(metrics.get('entrypoints', []))}")
    lines.append(f"- Cycles: {len(cycles)}")
    lines.append(f"- Orphan candidates: {len(orphans)}\n")

    lines.append("## External Dependencies")
    externals = metrics.get("externals", {}).get("bySpecifier", {})
    if externals:
        for spec, count in sorted(externals.items(), key=lambda item: (-item[1], item[0]))[:10]:
            lines.append(f"- {spec}: {count}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Top Fan-In")
    for path, count in _top_k(fan_in):
        lines.append(f"- {path}: {count}")
    if not fan_in:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Top Fan-Out")
    for path, count in _top_k(fan_out):
        lines.append(f"- {path}: {count}")
    if not fan_out:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Deepest Files")
    for path, value in _top_k(depth):
        lines.append(f"- {path}: depth {value}")
    if not depth:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Cycles")
    if cycles:
        for group in cycles:
            joined = ", ".join(group)
            lines.append(f"- {joined}")
    else:
        lines.append("- (none)")
    lines.append("")

    lines.append("## Orphan Candidates")
    if orphans:
        for entry in sorted(orphans, key=lambda o: o["path"]):
            lines.append(f"- {entry['path']} ({entry['reason']})")
    else:
        lines.append("- (none)")
    lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def _top_k(mapping: Dict[str, int], k: int = 10) -> List[Tuple[str, int]]:
    return sorted(mapping.items(), key=lambda item: (-item[1], item[0]))[:k]
