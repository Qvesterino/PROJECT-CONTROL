"""Self-architecture validation for PROJECT_CONTROL using import graph inspection."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple

PROJECT_PREFIX = "project_control"

LAYER_ORDER = [
    "analysis",
    "usecases",
    "core",
    "persistence",
    "cli",
]

# Allowed downstream dependencies per layer
ALLOWED_DEPS = {
    "analysis": set(),
    "usecases": {"analysis"},
    "core": {"analysis", "usecases"},
    "persistence": {"analysis", "core"},
    "cli": {"analysis", "usecases", "core"},
}


@dataclass(frozen=True)
class LayerViolation:
    source: str
    target: str
    file: Path
    line: int
    rule: str


def _path_to_module(path: Path, root: Path) -> str:
    rel = path.relative_to(root)
    return f"{PROJECT_PREFIX}." + ".".join(rel.with_suffix("").parts)


def _resolve_relative(module: str, current: str) -> str:
    dots = len(module) - len(module.lstrip("."))
    target = module.lstrip(".")
    parts = current.split(".")
    base_parts = parts[: max(0, len(parts) - dots)]
    prefix = ".".join(base_parts)
    return f"{prefix}.{target}".strip(".") if target else prefix


def _iter_imports(source: str, current_module: str) -> Iterable[Tuple[str, int]]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    imports: List[Tuple[str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append((alias.name, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            base = "." * node.level + (node.module or "")
            for alias in node.names:
                name = f"{base}.{alias.name}" if base else f"{'.' * node.level}{alias.name}"
                if name.startswith("."):
                    resolved = _resolve_relative(name, current_module)
                else:
                    resolved = name
                imports.append((resolved, node.lineno))
    return imports


def _layer_for_module(module: str) -> str | None:
    parts = module.split(".")
    if len(parts) < 2:
        return None
    if parts[0] != PROJECT_PREFIX:
        return None
    if parts[1] == "pc":
        return "cli"
    candidate = parts[1]
    return candidate if candidate in LAYER_ORDER else None


def validate_architecture() -> List[LayerViolation]:
    root = Path(__file__).resolve().parents[1]
    violations: List[LayerViolation] = []

    py_files = sorted(root.rglob("*.py"))
    module_map: Dict[str, Path] = {}
    for file_path in py_files:
        module_map[_path_to_module(file_path, root)] = file_path

    for module, file_path in sorted(module_map.items()):
        source = file_path.read_text(encoding="utf-8")
        for target, line in _iter_imports(source, module):
            if not target.startswith(PROJECT_PREFIX):
                continue
            src_layer = _layer_for_module(module)
            tgt_layer = _layer_for_module(target)
            if not src_layer or not tgt_layer:
                continue
            if src_layer == tgt_layer:
                continue
            allowed = ALLOWED_DEPS.get(src_layer, set())
            if tgt_layer not in allowed:
                violations.append(
                    LayerViolation(
                        source=module,
                        target=target,
                        file=file_path,
                        line=line,
                        rule=f"{src_layer} layer cannot depend on {tgt_layer}",
                    )
                )
    return violations
