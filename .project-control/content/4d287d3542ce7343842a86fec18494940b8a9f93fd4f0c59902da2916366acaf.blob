"""Shared data transfer objects for core workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional


class ResultValidationError(Exception):
    """Raised when a result DTO breaks expected invariants."""


    def __init__(self, message: str):
        super().__init__(message)


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise ResultValidationError(message)


def _require_keys(mapping: Dict[str, Any], keys: list[str], label: str) -> None:
    for key in keys:
        _ensure(key in mapping, f"{label} missing key: {key}")


def _is_dict_or_none(value: Any) -> bool:
    return value is None or isinstance(value, dict)


@dataclass
class GhostAnalysisResult:
    graph: Dict[str, Any]
    metrics: Dict[str, Any]
    anomalies: Dict[str, Any]
    drift: Optional[Dict[str, Any]]
    trend: Optional[Dict[str, Any]]

    def as_dict(self) -> Dict[str, Any]:
        return {
            "graph": self.graph,
            "metrics": self.metrics,
            "anomalies": self.anomalies,
            "drift": self.drift,
            "trend": self.trend,
        }

    def validate(self) -> None:
        _ensure(isinstance(self.graph, dict), "graph must be dict")
        _ensure(isinstance(self.metrics, dict), "metrics must be dict")
        _ensure(isinstance(self.anomalies, dict), "anomalies must be dict")
        _ensure(_is_dict_or_none(self.drift), "drift must be dict or None")
        _ensure(_is_dict_or_none(self.trend), "trend must be dict or None")

        _require_keys(self.graph, ["nodes", "edges"], "graph")
        _require_keys(self.metrics, ["node_count"], "metrics")
