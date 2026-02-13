"""Render structured ghost results into a markdown report."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence


SECTION_ORDER: Sequence[tuple[str, str]] = (
    ("orphans", "Orphans"),
    ("legacy", "Legacy snippets"),
    ("session", "Session files"),
    ("duplicates", "Duplicates"),
)


def _format_list(title: str, items: Iterable[Any]) -> str:
    if not items:
        return f"### {title}\n\n_No entries found._\n\n"
    body = "\n".join(f"- {item}" for item in items)
    return f"### {title}\n\n{body}\n\n"


def render_ghost_report(result: Dict[str, Any], output_path: str) -> None:
    """
    Build a grouped markdown report and persist it to disk.

    Args:
        result: Ghost analysis output as returned by `core.ghost.analyze_ghost`.
        output_path: When sanitized, path where the markdown should be written.
    """
    report_lines = ["# Smart Ghost Report", ""]

    for key, heading in SECTION_ORDER:
        section_items = result.get(key, [])
        report_lines.append(_format_list(heading, section_items))

    report_text = "\n".join(report_lines).rstrip() + "\n"
    Path(output_path).write_text(report_text, encoding="utf-8")


def render_writer_report(results: Dict[str, str], output_path: str) -> None:
    """
    Write a markdown report per writer pattern.

    Args:
        results: Map of writer keywords to ripgrep output.
        output_path: Destination path for the report.
    """
    report_lines = ["# Writer Report", ""]

    for pattern, output in results.items():
        body = output.strip() if output else "_No matches found._"
        section = f"## {pattern}\n\n{body}\n"
        report_lines.append(section)

    report_text = "\n".join(report_lines).rstrip() + "\n"
    Path(output_path).write_text(report_text, encoding="utf-8")
