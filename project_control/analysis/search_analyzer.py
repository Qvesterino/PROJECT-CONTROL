"""Smart search - power-user code search with advanced filters."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Sequence, TypedDict

from project_control.utils.rg_helper import run_rg_json, run_rg_files_only

LOGGER = logging.getLogger(__name__)


class SearchResult(TypedDict):
    """Structured result from smart search."""
    matches: list[dict]
    stats: dict


def smart_search(
    patterns: Sequence[str],
    project_root: str | Path = ".",
    invert: bool = False,
    files_only: bool = False,
    extra_args: list[str] | None = None,
) -> SearchResult:
    """
    Perform power-user search with advanced filtering.

    Args:
        patterns: List of regex patterns to search for.
        project_root: Root directory to search in.
        invert: If True, find files that DO NOT match the patterns.
        files_only: If True, return only file paths (no line details).
        extra_args: Additional ripgrep arguments.

    Returns:
        Structured result with matches and search stats.
    """
    if extra_args is None:
        extra_args = []

    # For invert mode, always use files-only approach
    # because -L doesn't work with JSON output
    if invert:
        matching_files = run_rg_files_only(patterns, extra_args + ["-L"])
        return {
            "matches": [{"file": f} for f in matching_files],
            "stats": {
                "total_matches": len(matching_files),
                "files_only": True,
                "inverted": True,
            },
        }

    if files_only:
        matching_files = run_rg_files_only(patterns, extra_args)
        return {
            "matches": [{"file": f} for f in matching_files],
            "stats": {
                "total_matches": len(matching_files),
                "files_only": True,
                "inverted": False,
            },
        }
    else:
        matches = run_rg_json(patterns, extra_args)
        return {
            "matches": matches,
            "stats": {
                "total_matches": len(matches),
                "files_only": False,
                "inverted": False,
            },
        }
