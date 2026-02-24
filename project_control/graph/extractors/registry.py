"""Extractor registry wired by language configuration."""

from __future__ import annotations

from typing import Dict

from project_control.config.graph_config import GraphConfig
from project_control.graph.extractors.base import BaseExtractor
from project_control.graph.extractors.js_ts import JsTsExtractor
from project_control.graph.extractors.python_ast import PythonAstExtractor


def build_registry(config: GraphConfig) -> Dict[str, BaseExtractor]:
    """
    Map file extension -> extractor based on enabled languages.
    Ext keys are stored with leading dot (e.g., ".ts").
    """
    registry: Dict[str, BaseExtractor] = {}
    languages = config.languages or {}
    for name, body in languages.items():
        if not isinstance(body, dict) or not body.get("enabled", False):
            continue
        include_exts = body.get("include_exts", []) or []
        extractor = _build_extractor_for_language(name)
        if extractor is None:
            continue
        for ext in include_exts:
            if isinstance(ext, str):
                registry[ext] = extractor
    return registry


def _build_extractor_for_language(name: str) -> BaseExtractor | None:
    if name == "js_ts":
        return JsTsExtractor()
    if name == "python":
        return PythonAstExtractor()
    return None
