"""Patterns analyzer - detects suspicious or forbidden code patterns."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

import yaml

from project_control.utils.rg_helper import run_rg_json

LOGGER = logging.getLogger(__name__)


class PatternsResult(TypedDict):
    """Structured result from patterns analysis."""
    patterns: dict[str, dict]
    stats: dict


def analyze_patterns(
    project_root: str | Path = ".",
    patterns_file: str | Path | None = None,
) -> PatternsResult:
    """
    Analyze project for suspicious or forbidden code patterns.

    Args:
        project_root: Root directory to analyze.
        patterns_file: Path to patterns YAML file.
                       Defaults to .project-control/patterns.yaml.

    Returns:
        Structured result with pattern matches grouped by pattern name.
    """
    root = Path(project_root)

    if patterns_file is None:
        patterns_file = root / ".project-control" / "patterns.yaml"
    else:
        patterns_file = Path(patterns_file)

    # Load patterns config
    if not patterns_file.exists():
        LOGGER.warning(f"Patterns file not found: {patterns_file}")
        return {
            "patterns": {},
            "stats": {
                "total_patterns": 0,
                "total_matches": 0,
            },
        }

    with open(patterns_file, encoding="utf-8") as f:
        config = yaml.safe_load(f) or {}

    patterns_config = config.get("patterns", {})

    results: dict[str, dict] = {}
    total_matches = 0

    for pattern_name, pattern_terms in patterns_config.items():
        if not isinstance(pattern_terms, list):
            LOGGER.warning(f"Pattern '{pattern_name}' is not a list, skipping")
            continue

        if not pattern_terms:
            continue

        # Search for all pattern terms
        matches = run_rg_json(
            pattern_terms,
            extra_args=["--type", "py", "--type", "js", "--type", "ts"],
        )

        if matches:
            # Group matches by file
            by_file: dict[str, list[dict]] = {}
            for match in matches:
                file_path = match["file"]
                if file_path not in by_file:
                    by_file[file_path] = []
                by_file[file_path].append({
                    "line": match["line"],
                    "text": match["text"],
                    "file": file_path,
                })

            results[pattern_name] = {
                "matches": [],
            }

            # Flatten matches
            for file_matches in by_file.values():
                results[pattern_name]["matches"].extend(file_matches)

            total_matches += len(results[pattern_name]["matches"])

    return {
        "patterns": results,
        "stats": {
            "total_patterns": len(patterns_config),
            "matched_patterns": len(results),
            "total_matches": total_matches,
        },
    }
