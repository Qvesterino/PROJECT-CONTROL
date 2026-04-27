"""Dead code analyzer - finds files with zero or minimal usage.

Matches the final_analyzer_design.md specification:
- Pure ripgrep-based analysis
- Simple basename matching
- Deterministic output
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

from project_control.utils.rg_helper import run_rg_files_only

LOGGER = logging.getLogger(__name__)


class DeadCodeResult(TypedDict):
    """Structured result from dead code analysis.
    
    Matches design spec: high/medium contain file paths (strings), not dicts.
    """
    high: list[str]  # orphan files (0-1 usage)
    medium: list[str]  # low usage files
    stats: dict


def _should_ignore_file(file_path: Path) -> bool:
    """
    Check if a file should be automatically ignored based on common patterns.

    Args:
        file_path: Path to the file to check.

    Returns:
        True if file should be ignored, False otherwise.
    """
    # Get path parts for easier checking
    parts = file_path.parts

    # Check directory-level ignores
    ignore_dirs = {
        "node_modules",
        ".git",
        ".project-control",
        "venv",
        ".venv",
        "env",
        ".env",
        "__pycache__",
        ".pytest_cache",
        ".cache",
        "dist",
        "build",
        ".next",
        "target",
        "bin",
        "obj",
        "out",
    }

    for part in parts:
        # Direct match
        if part in ignore_dirs:
            return True
        # Pattern match for .venv-* directories
        if part.startswith(".venv-") or part.startswith("venv-"):
            return True
        # Pattern match for Lib/site-packages (virtual environment packages)
        if part == "Lib" and "site-packages" in parts:
            return True
        if part == "site-packages":
            return True

    # Check for test files
    file_name = file_path.name
    file_stem = file_path.stem

    # Python test files
    if file_name.startswith("test_") and file_name.endswith(".py"):
        return True
    if file_name.endswith("_test.py"):
        return True

    # JavaScript/TypeScript test files
    if file_name.endswith(".test.js") or file_name.endswith(".test.ts"):
        return True
    if file_name.endswith(".test.jsx") or file_name.endswith(".test.tsx"):
        return True
    if file_name.endswith(".spec.js") or file_name.endswith(".spec.ts"):
        return True
    if file_name.endswith(".spec.jsx") or file_name.endswith(".spec.tsx"):
        return True

    # Config files
    if file_name in {"config.py", "config.js", "config.ts", "settings.py", "settings.js"}:
        return True

    # Setup/build files
    if file_name in {"setup.py", "setup.js", "package-lock.json", "yarn.lock", "pnpm-lock.yaml"}:
        return True

    # Migration files
    if file_name.startswith("000") and file_name.endswith(".py"):
        return True

    return False


def analyze_dead_code(
    files: list[str],
    low_usage_threshold: int = 2,
) -> DeadCodeResult:
    """
    Analyze files for dead/unused code using ripgrep.

    Matches final_analyzer_design.md specification:
    - Input: list of file paths
    - Logic: basename matching via ripgrep
    - Output: {"high": [paths], "medium": [paths], "stats": {...}}

    Args:
        files: List of file paths to analyze.
        low_usage_threshold: Max usage count to consider as "low usage" (default: 2).

    Returns:
        Structured result with high/medium priority files and stats.
    """
    high: list[str] = []
    medium: list[str] = []
    total_files = len(files)
    dead_files = 0

    for file_path in files:
        # Skip ignored files
        if _should_ignore_file(Path(file_path)):
            continue

        # Get basename for search (per design spec)
        name = Path(file_path).name  # basename with extension
        name_without_ext = Path(file_path).stem  # basename without extension

        # Search for file name usage using ripgrep -l (files only mode)
        # Search for both with and without extension
        matches = run_rg_files_only(
            [name, name_without_ext],
            extra_args=None,  # Search all file types
        )

        # Count usage (number of files that reference this file)
        # Note: run_rg_files_only returns list of unique file paths
        usage_count = len(matches)

        if usage_count <= 1:
            # Orphan (0-1 references)
            high.append(file_path)
            dead_files += 1
        elif usage_count <= low_usage_threshold:
            # Low usage
            medium.append(file_path)

    return {
        "high": sorted(high),
        "medium": sorted(medium),
        "stats": {
            "total": total_files,
            "dead": dead_files,
        },
    }
