"""Ripgrep wrapper with structured JSON output parsing."""

from __future__ import annotations

import json
import logging
import subprocess
from typing import Sequence, TypedDict

LOGGER = logging.getLogger(__name__)


class RgMatch(TypedDict, total=False):
    """Structured ripgrep match result."""
    type: str
    path: dict[str, str] | str
    lines: dict[str, str]
    line_number: int | None
    absolute_offset: int | None
    submatches: list[dict]


def run_rg_json(
    patterns: Sequence[str],
    extra_args: Sequence[str] | None = None,
) -> list[dict]:
    """
    Execute ripgrep with JSON output and return structured matches.

    Args:
        patterns: List of regex patterns to search for (supports multi-pattern via -e).
        extra_args: Additional command-line arguments forwarded to rg.

    Returns:
        List of parsed JSON match dictionaries. Each contains at least:
        - path: str (file path)
        - line_number: int (match line number)
        - text: str (matching line text)
    """
    cmd = ["rg", "--json", "--line-number", "--no-heading"]

    for pattern in patterns:
        cmd.extend(["-e", pattern])

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if not result.stdout:
            return []

        matches = []
        for line in result.stdout.strip().split("\n"):
            try:
                data = json.loads(line)
                if data.get("type") == "match":
                    match_data = data.get("data", {})
                    path = match_data.get("path", {})
                    if isinstance(path, dict):
                        path_text = path.get("text", "")
                    else:
                        path_text = str(path)

                    lines = match_data.get("lines", {})
                    text = lines.get("text", "").strip()

                    line_number = match_data.get("line_number")
                    if line_number is None:
                        line_number = 0

                    matches.append({
                        "file": path_text,
                        "line": line_number,
                        "text": text,
                        "raw": data,
                    })
            except json.JSONDecodeError as e:
                LOGGER.warning(f"Failed to parse ripgrep JSON: {e}")
                continue

        return matches

    except FileNotFoundError:
        LOGGER.warning("ripgrep (rg) not found in PATH.")
        return []


def run_rg_files_only(
    patterns: Sequence[str],
    extra_args: Sequence[str] | None = None,
) -> list[str]:
    """
    Execute ripgrep and return only file paths (no line details).

    Args:
        patterns: List of regex patterns to search for.
        extra_args: Additional command-line arguments forwarded to rg.

    Returns:
        List of unique file paths containing matches.
    """
    cmd = ["rg", "--files-with-matches"]

    for pattern in patterns:
        cmd.extend(["-e", pattern])

    if extra_args:
        cmd.extend(extra_args)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
        )
        if not result.stdout:
            return []

        # Parse file paths (each line is a file path)
        files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return sorted(set(files))

    except FileNotFoundError:
        LOGGER.warning("ripgrep (rg) not found in PATH.")
        return []
