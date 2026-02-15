"""Minimal ASCII tree renderer for path lists."""

from __future__ import annotations

from typing import List, Dict


def render_tree(paths: List[str]) -> str:
    """Render an ASCII tree from slash-delimited paths."""

    def insert_path(tree: Dict[str, Dict], parts: List[str]) -> None:
        node = tree
        for part in parts:
            node = node.setdefault(part, {})

    tree: Dict[str, Dict] = {}
    for path in paths:
        normalized = path.replace("\\", "/")
        components = [segment for segment in normalized.split("/") if segment]
        if not components:
            continue
        insert_path(tree, components)

    lines: List[str] = []

    def walk(subtree: Dict[str, Dict], prefix: str) -> None:
        items = sorted(subtree.items())
        for index, (name, child) in enumerate(items):
            is_last = index == len(items) - 1
            connector = "└── " if is_last else "├── "
            lines.append(f"{prefix}{connector}{name}{'/' if child else ''}")
            if child:
                extension = "    " if is_last else "│   "
                walk(child, prefix + extension)

    root_items = sorted(tree.items())
    for name, subtree in root_items:
        lines.append(f"{name}{'/' if subtree else ''}")
        if subtree:
            walk(subtree, "")

    return "\n".join(lines)
