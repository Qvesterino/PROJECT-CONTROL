"""Composable specifier resolution for JS/TS dependency graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


DEFAULT_JS_EXTENSIONS = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]


@dataclass(frozen=True)
class ResolutionResult:
    resolved_path: Optional[str]
    is_external: bool
    handled: bool


class ResolverStrategy:
    """Strategy interface; returns ResolutionResult. `handled` signals applicability."""

    def resolve(self, from_path: str, specifier: str) -> ResolutionResult:  # pragma: no cover - interface
        raise NotImplementedError


class AliasRelativeStrategy(ResolverStrategy):
    """Resolves alias-prefixed or relative specifiers against known internal paths."""

    def __init__(self, internal_paths: Iterable[str], alias: Dict[str, str], extension_order: Sequence[str] = DEFAULT_JS_EXTENSIONS):
        self.internal_set = set(internal_paths)
        self.alias = {k: v for k, v in alias.items()}
        self.extension_order = list(extension_order) if extension_order else list(DEFAULT_JS_EXTENSIONS)

    def resolve(self, from_path: str, specifier: str) -> ResolutionResult:
        mapped = self._apply_alias(specifier)
        is_relative = specifier.startswith((".", "/"))
        if mapped is None and not is_relative:
            return ResolutionResult(None, False, False)

        base = mapped if mapped is not None else specifier
        base_path = Path(from_path).parent.joinpath(base).as_posix()
        candidate = self._match_internal(base_path)
        if candidate:
            return ResolutionResult(candidate, False, True)
        return ResolutionResult(None, True, True)

    def _apply_alias(self, specifier: str) -> Optional[str]:
        for prefix, target in sorted(self.alias.items(), key=lambda kv: kv[0]):
            if specifier.startswith(prefix):
                remainder = specifier[len(prefix) :]
                return (Path(target) / remainder).as_posix()
        return None

    def _match_internal(self, base_path: str) -> Optional[str]:
        if base_path in self.internal_set:
            return base_path

        root = Path(base_path)
        root_no_suffix = Path(str(root.with_suffix("")))

        candidates = []
        for ext in self.extension_order:
            candidates.append(root_no_suffix.with_suffix(ext).as_posix())
        for ext in self.extension_order:
            candidates.append(root_no_suffix.joinpath("index" + ext).as_posix())

        for candidate in candidates:
            if candidate in self.internal_set:
                return candidate
        return None


class BareExternalStrategy(ResolverStrategy):
    """Marks remaining specifiers as external."""

    def resolve(self, from_path: str, specifier: str) -> ResolutionResult:  # pragma: no cover - trivial
        return ResolutionResult(None, True, True)


class SpecifierResolver:
    """
    Composable resolver orchestrator. Strategies can be extended to support tsconfig paths, webpack, etc.
    """

    def __init__(self, project_root: Path, internal_paths: Iterable[str], alias: Dict[str, str], extension_order: Sequence[str] = DEFAULT_JS_EXTENSIONS):
        self.project_root = project_root
        self.strategies: List[ResolverStrategy] = [
            AliasRelativeStrategy(internal_paths, alias, extension_order=extension_order),
            BareExternalStrategy(),
        ]

    def resolve(self, from_path: str, specifier: str) -> Tuple[Optional[str], bool]:
        """
        Resolve a specifier relative to `from_path`.
        Returns (resolved_path, is_external). resolved_path is posix relative to project root.
        """
        for strategy in self.strategies:
            result = strategy.resolve(from_path, specifier)
            if not result.handled:
                continue
            return result.resolved_path, result.is_external if result.is_external is not None else False
        return None, True

    def register_strategy(self, strategy: ResolverStrategy) -> None:
        """Append a new resolver strategy (used for future tsconfig/webpack/vite support)."""
        self.strategies.insert(-1, strategy)  # keep BareExternalStrategy last


class PythonResolver:
    """Simple Python module resolver that maps modules to files under project root."""

    def __init__(self, project_root: Path, internal_paths: Iterable[str]):
        self.project_root = project_root
        self.internal_set = set(internal_paths)

    def resolve(self, from_path: str, specifier: str) -> Tuple[Optional[str], bool]:
        """
        Resolve Python import specifier to a file path relative to project root when possible.
        Returns (resolved_path, is_external).
        """
        candidates = self._candidate_paths(from_path, specifier)
        for candidate in candidates:
            if candidate in self.internal_set:
                return candidate, False
        return None, True

    def _candidate_paths(self, from_path: str, specifier: str) -> List[str]:
        if not specifier:
            return []

        base_path = Path(from_path).parent
        if specifier.startswith("."):
            prefix_len = len(specifier) - len(specifier.lstrip("."))
            module_part = specifier.lstrip(".")
            for _ in range(prefix_len):
                base_path = base_path.parent
            parts = [p for p in module_part.split(".") if p] if module_part else []
            module_path = base_path.joinpath(*parts)
        else:
            module_path = Path(specifier.replace(".", "/"))

        candidates: List[Path] = []
        candidates.append(module_path.with_suffix(".py"))
        candidates.append(module_path.joinpath("__init__.py"))

        # Normalize to posix relative to project root if possible
        normalized: List[str] = []
        for candidate in candidates:
            try:
                rel = candidate.as_posix()
            except Exception:
                rel = str(candidate).replace("\\", "/")
            normalized.append(rel)
        return normalized
