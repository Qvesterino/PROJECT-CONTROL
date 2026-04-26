"""Dead code analyzer - finds files with zero or minimal usage."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TypedDict

from project_control.utils.rg_helper import run_rg_json

LOGGER = logging.getLogger(__name__)


class DeadCodeResult(TypedDict):
    """Structured result from dead code analysis."""
    high: list[dict]  # orphan files (0-1 usage)
    medium: list[dict]  # low usage files
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
    project_root: str | Path = ".",
    low_usage_threshold: int = 2,
    extensions: list[str] | None = None,
) -> DeadCodeResult:
    """
    Analyze project for dead/unused code.

    Args:
        project_root: Root directory to analyze.
        low_usage_threshold: Max usage count to consider as "low usage".
        extensions: File extensions to include (e.g., [".py", ".js", ".ts"]).

    Returns:
        Structured result with high/medium priority files and stats.
    """
    root = Path(project_root)
    if extensions is None:
        extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]

    high: list[dict] = []
    medium: list[dict] = []
    total_files = 0
    dead_files = 0

    # Collect all relevant files
    files_to_check = []
    for ext in extensions:
        files_to_check.extend(root.rglob(f"*{ext}"))

    total_files = len(files_to_check)

    for file_path in files_to_check:
        # Skip ignored files
        if _should_ignore_file(file_path):
            continue

        # Search for file name usage in project
        file_name = file_path.stem  # filename without extension
        file_name_with_ext = file_path.name  # filename with extension

        # Search for both with and without extension
        matches = run_rg_json(
            [file_name, file_name_with_ext],
            extra_args=["--type", "py", "--type", "js", "--type", "ts"],
        )

        # Filter out matches from the file itself (self-reference)
        external_matches = [
            m for m in matches
            if Path(m["file"]) != file_path
        ]

        usage_count = len(external_matches)

        if usage_count <= 1:
            # Orphan candidate
            high.append({
                "file": str(file_path.relative_to(root)),
                "usage": usage_count,
                "reason": "Orphan" if usage_count == 0 else "Near-orphan",
            })
            dead_files += 1
        elif usage_count <= low_usage_threshold:
            # Low usage
            medium.append({
                "file": str(file_path.relative_to(root)),
                "usage": usage_count,
                "reason": "Low usage",
            })

    return {
        "high": sorted(high, key=lambda x: x["file"]),
        "medium": sorted(medium, key=lambda x: x["file"]),
        "stats": {
            "total_files": total_files,
            "dead_files": dead_files,
            "low_usage_files": len(medium),
        },
    }
