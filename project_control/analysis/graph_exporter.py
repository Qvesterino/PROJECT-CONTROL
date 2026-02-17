"""Export import graph structures into DOT and Mermaid formats."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Set


def _sanitize_node(name: str) -> str:
    return name.replace("/", "_").replace(".", "_").replace("-", "_")


def export_dot(graph: Dict[str, Set[str]], output_path: Path) -> None:
    if not graph:
        return
    lines = ["digraph ImportGraph {"]
    for node in sorted(graph):
        neighbors = sorted(graph[node])
        if neighbors:
            for neighbor in neighbors:
                lines.append(f'    "{node}" -> "{neighbor}";')
        else:
            lines.append(f'    "{node}";')
    lines.append("}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def export_mermaid(graph: Dict[str, Set[str]], output_path: Path) -> None:
    if not graph:
        return
    lines = ["graph TD"]
    for node in sorted(graph):
        neighbors = sorted(graph[node])
        sanitized_node = _sanitize_node(node)
        if neighbors:
            for neighbor in neighbors:
                lines.append(f"{sanitized_node} --> {_sanitize_node(neighbor)}")
        else:
            lines.append(f"{sanitized_node}")
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
