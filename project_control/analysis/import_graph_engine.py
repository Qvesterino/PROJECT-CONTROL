"""Abstract interface for import graph engines."""

from __future__ import annotations

from typing import Any, Dict, List, Protocol, Set, Tuple

from project_control.core.content_store import ContentStore


class ImportGraphEngine(Protocol):
    def build_graph(
        self,
        snapshot: Dict[str, Any],
        content_store: ContentStore,
        entrypoints: List[str],
        ignore_patterns: List[str],
        entry_modules: List[str] | None = None,
    ) -> Tuple[Set[str], Dict[str, Set[str]]]:
        """
        Returns unreachable snapshot paths for the configured entrypoints.
        Must operate using snapshot data only.
        """
