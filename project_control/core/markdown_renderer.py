"""Render structured ghost results into a markdown report."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, Sequence


BASE_SECTIONS: Sequence[tuple[str, str]] = (
    ("orphans", "Orphans"),
    ("legacy", "Legacy snippets"),
    ("sessions", "Session files"),
    ("duplicates", "Duplicates"),
)

SEVERITY_MAP: Dict[str, str] = {
    "orphans": "HIGH",
    "legacy": "MEDIUM",
    "sessions": "LOW",
    "duplicates": "INFO",
    "semantic": "MEDIUM",
}


def _format_list(title: str, items: Iterable[Any], severity: str) -> str:
    if not items:
        return f"### {title} [{severity}]\n\n_No entries found._\n\n"
    body = "\n".join(f"- {item}" for item in items)
    return f"### {title} [{severity}]\n\n{body}\n\n"


def render_ghost_report(
    result: Dict[str, Any],
    output_path: str,
) -> None:
    """
    Build a grouped markdown report and persist it to disk.

    Args:
        result: Ghost analysis output as returned by `core.ghost.ghost`.
        output_path: Path where the markdown should be written.
    """
    report_lines = ["# Smart Ghost Report", ""]
    summary = [
        "## Summary",
        "",
        f"- Orphans ({SEVERITY_MAP['orphans']}): {len(result.get('orphans', []))}",
        f"- Legacy snippets ({SEVERITY_MAP['legacy']}): {len(result.get('legacy', []))}",
        f"- Session files ({SEVERITY_MAP['sessions']}): {len(result.get('sessions', []))}",
        f"- Duplicates ({SEVERITY_MAP['duplicates']}): {len(result.get('duplicates', []))}",
        f"- Semantic findings ({SEVERITY_MAP['semantic']}): {len(result.get('semantic', []))}",
        "",
    ]
    report_lines.extend(summary)

    for key, heading in BASE_SECTIONS:
        section_items = result.get(key, [])
        severity = SEVERITY_MAP.get(key, "INFO")
        report_lines.append(_format_list(heading, section_items, severity))
        if key == "legacy":
            semantic_items = result.get("semantic", [])
            if semantic_items:
                section = "### Semantic Findings [MEDIUM]\n\n"
                orphans = [item for item in semantic_items if isinstance(item, dict) and item.get("type") == "orphan"]
                duplicates = [item for item in semantic_items if isinstance(item, dict) and item.get("type") == "duplicate"]
                if orphans:
                    section += "**Semantic Orphans** (low similarity to codebase):\n"
                    for item in orphans:
                        section += f"- {item['path']} (similarities: {item.get('similarities', 0):.2f})\n"
                    section += "\n"
                if duplicates:
                    section += "**Semantic Duplicates** (high similarity to other files):\n"
                    for item in duplicates:
                        section += f"- {item['path']} ↔ {item.get('related_to', 'unknown')} (similarities: {item.get('similarity', 0):.2f})\n"
                report_lines.append(section)
            else:
                report_lines.append("### Semantic Findings [MEDIUM]\n\nNo entries found.\n")

    report_text = "\n".join(report_lines).rstrip() + "\n"
    Path(output_path).write_text(report_text, encoding="utf-8")


def render_writer_report(results: Dict[str, str], output_path: str) -> None:
    """
    Write a markdown report per writer pattern.

    Args:
        results: Mapping of pattern name to its usage summary string.
        output_path: Destination file path.
    """
    lines = ["# Writers Report\n"]
    for pattern, summary in sorted(results.items()):
        lines.append(f"## {pattern}\n")
        lines.append(summary)
        lines.append("")
    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
