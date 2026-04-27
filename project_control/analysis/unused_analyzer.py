"""Unused systems analyzer - finds systems that exist but aren't used.

Matches the final_analyzer_design.md specification:
- 4-signal detection system (import, instantiation, usage, entrypoint)
- Scoring system (0-4 scale)
- HIGH/MEDIUM/LOW classification
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TypedDict

from project_control.utils.rg_helper import run_rg_json, run_rg_files_only
from project_control.analysis.dead_analyzer import _should_ignore_file

LOGGER = logging.getLogger(__name__)


class UnusedSystemsResult(TypedDict):
    """Structured result from unused systems analysis.

    Matches design spec: high/medium/low contain dicts with file, score, reasons.
    """
    high: list[dict]   # score 4 - completely unused
    medium: list[dict] # score 2-3 - barely used
    low: list[dict]    # score 1 - used but suspicious
    stats: dict


def _detect_system_name(file_path: Path) -> str:
    """
    Extract system name from file path.

    Args:
        file_path: Path to the system file.

    Returns:
        System/class name (file name without extension).
    """
    return file_path.stem


def _check_import_signal(system_name: str, project_root: Path) -> tuple[bool, str]:
    """
    Signal 1: Check if system is imported anywhere.

    Args:
        system_name: Name of the system/class.
        project_root: Root directory to search in.

    Returns:
        (has_import, reason): Tuple with boolean and reason string.
    """
    # Try multiple import patterns
    patterns = [
        f"import.*{system_name}",
        f"require.*{system_name}",
        f"from.*{system_name}",
    ]

    matches = run_rg_json(
        patterns,
        extra_args=["--type", "py", "--type", "js", "--type", "ts"],
    )

    if matches:
        return True, f"Import found in {len(matches)} location(s)"
    return False, "No import found"


def _check_instantiation_signal(system_name: str, project_root: Path) -> tuple[bool, str]:
    """
    Signal 2: Check if system is instantiated anywhere.

    Args:
        system_name: Name of the system/class.
        project_root: Root directory to search in.

    Returns:
        (has_instantiation, reason): Tuple with boolean and reason string.
    """
    # Look for "new ClassName" or "ClassName()" patterns
    patterns = [
        f"new {system_name}",
        f"{system_name}\\(",  # Class instantiation: ClassName(
        f"{system_name} =",  # Variable assignment (potential instantiation)
    ]

    matches = run_rg_json(
        patterns,
        extra_args=["--type", "py", "--type", "js", "--type", "ts"],
    )

    if matches:
        return True, f"Instantiation found in {len(matches)} location(s)"
    return False, "No instantiation found"


def _check_usage_signal(system_name: str, project_root: Path, exclude_file: Path) -> tuple[bool, str]:
    """
    Signal 3: Check if system name appears in code (general usage).

    Args:
        system_name: Name of the system/class.
        project_root: Root directory to search in.
        exclude_file: File to exclude from search (self-reference).

    Returns:
        (has_usage, reason): Tuple with boolean and reason string.
    """
    # Search for system name in general
    matches = run_rg_json(
        [system_name],
        extra_args=["--type", "py", "--type", "js", "--type", "ts"],
    )

    # Filter out self-references
    external_matches = [
        m for m in matches
        if Path(m["file"]).resolve() != exclude_file.resolve()
    ]

    if len(external_matches) > 1:
        return True, f"Usage found in {len(external_matches)} location(s)"
    return False, f"Usage count: {len(external_matches)} (<=1 threshold)"


def _check_entrypoint_signal(system_name: str, project_root: Path) -> tuple[bool, str]:
    """
    Signal 4: Check if system is referenced in entrypoint files.

    Args:
        system_name: Name of the system/class.
        project_root: Root directory to search in.

    Returns:
        (has_entrypoint, reason): Tuple with boolean and reason string.
    """
    # Common entrypoint files
    entrypoints = ["main.js", "index.js", "main.py", "index.py", "app.js", "app.py"]

    # Search for system name in entrypoint files only
    matches = []
    for entrypoint in entrypoints:
        entrypoint_path = project_root / entrypoint
        if entrypoint_path.exists():
            file_matches = run_rg_json(
                [system_name],
                extra_args=["--type", "py", "--type", "js"],
            )
            # Filter to only matches from the entrypoint file
            entrypoint_matches = [
                m for m in file_matches
                if Path(m["file"]).resolve() == entrypoint_path.resolve()
            ]
            matches.extend(entrypoint_matches)

    if matches:
        return True, f"Referenced in entrypoint: {matches[0]['file']}"
    return False, "Not referenced in any entrypoint"


def _calculate_score(
    has_import: bool,
    has_instantiation: bool,
    has_usage: bool,
    has_entrypoint: bool,
) -> int:
    """
    Calculate unused score based on 4 signals.

    Scoring:
    - no import → +1
    - no instantiation → +1
    - no usage (or <=1) → +1
    - no entrypoint → +1

    Score 4: HIGH (completely unused)
    Score 2-3: MEDIUM (barely used)
    Score 1: LOW (used but suspicious)
    Score 0: Used (not included in results)

    Args:
        has_import: Whether system is imported.
        has_instantiation: Whether system is instantiated.
        has_usage: Whether system is used (count > 1).
        has_entrypoint: Whether system is in entrypoint.

    Returns:
        Score from 0-4.
    """
    score = 0

    if not has_import:
        score += 1
    if not has_instantiation:
        score += 1
    if not has_usage:
        score += 1
    if not has_entrypoint:
        score += 1

    return score


def _classify_score(score: int) -> str:
    """
    Classify score into HIGH/MEDIUM/LOW.

    Args:
        score: Score from 0-4.

    Returns:
        Classification string: "high", "medium", "low", or None for score 0.
    """
    if score == 4:
        return "high"
    elif score >= 2:
        return "medium"
    elif score == 1:
        return "low"
    else:
        return None  # Score 0 means system is used


def analyze_unused_systems(
    project_root: str | Path = ".",
    extensions: list[str] | None = None,
    name_patterns: list[str] | None = None,
) -> UnusedSystemsResult:
    """
    Analyze project for unused systems using 4-signal detection system.

    Matches final_analyzer_design.md specification:
    - STEP 1: Detect system files (System, Manager, Controller, Service, Engine)
    - STEP 2: Run 4 signals (import, instantiation, usage, entrypoint)
    - STEP 3: Calculate score (0-4)
    - STEP 4: Classify (4=HIGH, 2-3=MEDIUM, 1=LOW)
    - Output: {"high": [...], "medium": [...], "low": [...], "stats": {...}}

    Args:
        project_root: Root directory to analyze.
        extensions: File extensions to include.
        name_patterns: Patterns to identify system files (default: System, Manager, Controller, Service, Engine).

    Returns:
        Structured result with high/medium/low priority systems and stats.
    """
    root = Path(project_root)
    if extensions is None:
        extensions = [".py", ".js", ".ts", ".jsx", ".tsx"]

    if name_patterns is None:
        name_patterns = ["System", "Manager", "Controller", "Service", "Engine"]

    high: list[dict] = []
    medium: list[dict] = []
    low: list[dict] = []
    total_systems = 0

    # Find files matching system naming patterns
    system_files = []
    for ext in extensions:
        for pattern in name_patterns:
            system_files.extend(root.rglob(f"*{pattern}*{ext}"))

    # Remove duplicates (same file might match multiple patterns)
    system_files = list(set(system_files))
    total_systems = len(system_files)

    for file_path in system_files:
        # Skip ignored files (test, config, venv, etc.)
        if _should_ignore_file(file_path):
            continue

        # STEP 1: Detect system name
        system_name = _detect_system_name(file_path)

        # STEP 2: Run 4 signals
        has_import, import_reason = _check_import_signal(system_name, root)
        has_instantiation, instantiation_reason = _check_instantiation_signal(system_name, root)
        has_usage, usage_reason = _check_usage_signal(system_name, root, file_path)
        has_entrypoint, entrypoint_reason = _check_entrypoint_signal(system_name, root)

        # STEP 3: Calculate score
        score = _calculate_score(has_import, has_instantiation, has_usage, has_entrypoint)

        # Skip if score is 0 (system is used)
        if score == 0:
            continue

        # STEP 4: Collect reasons
        reasons = []
        if not has_import:
            reasons.append(import_reason)
        if not has_instantiation:
            reasons.append(instantiation_reason)
        if not has_usage:
            reasons.append(usage_reason)
        if not has_entrypoint:
            reasons.append(entrypoint_reason)

        # Classify and add to appropriate bucket
        classification = _classify_score(score)

        system_entry = {
            "file": str(file_path.relative_to(root)),
            "system_name": system_name,
            "score": score,
            "reasons": reasons,
        }

        if classification == "high":
            high.append(system_entry)
        elif classification == "medium":
            medium.append(system_entry)
        elif classification == "low":
            low.append(system_entry)

    return {
        "high": sorted(high, key=lambda x: x["file"]),
        "medium": sorted(medium, key=lambda x: x["file"]),
        "low": sorted(low, key=lambda x: x["file"]),
        "stats": {
            "total_systems": total_systems,
            "high_priority": len(high),
            "medium_priority": len(medium),
            "low_priority": len(low),
        },
    }
