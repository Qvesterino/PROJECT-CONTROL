"""Composable specifier resolution for JS/TS dependency graph."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple


EXTENSION_ORDER = [".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"]


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

    def __init__(self, internal_paths: Iterable[str], alias: Dict[str, str]):
        self.internal_set = set(internal_paths)
        self.alias = {k: v for k, v in alias.items()}

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
        for ext in EXTENSION_ORDER:
            candidates.append(root_no_suffix.with_suffix(ext).as_posix())
        for ext in EXTENSION_ORDER:
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

    def __init__(self, project_root: Path, internal_paths: Iterable[str], alias: Dict[str, str]):
        self.project_root = project_root
        self.strategies: List[ResolverStrategy] = [
            AliasRelativeStrategy(internal_paths, alias),
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
