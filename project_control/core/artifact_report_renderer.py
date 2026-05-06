"""Markdown renderer for artifact hygiene reports."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def _format_bytes_and_mb(size_bytes: int) -> str:
    return f"{size_bytes} B ({size_bytes / (1024 * 1024):.2f} MB)"


def _format_candidate(candidate: dict[str, Any]) -> str:
    details: list[str] = [
        f"score={candidate.get('score', 0)}",
        f"size={candidate.get('size_bytes', 0)}B",
        f"safe_to_delete={'yes' if candidate.get('safe_to_delete') else 'no'}",
    ]
    if candidate.get("age_days") is not None:
        details.append(f"age={candidate['age_days']}d")
    if candidate.get("resolution"):
        details.append(f"resolution={candidate['resolution']}")
    if candidate.get("generator_hint"):
        details.append(f"generator={candidate['generator_hint']}")
    if candidate.get("referenced") is not None:
        details.append(f"referenced={'yes' if candidate['referenced'] else 'no'}")
    if candidate.get("git_tracked") is not None:
        details.append(f"git_tracked={'yes' if candidate['git_tracked'] else 'no'}")
    if candidate.get("git_ignored") is not None:
        details.append(f"git_ignored={'yes' if candidate['git_ignored'] else 'no'}")
    if candidate.get("duplicate_count", 0):
        details.append(f"duplicate_count={candidate['duplicate_count']}")
    if candidate.get("estimated_space_saved_bytes", 0):
        details.append(f"estimated_saved={candidate['estimated_space_saved_bytes']}B")
    reasons = ", ".join(candidate.get("reasons", [])) or "none"
    details.append(f"reasons={reasons}")
    line = f"- `{candidate['path']}` ({'; '.join(details)})"
    why = candidate.get("why", [])
    if why:
        return line + "\n  - Why: " + " | ".join(str(item) for item in why)
    return line


def _render_candidate_section(title: str, candidates: list[dict[str, Any]]) -> list[str]:
    lines = [f"## {title}", ""]
    if not candidates:
        lines.append("_No entries found._")
        lines.append("")
        return lines

    lines.extend(_format_candidate(candidate) for candidate in candidates)
    lines.append("")
    return lines


def _render_group_section(title: str, groups: list[dict[str, Any]], key_name: str) -> list[str]:
    lines = [f"## {title}", ""]
    if not groups:
        lines.append("_No entries found._")
        lines.append("")
        return lines

    for group in groups:
        label = group.get(key_name) or "unknown"
        lines.append(f"### {label}")
        lines.append("")
        lines.append(f"- Count: {group.get('count', 0)}")
        for path_value in group.get("paths", []):
            lines.append(f"- `{path_value}`")
        lines.append("")
    return lines


def _render_space_savings(result: dict[str, Any]) -> list[str]:
    savings = result.get("space_savings", {})
    lines = ["## Space Savings", ""]
    lines.append(f"- Safe-to-delete bytes: {_format_bytes_and_mb(int(savings.get('safe_to_delete_bytes', 0)))}")
    lines.append(f"- Duplicate wasted bytes: {_format_bytes_and_mb(int(savings.get('duplicate_wasted_bytes', 0)))}")
    lines.append("")
    lines.append("### Top Space-Saving Directories")
    lines.append("")
    directories = savings.get("top_space_saving_directories", [])
    if not directories:
        lines.append("_No entries found._")
        lines.append("")
        return lines

    for entry in directories:
        lines.append(
            f"- `{entry.get('directory', '.')}`: "
            f"{_format_bytes_and_mb(int(entry.get('reclaimable_bytes', 0)))} "
            f"across {entry.get('candidate_count', 0)} candidates"
        )
    lines.append("")
    return lines


def _render_duplicate_screenshots(groups: list[dict[str, Any]]) -> list[str]:
    lines = ["## Duplicate Screenshots", ""]
    if not groups:
        lines.append("_No entries found._")
        lines.append("")
        return lines

    for group in groups:
        lines.append(
            f"### Group {group.get('duplicate_group_id', 'unknown')} "
            f"({group.get('count', 0)} files, canonical `{group.get('canonical_path', 'unknown')}`)"
        )
        lines.append("")
        lines.append(f"- Duplicate wasted bytes: {_format_bytes_and_mb(int(group.get('duplicate_wasted_bytes', 0)))}")
        lines.append(f"- Safe-to-delete members: {group.get('safe_to_delete_count', 0)}")
        for path_value in group.get("duplicate_paths", []):
            lines.append(f"- `{path_value}`")
        lines.append("")
    return lines


def render_artifact_report(result: dict[str, Any], output_path: str | Path) -> None:
    """Persist a markdown artifact hygiene report."""
    summary = result.get("summary", {})
    lines = [
        "# Artifact Hygiene Report",
        "",
        "## Summary",
        "",
        f"- Total assets scanned: {summary.get('total_assets_scanned', 0)}",
        f"- Report candidates: {summary.get('report_candidates', 0)}",
        f"- Safe to delete now: {summary.get('safe_to_delete', 0)}",
        f"- Safe-to-delete space: {_format_bytes_and_mb(int(summary.get('safe_to_delete_bytes', 0)))}",
        f"- High confidence cleanup candidates: {summary.get('high_confidence_cleanup_candidates', 0)}",
        f"- Review candidates: {summary.get('review_candidates', 0)}",
        f"- Duplicate groups: {summary.get('duplicate_groups', 0)}",
        f"- Duplicate wasted space: {_format_bytes_and_mb(int(summary.get('duplicate_wasted_bytes', 0)))}",
        f"- Delete candidates: {summary.get('delete_candidates', 0)}",
        "",
    ]

    lines.extend(
        _render_candidate_section(
            "Safe To Delete Now",
            result.get("safe_to_delete_candidates", []),
        )
    )
    lines.extend(
        _render_candidate_section(
            "High Confidence Cleanup Candidates",
            result.get("high_confidence_cleanup_candidates", []),
        )
    )
    lines.extend(_render_candidate_section("Review Candidates", result.get("review_candidates", [])))
    lines.extend(_render_space_savings(result))
    lines.extend(_render_duplicate_screenshots(result.get("duplicate_screenshot_groups", [])))
    lines.extend(_render_group_section("Grouped By Resolution", result.get("grouped_by_resolution", []), "resolution"))
    lines.extend(_render_group_section("Grouped By Directory", result.get("grouped_by_directory", []), "directory"))

    lines.append("## Delete Candidate List")
    lines.append("")
    delete_candidates = result.get("delete_candidates", [])
    if delete_candidates:
        lines.extend(f"- `{path_value}`" for path_value in delete_candidates)
    else:
        lines.append("_No entries found._")
    lines.append("")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
