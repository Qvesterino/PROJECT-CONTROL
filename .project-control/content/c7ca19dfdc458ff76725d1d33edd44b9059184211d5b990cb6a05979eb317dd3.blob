"""Base extractor protocol and data structures for import detection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol


@dataclass(frozen=True)
class ImportOccurrence:
    specifier: str
    kind: str  # "esm" | "cjs" | "dynamic" | "py_import" | "py_from"
    line: int
    lineText: str


class BaseExtractor(Protocol):
    """Interface for language-specific import extractors."""

    def extract(self, path: str, content_text: str) -> List[ImportOccurrence]:  # pragma: no cover - interface
        raise NotImplementedError
