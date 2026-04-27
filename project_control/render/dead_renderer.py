"""Dead code result renderer - clean CLI output."""

from __future__ import annotations

from typing import Dict


def render_dead(result: Dict) -> str:
    """
    Render dead code analysis results for CLI output.

    Matches final_analyzer_design.md specification:
    - Clean CLI output (no raw JSON dumps)
    - Group by HIGH / MEDIUM priority
    - Show file paths
    - Display summary stats

    Args:
        result: Analysis result from analyze_dead_code().
                Expected format: {
                    "high": [file_paths],
                    "medium": [file_paths],
                    "stats": {"total": int, "dead": int}
                }

    Returns:
        Formatted string for CLI display.
    """
    lines = []

    # Header
    lines.append("=" * 70)
    lines.append("DEAD CODE ANALYSIS")
    lines.append("=" * 70)
    lines.append("")

    # High priority (orphan files)
    high_files = result.get("high", [])
    if high_files:
        lines.append(f"[HIGH] ({len(high_files)} files)")
        lines.append("-" * 70)
        for file_path in high_files:
            lines.append(f"  {file_path}")
        lines.append("")
    else:
        lines.append("[OK] No orphan files found")
        lines.append("")

    # Medium priority (low usage files)
    medium_files = result.get("medium", [])
    if medium_files:
        lines.append(f"[MEDIUM] ({len(medium_files)} files)")
        lines.append("-" * 70)
        for file_path in medium_files:
            lines.append(f"  {file_path}")
        lines.append("")
    else:
        lines.append("[OK] No low-usage files found")
        lines.append("")

    # Summary stats
    stats = result.get("stats", {})
    total = stats.get("total", 0)
    dead = stats.get("dead", 0)
    low_usage = len(medium_files)

    lines.append("=" * 70)
    lines.append("SUMMARY")
    lines.append("-" * 70)
    lines.append(f"Total files analyzed: {total}")
    lines.append(f"Orphan files: {dead}")
    lines.append(f"Low-usage files: {low_usage}")
    lines.append(f"Healthy files: {total - dead - low_usage}")
    lines.append("=" * 70)

    return "\n".join(lines)
