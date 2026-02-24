"""Line-oriented JS/TS import extractor (fast, regex-based)."""

from __future__ import annotations

import re
from typing import List

from project_control.graph.extractors.base import BaseExtractor, ImportOccurrence


class JsTsExtractor(BaseExtractor):
    # Patterns kept simple for speed; anchored per-line for determinism.
    _ESM_RE = re.compile(
        r"""^\s*(?:import|export)\s+(?:[^;]*?\s+from\s+)?(?P<q>["'])(?P<spec>[^"']+)(?P=q)""",
        re.MULTILINE,
    )
    _CJS_RE = re.compile(r"""require\(\s*(?P<q>["'])(?P<spec>[^"']+)(?P=q)\s*\)""")
    _DYNAMIC_RE = re.compile(r"""import\(\s*(?P<q>["'])(?P<spec>[^"']+)(?P=q)\s*\)""")

    def extract(self, path: str, content_text: str) -> List[ImportOccurrence]:
        occurrences: List[ImportOccurrence] = []
        for idx, line in enumerate(content_text.splitlines(), start=1):
            occurrences.extend(self._collect_matches(line, idx))

        occurrences.sort(key=lambda occ: (occ.line, occ.specifier, occ.kind))
        return occurrences

    def _collect_matches(self, line: str, line_no: int) -> List[ImportOccurrence]:
        found: List[ImportOccurrence] = []
        for match in self._ESM_RE.finditer(line):
            spec = match.group("spec")
            if spec:
                found.append(ImportOccurrence(specifier=spec, kind="esm", line=line_no, lineText=line))
        for match in self._CJS_RE.finditer(line):
            spec = match.group("spec")
            if spec:
                found.append(ImportOccurrence(specifier=spec, kind="cjs", line=line_no, lineText=line))
        for match in self._DYNAMIC_RE.finditer(line):
            spec = match.group("spec")
            if spec:
                found.append(ImportOccurrence(specifier=spec, kind="dynamic", line=line_no, lineText=line))
        return found
