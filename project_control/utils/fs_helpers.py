"""Filesystem helpers for PROJECT CONTROL."""

from __future__ import annotations

import logging
import subprocess
from typing import Sequence

LOGGER = logging.getLogger(__name__)


def run_rg(pattern: str, extra_args: Sequence[str] | None = None) -> str:
    """
    Execute ripgrep with the provided pattern and return its stdout.

    Args:
        pattern: Regex pattern to search for.
        extra_args: Additional command-line arguments forwarded to rg.

    Returns:
        Captured stdout (empty string if rg is unavailable or no matches).
    """
    cmd = ["rg", pattern, "--line-number", "--no-heading"]
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
        return result.stdout
    except FileNotFoundError:
        LOGGER.warning("ripgrep (rg) not found in PATH.")
        return ""
