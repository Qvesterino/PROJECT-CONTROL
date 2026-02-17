"""Entry point policy resolver for the import graph system."""

from __future__ import annotations

import fnmatch
from pathlib import Path
from typing import Any, Dict, List

from project_control.core.content_store import ContentStore


def _path_to_module(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.endswith(".py"):
        normalized = normalized[:-3]
    return normalized.replace("/", ".")


class EntryPointPolicy:
    def __init__(self, snapshot: Dict[str, Any], content_store: ContentStore, config: Dict[str, Any]):
        self.snapshot = snapshot
        self.content_store = content_store
        self.config = config or {}
        self.module_map: Dict[str, str] = {}
        for entry in sorted(snapshot.get("files", []), key=lambda e: e["path"]):
            path = entry["path"]
            if not path.endswith(".py"):
                continue
            self.module_map[_path_to_module(path)] = path

    def resolve(self) -> List[str]:
        explicit = self._explicit_modules()
        globbed = self._glob_modules()
        auto = self._auto_detect_modules() if self._auto_detect_enabled() else []
        resolved = {module for module in explicit + globbed + auto if module in self.module_map}
        normalized = sorted(resolved)
        print("ENTRYPOINTS RAW:", self._raw_entrypoints())
        print("ENTRYPOINTS NORMALIZED:", normalized)
        return normalized

    def _raw_entrypoints(self) -> List[str]:
        raw = self.config.get("entrypoints", [])
        if isinstance(raw, dict):
            explicit = raw.get("explicit", [])
            return explicit
        return raw or []

    def _explicit_modules(self) -> List[str]:
        raw = self._raw_entrypoints()
        return [_path_to_module(path) for path in raw if path.endswith(".py")]

    def _glob_modules(self) -> List[str]:
        raw = self.config.get("entrypoints", {})
        patterns = []
        if isinstance(raw, dict):
            patterns = raw.get("glob", [])
        modules: List[str] = []
        for pattern in patterns:
            normalized_pattern = pattern.replace("\\", "/")
            for module, path in self.module_map.items():
                if fnmatch.fnmatch(path, normalized_pattern):
                    modules.append(module)
        return modules

    def _auto_detect_enabled(self) -> bool:
        raw = self.config.get("entrypoints", {})
        if isinstance(raw, dict):
            return raw.get("auto_detect_main", False)
        return False

    def _auto_detect_modules(self) -> List[str]:
        modules: List[str] = []
        for module, path in self.module_map.items():
            try:
                content = self.content_store.get_text(path)
            except Exception:
                continue
            if 'if __name__ == "__main__":' in content:
                modules.append(module)
        return modules
