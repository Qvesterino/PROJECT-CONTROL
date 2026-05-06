"""Pattern configuration loader for PROJECT CONTROL."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Union

import yaml

LOGGER = logging.getLogger(__name__)


ARTIFACT_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "older_than_days": 30,
    "min_score": 8,
    "extensions": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"],
    "suspicious_dirs": [
        "screenshots",
        "screenshot",
        "test-results",
        "playwright-report",
        "tmp",
        "temp",
        "debug",
        "captures",
        "exports",
    ],
    "safe_dirs": [
        "public/assets",
        "src/assets",
        "assets/icons",
        "assets/textures",
        "public/favicon",
    ],
    "likely_asset_resolutions": [
        "16x16",
        "32x32",
        "64x64",
        "128x128",
        "256x256",
        "512x512",
        "1024x1024",
    ],
    "likely_screenshot_resolutions": [
        "1920x1080",
        "1366x768",
        "1440x900",
        "1280x720",
        "1536x864",
    ],
}


AUDIT_RETENTION_DEFAULTS: Dict[str, Any] = {
    "enabled": True,
    "older_than_days": 45,
    "min_score": 8,
    "keep_latest_per_family": 3,
    "extensions": [".md", ".txt", ".json", ".html", ".csv"],
    "suspicious_dirs": [
        ".project-control/exports",
        ".project-control/out",
        "docs/audits",
        "docs/reports",
        "reports",
        "audit",
        "audits",
        "checklists",
        "exports",
    ],
    "safe_dirs": [
        "docs/specs",
        "docs/architecture",
        "docs/reference",
        "docs/adr",
    ],
    "family_keywords": {
        "ghost": ["ghost", "orphan", "legacy", "semantic"],
        "graph": ["graph", "dependency", "trace", "metrics"],
        "ui_verification": ["ui_verification", "ui-verify", "ui_verify"],
        "vfx": ["vfx", "contract_audit"],
        "checklist": ["checklist"],
        "artifacts": ["artifact", "delete_candidates"],
        "generic_audit": ["audit", "report", "review"],
    },
}


_DEFAULT_PATTERNS: Dict[str, Any] = {
    "writers": ["scale", "emissive", "opacity", "position"],
    "entrypoints": ["main.js", "index.ts"],
    "ignore_dirs": [".git", ".project-control", "node_modules", "__pycache__"],
    "extensions": [".py", ".js", ".ts", ".md", ".txt"],
    "artifacts": ARTIFACT_DEFAULTS,
    "audit_retention": AUDIT_RETENTION_DEFAULTS,
}


def _copy_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    return value


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = _copy_value(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = _copy_value(value)
    return merged


def _default_patterns() -> Dict[str, Any]:
    """Return a fresh copy of default patterns so callers can mutate safely."""
    return _copy_value(_DEFAULT_PATTERNS)


def get_default_patterns() -> Dict[str, Any]:
    """Return the current default patterns structure."""
    return _default_patterns()


def get_scan_extensions(patterns: Dict[str, Any]) -> list[str]:
    """Return the effective extension list used by scan."""
    extensions = list(patterns.get("extensions", []))
    artifacts = patterns.get("artifacts", {})
    if isinstance(artifacts, dict) and artifacts.get("enabled", True):
        for extension in artifacts.get("extensions", []):
            if extension not in extensions:
                extensions.append(extension)
    audit_retention = patterns.get("audit_retention", {})
    if isinstance(audit_retention, dict) and audit_retention.get("enabled", True):
        for extension in audit_retention.get("extensions", []):
            if extension not in extensions:
                extensions.append(extension)
    return extensions


def load_patterns(project_root: Union[str, Path]) -> Dict[str, Any]:
    """
    Read the patterns.yaml stored in `project_root/.project-control`.

    Returns defaults when the file is missing or invalid and merges any loaded
    values on top so callers don't have to spread defaults everywhere.
    """
    config_path = Path(project_root) / ".project-control" / "patterns.yaml"

    if not config_path.is_file():
        return _default_patterns()

    try:
        with config_path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
    except (yaml.YAMLError, OSError) as error:
        LOGGER.debug("Failed to load patterns from %s: %s", config_path, error)
        return _default_patterns()

    return _merge_dicts(_default_patterns(), data)
