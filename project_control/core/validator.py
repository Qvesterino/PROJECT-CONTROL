"""Validation layer for PROJECT_CONTROL data structures."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from project_control.core.error_handler import (
    CorruptedDataError,
    ValidationError,
    Validator,
)

logger = logging.getLogger(__name__)


# ── Validation Results ─────────────────────────────────────────────────────

@dataclass(frozen=True)
class ValidationResult:
    """Result of a validation operation."""
    is_valid: bool
    errors: List[str]
    warnings: List[str]

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def create_validation_result(
    is_valid: bool,
    errors: Optional[List[str]] = None,
    warnings: Optional[List[str]] = None,
) -> ValidationResult:
    """Create a ValidationResult with optional lists."""
    return ValidationResult(
        is_valid=is_valid,
        errors=errors or [],
        warnings=warnings or [],
    )


# ── Snapshot Validation ────────────────────────────────────────────────────

def validate_snapshot(snapshot: Dict[str, Any], snapshot_path: Path) -> ValidationResult:
    """
    Validate snapshot structure and integrity.

    Args:
        snapshot: Snapshot dictionary to validate
        snapshot_path: Path to snapshot.json file (for error messages)

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Required top-level keys
    required_keys = ["snapshot_version", "snapshot_id", "file_count", "files"]
    for key in required_keys:
        if key not in snapshot:
            errors.append(f"Missing required key: '{key}'")

    # Validate snapshot_version
    if "snapshot_version" in snapshot:
        version = snapshot["snapshot_version"]
        if not isinstance(version, int) or version < 1:
            errors.append(f"Invalid snapshot_version: {version}")

    # Validate snapshot_id
    if "snapshot_id" in snapshot:
        snapshot_id = snapshot["snapshot_id"]
        if not isinstance(snapshot_id, str) or len(snapshot_id) != 64:
            errors.append(f"Invalid snapshot_id: must be 64-character hex string")

    # Validate file_count
    if "file_count" in snapshot:
        file_count = snapshot["file_count"]
        if not isinstance(file_count, int) or file_count < 0:
            errors.append(f"Invalid file_count: {file_count}")

    # Validate files array
    if "files" in snapshot:
        files = snapshot["files"]
        if not isinstance(files, list):
            errors.append(f"'files' must be a list, got {type(files).__name__}")
        else:
            # Validate each file entry
            for idx, file_entry in enumerate(files):
                entry_errors = _validate_file_entry(file_entry, idx)
                errors.extend(entry_errors)

            # Check if file_count matches actual count
            if "file_count" in snapshot and file_count != len(files):
                warnings.append(
                    f"file_count mismatch: declared {file_count}, actual {len(files)}"
                )

    # Validate content directory
    content_dir = snapshot_path.parent / "content"
    if not content_dir.exists():
        warnings.append(f"Content directory missing: {content_dir}")
    else:
        # Check if all referenced blobs exist
        if "files" in snapshot and isinstance(snapshot["files"], list):
            missing_blobs = 0
            for file_entry in snapshot["files"]:
                if isinstance(file_entry, dict) and "sha256" in file_entry:
                    sha256 = file_entry["sha256"]
                    blob_path = content_dir / f"{sha256}.blob"
                    if not blob_path.exists():
                        missing_blobs += 1

            if missing_blobs > 0:
                warnings.append(f"{missing_blobs} content blobs missing from {content_dir}")

    is_valid = len(errors) == 0
    return create_validation_result(is_valid, errors, warnings)


def _validate_file_entry(entry: Any, index: int) -> List[str]:
    """Validate a single file entry."""
    errors: List[str] = []

    if not isinstance(entry, dict):
        errors.append(f"File entry #{index} is not a dict: {type(entry).__name__}")
        return errors

    # Required keys for file entry
    required_keys = ["path", "size", "modified", "sha256"]
    for key in required_keys:
        if key not in entry:
            errors.append(f"File entry #{index} missing required key: '{key}'")

    # Validate path
    if "path" in entry:
        path = entry["path"]
        if not isinstance(path, str):
            errors.append(f"File entry #{index} 'path' must be a string, got {type(path).__name__}")
        elif not path:
            errors.append(f"File entry #{index} 'path' cannot be empty")

    # Validate size
    if "size" in entry:
        size = entry["size"]
        if not isinstance(size, int) or size < 0:
            errors.append(f"File entry #{index} 'size' must be a non-negative integer, got {size}")

    # Validate modified (ISO 8601 timestamp)
    if "modified" in entry:
        modified = entry["modified"]
        if not isinstance(modified, str):
            errors.append(f"File entry #{index} 'modified' must be a string, got {type(modified).__name__}")
        else:
            # Basic ISO 8601 check (YYYY-MM-DDTHH:MM:SS)
            if not modified or "T" not in modified:
                errors.append(f"File entry #{index} 'modified' must be ISO 8601 format, got: {modified}")

    # Validate sha256
    if "sha256" in entry:
        sha256 = entry["sha256"]
        if not isinstance(sha256, str) or len(sha256) != 64:
            errors.append(f"File entry #{index} 'sha256' must be 64-character hex string, got: {sha256}")
        else:
            # Check if it's valid hex
            try:
                int(sha256, 16)
            except ValueError:
                errors.append(f"File entry #{index} 'sha256' is not valid hex: {sha256}")

    return errors


# ── Graph Validation ───────────────────────────────────────────────────────

def validate_graph(graph: Dict[str, Any], graph_path: Path) -> ValidationResult:
    """
    Validate graph structure and consistency.

    Args:
        graph: Graph dictionary to validate
        graph_path: Path to graph.snapshot.json file

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Required top-level keys
    required_keys = ["meta", "nodes", "edges", "entrypoints"]
    for key in required_keys:
        if key not in graph:
            errors.append(f"Missing required key: '{key}'")

    # Validate meta
    if "meta" in graph:
        meta = graph["meta"]
        if not isinstance(meta, dict):
            errors.append(f"'meta' must be a dict, got {type(meta).__name__}")
        else:
            # Required meta keys
            meta_required = ["projectRoot", "createdAt", "toolVersion", "configHash", "snapshotHash"]
            for key in meta_required:
                if key not in meta:
                    warnings.append(f"Meta missing recommended key: '{key}'")

    # Validate nodes
    if "nodes" in graph:
        nodes = graph["nodes"]
        if not isinstance(nodes, list):
            errors.append(f"'nodes' must be a list, got {type(nodes).__name__}")
        else:
            node_ids = set()
            for idx, node in enumerate(nodes):
                node_errors = _validate_graph_node(node, idx)
                errors.extend(node_errors)
                if isinstance(node, dict) and "id" in node:
                    node_id = node["id"]
                    if node_id in node_ids:
                        errors.append(f"Duplicate node ID: {node_id}")
                    node_ids.add(node_id)

    # Validate edges
    if "edges" in graph:
        edges = graph["edges"]
        if not isinstance(edges, list):
            errors.append(f"'edges' must be a list, got {type(edges).__name__}")
        else:
            if "nodes" in graph and isinstance(graph["nodes"], list):
                node_ids = {node.get("id") for node in graph["nodes"] if isinstance(node, dict)}
                for idx, edge in enumerate(edges):
                    edge_errors = _validate_graph_edge(edge, idx, node_ids)
                    errors.extend(edge_errors)

    # Validate entrypoints
    if "entrypoints" in graph:
        entrypoints = graph["entrypoints"]
        if not isinstance(list(entrypoints), list):
            errors.append(f"'entrypoints' must be a list, got {type(entrypoints).__name__}")

    is_valid = len(errors) == 0
    return create_validation_result(is_valid, errors, warnings)


def _validate_graph_node(node: Any, index: int) -> List[str]:
    """Validate a single graph node."""
    errors: List[str] = []

    if not isinstance(node, dict):
        errors.append(f"Node #{index} is not a dict: {type(node).__name__}")
        return errors

    # Required keys for node
    required_keys = ["id", "path", "ext"]
    for key in required_keys:
        if key not in node:
            errors.append(f"Node #{index} missing required key: '{key}'")

    # Validate id
    if "id" in node:
        node_id = node["id"]
        if not isinstance(node_id, int) or node_id < 1:
            errors.append(f"Node #{index} 'id' must be a positive integer, got: {node_id}")

    # Validate path
    if "path" in node:
        path = node["path"]
        if not isinstance(path, str) or not path:
            errors.append(f"Node #{index} 'path' must be a non-empty string")

    # Validate ext
    if "ext" in node:
        ext = node["ext"]
        if not isinstance(ext, str):
            errors.append(f"Node #{index} 'ext' must be a string, got {type(ext).__name__}")

    return errors


def _validate_graph_edge(edge: Any, index: int, valid_node_ids: set[int]) -> List[str]:
    """Validate a single graph edge."""
    errors: List[str] = []

    if not isinstance(edge, dict):
        errors.append(f"Edge #{index} is not a dict: {type(edge).__name__}")
        return errors

    # Required keys for edge
    required_keys = ["from", "to"]
    for key in required_keys:
        if key not in edge:
            errors.append(f"Edge #{index} missing required key: '{key}'")

    # Validate from and to node IDs
    for key in ["from", "to"]:
        if key in edge:
            node_id = edge[key]
            if not isinstance(node_id, int):
                errors.append(f"Edge #{index} '{key}' must be an integer, got: {type(node_id).__name__}")
            elif node_id not in valid_node_ids:
                errors.append(f"Edge #{index} '{key}' references non-existent node ID: {node_id}")

    return errors


# ── Configuration Validation ───────────────────────────────────────────────

def validate_patterns_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate patterns.yaml configuration.

    Args:
        config: Configuration dictionary

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Expected keys with their types
    expected_keys = {
        "writers": list,
        "entrypoints": list,
        "ignore_dirs": list,
        "extensions": list,
    }

    for key, expected_type in expected_keys.items():
        if key in config:
            value = config[key]
            if not isinstance(value, expected_type):
                errors.append(f"'{key}' must be {expected_type.__name__}, got {type(value).__name__}")

    # Validate extensions start with '.'
    if "extensions" in config and isinstance(config["extensions"], list):
        for ext in config["extensions"]:
            if not isinstance(ext, str):
                errors.append(f"Extension must be string, got {type(ext).__name__}: {ext}")
            elif not ext.startswith("."):
                warnings.append(f"Extension should start with '.': {ext}")

    is_valid = len(errors) == 0
    return create_validation_result(is_valid, errors, warnings)


def validate_graph_config(config: Dict[str, Any]) -> ValidationResult:
    """
    Validate graph.config.yaml configuration.

    Args:
        config: Configuration dictionary

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Required keys
    required_keys = ["include_globs", "exclude_globs", "entrypoints", "languages"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required key: '{key}'")

    # Validate lists
    list_keys = ["include_globs", "exclude_globs", "entrypoints"]
    for key in list_keys:
        if key in config and not isinstance(config[key], list):
            errors.append(f"'{key}' must be a list, got {type(config[key]).__name__}")

    # Validate languages structure
    if "languages" in config:
        languages = config["languages"]
        if not isinstance(languages, dict):
            errors.append(f"'languages' must be a dict, got {type(languages).__name__}")
        else:
            for lang_name, lang_config in languages.items():
                if not isinstance(lang_config, dict):
                    errors.append(f"Language '{lang_name}' config must be a dict")
                    continue

                if "enabled" in lang_config:
                    enabled = lang_config["enabled"]
                    if not isinstance(enabled, bool):
                        errors.append(f"Language '{lang_name}' 'enabled' must be bool")

                if "include_exts" in lang_config:
                    include_exts = lang_config["include_exts"]
                    if not isinstance(include_exts, list):
                        errors.append(f"Language '{lang_name}' 'include_exts' must be a list")

    is_valid = len(errors) == 0
    return create_validation_result(is_valid, errors, warnings)


# ── UI State Validation ────────────────────────────────────────────────────

def validate_ui_state(state: Dict[str, Any]) -> ValidationResult:
    """
    Validate UI state (config.json).

    Args:
        state: UI state dictionary

    Returns:
        ValidationResult with errors and warnings
    """
    errors: List[str] = []
    warnings: List[str] = []

    # Expected keys with validation
    validations = {
        "project_mode": ("js_ts", "python", "mixed"),
        "graph_profile": ("pragmatic", "strict"),
        "trace_direction": ("inbound", "outbound", "both"),
    }

    for key, valid_values in validations.items():
        if key in state:
            value = state[key]
            if value not in valid_values:
                errors.append(f"'{key}' must be one of {valid_values}, got: {value}")

    # Validate trace_depth
    if "trace_depth" in state:
        depth = state["trace_depth"]
        if not isinstance(depth, int) or depth < 1:
            errors.append(f"'trace_depth' must be positive integer, got: {depth}")

    # Validate trace_all_paths
    if "trace_all_paths" in state:
        all_paths = state["trace_all_paths"]
        if not isinstance(all_paths, bool):
            errors.append(f"'trace_all_paths' must be bool, got: {type(all_paths).__name__}")

    is_valid = len(errors) == 0
    return create_validation_result(is_valid, errors, warnings)


# ── Convenient Wrapper Functions ──────────────────────────────────────────

def validate_and_raise_snapshot(snapshot_path: Path) -> Dict[str, Any]:
    """
    Load and validate snapshot, raising exception if invalid.

    Args:
        snapshot_path: Path to snapshot.json

    Returns:
        Validated snapshot dictionary

    Raises:
        FileNotFoundError: If snapshot file doesn't exist
        CorruptedDataError: If snapshot is invalid
    """
    Validator.require_file_exists(snapshot_path, "Snapshot file")
    Validator.validate_json_loadable(snapshot_path, "Snapshot file")

    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    result = validate_snapshot(snapshot, snapshot_path)

    if not result.is_valid:
        raise CorruptedDataError(
            f"Snapshot validation failed: {snapshot_path}",
            details=f"Errors: {'; '.join(result.errors)}"
        )

    if result.has_warnings():
        logger.warning(f"Snapshot warnings: {'; '.join(result.warnings)}")

    return snapshot


def validate_and_raise_graph(graph_path: Path) -> Dict[str, Any]:
    """
    Load and validate graph, raising exception if invalid.

    Args:
        graph_path: Path to graph.snapshot.json

    Returns:
        Validated graph dictionary

    Raises:
        FileNotFoundError: If graph file doesn't exist
        CorruptedDataError: If graph is invalid
    """
    Validator.require_file_exists(graph_path, "Graph file")
    Validator.validate_json_loadable(graph_path, "Graph file")

    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    result = validate_graph(graph, graph_path)

    if not result.is_valid:
        raise CorruptedDataError(
            f"Graph validation failed: {graph_path}",
            details=f"Errors: {'; '.join(result.errors)}"
        )

    if result.has_warnings():
        logger.warning(f"Graph warnings: {'; '.join(result.warnings)}")

    return graph
