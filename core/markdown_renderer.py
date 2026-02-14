"""Render structured ghost results into a markdown report."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence


BASE_SECTIONS: Sequence[tuple[str, str]] = (
    ("orphans", "Orphans"),
    ("legacy", "Legacy snippets"),
    ("session", "Session files"),
    ("duplicates", "Duplicates"),
)

GRAPH_SECTION = ("graph_orphans", "Import graph orphans")

SEVERITY_MAP: Dict[str, str] = {
    "graph_orphans": "CRITICAL",
    "orphans": "HIGH",
    "legacy": "MEDIUM",
    "session": "LOW",
    "duplicates": "INFO",
}


def _format_list(title: str, items: Iterable[Any], severity: str) -> str:
    if not items:
        return f"### {title} [{severity}]\n\n_No entries found._\n\n"
    body = "\n".join(f"- {item}" for item in items)
    return f"### {title} [{severity}]\n\n{body}\n\n"


def render_ghost_report(
    result: Dict[str, Any],
    output_path: str,
    include_graph: bool = False,
) -> None:
    """
    Build a grouped markdown report and persist it to disk.

    Args:
        result: Ghost analysis output as returned by `core.ghost.analyze_ghost`.
        output_path: When sanitized, path where the markdown should be written.
    """
    report_lines = ["# Smart Ghost Report", ""]
    summary = [
        "## Summary",
        "",
    ]
    if include_graph:
        summary.append(
            f"- Import graph orphans ({SEVERITY_MAP['graph_orphans']}): {len(result.get('graph_orphans', []))}"
        )
    summary.extend(
        [
            f"- Orphans ({SEVERITY_MAP['orphans']}): {len(result.get('orphans', []))}",
            f"- Legacy snippets ({SEVERITY_MAP['legacy']}): {len(result.get('legacy', []))}",
            f"- Session files ({SEVERITY_MAP['session']}): {len(result.get('session', []))}",
            f"- Duplicates ({SEVERITY_MAP['duplicates']}): {len(result.get('duplicates', []))}",
            "",
        ]
    )
    report_lines.extend(summary)

    sections = list(BASE_SECTIONS)
    if include_graph:
        sections.insert(0, GRAPH_SECTION)

    for key, heading in sections:
        section_items = result.get(key, [])
        severity = SEVERITY_MAP.get(key, "INFO")
        report_lines.append(_format_list(heading, section_items, severity))

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
