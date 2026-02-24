"""Regex-based import extractor for JS/TS sources."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List


@dataclass(frozen=True)
class ImportRecord:
    specifier: str
    kind: str  # "esm" | "cjs" | "dynamic"


class ImportExtractor:
    # Matches:
    #   import x from 'spec';
    #   export * from "spec";
    #   require('spec');
    #   import('spec');
    _ESM_RE = re.compile(
        r"""(?:import\s+(?:[^;]*?\s+from\s+)?|export\s+(?:[^;]*?\s+from\s+))(?P<q>["'])(?P<spec>[^"']+)(?P=q)""",
        re.MULTILINE,
    )
    _CJS_RE = re.compile(r"""require\(\s*(?P<q>["'])(?P<spec>[^"']+)(?P=q)\s*\)""", re.MULTILINE)
    _DYNAMIC_RE = re.compile(r"""import\(\s*(?P<q>["'])(?P<spec>[^"']+)(?P=q)\s*\)""", re.MULTILINE)

    def extract(self, content: str) -> List[ImportRecord]:
        """Return deterministic list of imports found in content."""
        records: List[ImportRecord] = []

        def add(matches: Iterable[re.Match], kind: str) -> None:
            for match in matches:
                spec = match.group("spec")
                if spec:
                    records.append(ImportRecord(specifier=spec, kind=kind))

        add(self._ESM_RE.finditer(content), "esm")
        add(self._CJS_RE.finditer(content), "cjs")
        add(self._DYNAMIC_RE.finditer(content), "dynamic")

        # Deduplicate deterministically
        dedup = {(r.kind, r.specifier) for r in records}
        sorted_records = [ImportRecord(spec, kind) for kind, spec in sorted(dedup, key=lambda t: (t[1], t[0]))]
        return sorted_records
