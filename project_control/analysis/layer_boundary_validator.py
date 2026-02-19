"""Static guard to keep analysis layer free of higher-layer imports."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path
from typing import List

FORBIDDEN_PREFIXES = (
    "project_control.core",
    "project_control.persistence",
    "project_control.cli",
    "project_control.usecases",
    "project_control.pc",
)


@dataclass(frozen=True)
class LayerBoundaryViolation:
    file: Path
    line: int
    import_path: str


def _iter_python_files(root: Path) -> List[Path]:
    return sorted(root.rglob("*.py"))


def _extract_import_path(node: ast.AST) -> str:
    if isinstance(node, ast.Import):
        names = [alias.name for alias in node.names]
        return ", ".join(names)
    if isinstance(node, ast.ImportFrom):
        return node.module or ""
    return ""


def validate_boundaries() -> List[LayerBoundaryViolation]:
    violations: List[LayerBoundaryViolation] = []
    analysis_dir = Path(__file__).parent

    for file_path in _iter_python_files(analysis_dir):
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                import_path = _extract_import_path(node)
                if not import_path:
                    continue
                for forbidden in FORBIDDEN_PREFIXES:
                    if import_path.startswith(forbidden):
                        line_no = getattr(node, "lineno", 1)
                        violations.append(
                            LayerBoundaryViolation(
                                file=file_path,
                                line=line_no,
                                import_path=import_path,
                            )
                        )
                        break
    return violations
