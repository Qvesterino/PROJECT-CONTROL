"""Ripgrep wrapper with structured JSON output parsing."""

from __future__ import annotations

import json
import logging
import re
import subprocess
from pathlib import Path
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


def _parse_rg_type_filters(extra_args: Sequence[str] | None) -> list[str]:
    if not extra_args:
        return []

    types: list[str] = []
    iterator = iter(extra_args)
    for arg in iterator:
        if arg == "--type" and (next_arg := next(iterator, None)):
            types.append(next_arg if next_arg.startswith(".") else f".{next_arg}")
    return sorted(set(types))


def _python_search(
    patterns: Sequence[str],
    extra_args: Sequence[str] | None = None,
    cwd: str | Path | None = None,
) -> list[dict]:
    type_filters = _parse_rg_type_filters(extra_args)
    root = Path(cwd).resolve() if cwd is not None else Path.cwd()
    matches: list[dict] = []

    regexes = [re.compile(pattern) for pattern in patterns]
    file_paths = []

    if type_filters:
        for ext in type_filters:
            file_paths.extend(root.rglob(f"*{ext}"))
    else:
        file_paths.extend([p for p in root.rglob("*") if p.is_file()])

    for file_path in sorted(set(file_paths)):
        try:
            text = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue

        for line_number, line in enumerate(text.splitlines(), start=1):
            for regex in regexes:
                if regex.search(line):
                    matches.append({
                        "file": file_path.relative_to(root).as_posix(),
                        "line": line_number,
                        "text": line.strip(),
                        "raw": {},
                    })
                    break
    return matches


def _python_files_with_matches(
    patterns: Sequence[str],
    extra_args: Sequence[str] | None = None,
    cwd: str | Path | None = None,
) -> list[str]:
    matches = _python_search(patterns, extra_args, cwd=cwd)
    return sorted({match["file"] for match in matches})


def _normalize_rg_patterns(patterns: Sequence[str]) -> list[str]:
    normalized: list[str] = []
    for pattern in patterns:
        normalized.append(re.sub(r"\\\\", r"\\", pattern))
    return normalized


def run_rg_json(
    patterns: Sequence[str],
    extra_args: Sequence[str] | None = None,
    cwd: str | Path | None = None,
) -> list[dict]:
    """
    Execute ripgrep with JSON output and return structured matches.

    Args:
        patterns: List of regex patterns to search for (supports multi-pattern via -e).
        extra_args: Additional command-line arguments forwarded to rg.
        cwd: Optional working directory for the search.

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
            cwd=str(cwd) if cwd is not None else None,
        )
        if result.returncode != 0:
            stderr_text = (result.stderr or "").strip()
            LOGGER.warning("ripgrep failed: %s", stderr_text)
            normalized_patterns = _normalize_rg_patterns(patterns)
            if normalized_patterns != list(patterns):
                return run_rg_json(normalized_patterns, extra_args, cwd=cwd)
            return _python_search(patterns, extra_args, cwd=cwd)

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
        LOGGER.warning("ripgrep (rg) not found in PATH. Falling back to Python search.")
        return _python_search(patterns, extra_args, cwd=cwd)


def run_rg_files_only(
    patterns: Sequence[str],
    extra_args: Sequence[str] | None = None,
    cwd: str | Path | None = None,
) -> list[str]:
    """
    Execute ripgrep and return only file paths (no line details).

    Args:
        patterns: List of regex patterns to search for.
        extra_args: Additional command-line arguments forwarded to rg.
        cwd: Optional working directory for the search.

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
            cwd=str(cwd) if cwd is not None else None,
        )
        if result.returncode != 0:
            stderr_text = (result.stderr or "").strip()
            LOGGER.warning("ripgrep failed: %s", stderr_text)
            normalized_patterns = _normalize_rg_patterns(patterns)
            if normalized_patterns != list(patterns):
                return run_rg_files_only(normalized_patterns, extra_args, cwd=cwd)
            return _python_files_with_matches(patterns, extra_args, cwd=cwd)

        if not result.stdout:
            return []

        # Parse file paths (each line is a file path)
        files = [line.strip() for line in result.stdout.strip().split("\n") if line.strip()]
        return sorted(set(files))

    except FileNotFoundError:
        LOGGER.warning("ripgrep (rg) not found in PATH. Falling back to Python search.")
        return _python_files_with_matches(patterns, extra_args, cwd=cwd)
