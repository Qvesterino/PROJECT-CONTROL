"""Python import extractor based on ast for accuracy."""

from __future__ import annotations

import ast
from typing import List

from project_control.graph.extractors.base import BaseExtractor, ImportOccurrence


class PythonAstExtractor(BaseExtractor):
    def extract(self, path: str, content_text: str) -> List[ImportOccurrence]:
        lines = content_text.splitlines()
        try:
            tree = ast.parse(content_text)
        except SyntaxError:
            return []

        occurrences: List[ImportOccurrence] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    spec = alias.name
                    occurrences.append(
                        ImportOccurrence(
                            specifier=spec,
                            kind="py_import",
                            line=getattr(node, "lineno", 1),
                            lineText=self._safe_line(lines, getattr(node, "lineno", 1)),
                        )
                    )
            elif isinstance(node, ast.ImportFrom):
                prefix = "." * (node.level or 0)
                module = node.module or ""
                spec = f"{prefix}{module}" if module or prefix else ""
                if spec:
                    occurrences.append(
                        ImportOccurrence(
                            specifier=spec,
                            kind="py_from",
                            line=getattr(node, "lineno", 1),
                            lineText=self._safe_line(lines, getattr(node, "lineno", 1)),
                        )
                    )

        occurrences.sort(key=lambda occ: (occ.line, occ.specifier, occ.kind))
        return occurrences

    @staticmethod
    def _safe_line(lines: List[str], lineno: int) -> str:
        if 1 <= lineno <= len(lines):
            return lines[lineno - 1]
        return ""
