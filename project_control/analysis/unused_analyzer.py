"""Unused systems analyzer - finds systems that exist but aren't used."""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TypedDict

from project_control.utils.rg_helper import run_rg_json
from project_control.analysis.dead_analyzer import _should_ignore_file

LOGGER = logging.getLogger(__name__)


class UnusedSystemsResult(TypedDict):
    """Structured result from unused systems analysis."""
    unused_systems: list[dict]
    stats: dict


def analyze_unused_systems(
    project_root: str | Path = ".",
    extensions: list[str] | None = None,
    name_patterns: list[str] | None = None,
) -> UnusedSystemsResult:
    """
    Analyze project for unused systems (Manager, Controller, System files).

    Args:
        project_root: Root directory to analyze.
        extensions: File extensions to include.
        name_patterns: Patterns to identify system files (default: System, Manager, Controller).

    Returns:
        Structured result with unused systems and stats.
    """
    root = Path(project_root)
    if extensions is None:
        extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]

    if name_patterns is None:
        name_patterns = ["System", "Manager", "Controller", "Service", "Handler"]

    unused: list[dict] = []
    total_systems = 0

    # Find files matching system naming patterns
    system_files = []
    for ext in extensions:
        for pattern in name_patterns:
            system_files.extend(root.rglob(f"*{pattern}*{ext}"))

    total_systems = len(system_files)

    for file_path in system_files:
        # Skip ignored files (test, config, venv, etc.)
        if _should_ignore_file(file_path):
            continue

        # Extract system name (file name without extension and common suffixes)
        file_name = file_path.stem

        # Try different variations of the system name
        search_terms = [file_name]

        # Also search for class/module name variations
        # e.g., "UserManager" -> "UserManager", "userManager"
        camel_case = re.findall(r'[A-Z][a-z0-9]*', file_name)
        if camel_case:
            snake_case = '_'.join(camel_case).lower()
            search_terms.append(snake_case)

        # Search for usage
        matches = run_rg_json(
            search_terms,
            extra_args=["--type", "py", "--type", "js", "--type", "ts"],
        )

        # Filter out matches from the file itself (self-reference)
        external_matches = [
            m for m in matches
            if Path(m["file"]) != file_path
        ]

        # Check if file is imported/instantiated/used elsewhere
        # A system is "unused" if it's not referenced elsewhere
        usage_count = len(external_matches)

        if usage_count == 0:
            unused.append({
                "file": str(file_path.relative_to(root)),
                "system_name": file_name,
                "usage": 0,
                "reason": "No references found",
            })

    return {
        "unused_systems": sorted(unused, key=lambda x: x["file"]),
        "stats": {
            "total_systems": total_systems,
            "unused_count": len(unused),
        },
    }
