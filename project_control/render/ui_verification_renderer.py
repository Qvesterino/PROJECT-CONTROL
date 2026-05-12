"""Render and persist UI verification reports."""

from __future__ import annotations

from dataclasses import asdict
from html import escape
import json
from pathlib import Path
from typing import Optional

from project_control.services.ui_verification_service import VerificationReport


def _serialize_verification_report(report: VerificationReport) -> dict:
    payload = asdict(report)
    payload["elements"] = [
        {
            **{key: value for key, value in element.items() if key != "source_path"},
            **({"sourcePath": element["source_path"]} if element.get("source_path") else {}),
        }
        for element in payload.get("elements", [])
    ]
    return payload


def render_ui_verification_console_summary(report: VerificationReport) -> str:
    """Render a concise console summary for a verification report."""

    lines = [
        "=" * 70,
        f"{report.app_name} UI Verification",
        "=" * 70,
        f"Profile:         {report.profile_name}",
        f"URL:             {report.url}",
        f"Browser:         {report.browser}",
        f"Total elements:  {report.total}",
        f"Passed:          {report.passed}  ({report.summary.get('pass_rate', 0)}% of actively tested)",
        f"Failed:          {report.failed}",
        f"Hidden:          {report.hidden_by_context}",
        f"Not applicable:  {report.not_applicable}",
        f"Warned:          {report.warned}",
        "=" * 70,
    ]
    if report.failed > 0:
        lines.append("")
        lines.append("FAILED ELEMENTS:")
        for element in report.elements:
            if element.get("test_result") == "fail":
                lines.append(
                    f"  - {element.get('id')} ({element.get('section')}) -- {element.get('error', 'No error')}"
                )
    return "\n".join(lines)


def write_ui_verification_json_report(report: VerificationReport, out_dir: Path) -> Path:
    """Write the structured JSON report and return its path."""

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "ui_verification_data.json"
    path.write_text(json.dumps(_serialize_verification_report(report), indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def render_ui_verification_markdown(report: VerificationReport) -> str:
    """Render the verification report as markdown for text-first viewers."""

    lines = [
        "# UI Verification Report",
        "",
        f"**Application:** {report.app_name}  ",
        f"**Profile:** {report.profile_name}  ",
        f"**URL:** {report.url}  ",
        f"**Browser:** {report.browser}  ",
        f"**HTML Source:** {report.html_path}  ",
    ]

    if report.manifest_path:
        lines.append(f"**Manifest:** {report.manifest_path}  ")

    lines.extend(
        [
            f"**Timestamp:** {report.timestamp}",
            "",
            "## Summary",
            "",
            f"- **Total elements:** {report.total}",
            f"- **Passed:** {report.passed}",
            f"- **Failed:** {report.failed}",
            f"- **Hidden by context:** {report.hidden_by_context}",
            f"- **Not applicable:** {report.not_applicable}",
            f"- **Warned:** {report.warned}",
            f"- **Pass rate:** {report.summary.get('pass_rate', 0)}%",
            "",
            "## By Section",
            "",
            "| Section | Total | Pass | Fail | Hidden | N/A | Warn |",
            "|---------|-------|------|------|--------|-----|------|",
        ]
    )

    for section, data in report.summary.get("by_section", {}).items():
        lines.append(
            "| "
            f"{section} | {data.get('total', 0)} | {data.get('pass', 0)} | {data.get('fail', 0)} | "
            f"{data.get('hidden-by-context', 0)} | {data.get('not-applicable', 0)} | {data.get('warn', 0)} |"
        )

    lines.extend(
        [
            "",
            "## Elements",
            "",
            "| ID | Category | Section | Result | Notes | Error |",
            "|----|----------|---------|--------|-------|-------|",
        ]
    )

    for element in report.elements:
        notes = "; ".join(str(note) for note in element.get("notes", [])) or "-"
        error = str(element.get("error") or "-")
        lines.append(
            "| "
            f"{element.get('id', '')} | {element.get('category', '')} | {element.get('section', '')} | "
            f"{element.get('test_result', '')} | {notes} | {error} |"
        )

    return "\n".join(lines)


def write_ui_verification_markdown_report(report: VerificationReport, out_dir: Path) -> Path:
    """Write the markdown report and return its path."""

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "ui_verification_report.md"
    path.write_text(render_ui_verification_markdown(report), encoding="utf-8")
    return path


def write_ui_verification_html_report(report: VerificationReport, out_dir: Path) -> Path:
    """Write the HTML report and return its path."""

    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "ui_verification_report.html"
    path.write_text(render_ui_verification_html(report), encoding="utf-8")
    return path


def write_ui_verification_outputs(
    report: VerificationReport,
    out_dir: Path,
    *,
    include_html: bool = False,
) -> tuple[Path, Path, Optional[Path]]:
    """Write standard UI verification outputs and optionally an HTML dashboard."""

    markdown_path = write_ui_verification_markdown_report(report, out_dir)
    json_path = write_ui_verification_json_report(report, out_dir)
    html_path = write_ui_verification_html_report(report, out_dir) if include_html else None
    return markdown_path, json_path, html_path


def render_ui_verification_html(report: VerificationReport) -> str:
    """Render the verification report as an HTML dashboard."""

    rows: list[str] = []
    for element in report.elements:
        status_color = {
            "pass": "#22c55e",
            "fail": "#ef4444",
            "hidden-by-context": "#9ca3af",
            "not-applicable": "#60a5fa",
            "warn": "#f59e0b",
            "pending": "#6b7280",
            "skip": "#6b7280",
        }.get(str(element.get("test_result")), "#6b7280")

        notes = "<br>".join(escape(str(note)) for note in element.get("notes", [])) or "—"
        error = escape(str(element.get("error", ""))) if element.get("error") else "—"
        if error != "—":
            error = f"<span style='color:#ef4444'>{error}</span>"

        rows.append(
            f"""
        <tr>
            <td><code>{escape(str(element.get('id', '')))}</code></td>
            <td>{escape(str(element.get('tag', '')))}</td>
            <td>{escape(str(element.get('type') or '—'))}</td>
            <td>{escape(str(element.get('category', '')))}</td>
            <td>{escape(str(element.get('section', '')))}</td>
            <td>{'✅' if element.get('present') else '❌'}</td>
            <td>{'✅' if element.get('visible') else '❌'}</td>
            <td>{'✅' if element.get('interacted') else '❌'}</td>
            <td style="color:{status_color};font-weight:bold">{escape(str(element.get('test_result', 'pending')).upper())}</td>
            <td>{notes}</td>
            <td>{error}</td>
        </tr>
        """
        )

    section_rows: list[str] = []
    for section, data in report.summary.get("by_section", {}).items():
        total = int(data.get("total", 0))
        passed = int(data.get("pass", 0))
        failed = int(data.get("fail", 0))
        hidden = int(data.get("hidden-by-context", 0))
        not_applicable = int(data.get("not-applicable", 0))
        warned = int(data.get("warn", 0))
        rate = round(passed / max(total - hidden - not_applicable, 1) * 100, 1) if total > (hidden + not_applicable) else 0
        section_rows.append(
            f"""
        <tr>
            <td>{escape(section)}</td>
            <td>{total}</td>
            <td style="color:#22c55e">{passed}</td>
            <td style="color:#ef4444">{failed}</td>
            <td style="color:#9ca3af">{hidden}</td>
            <td style="color:#60a5fa">{not_applicable}</td>
            <td style="color:#f59e0b">{warned}</td>
            <td>{rate}%</td>
        </tr>
        """
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{escape(report.app_name)} UI Verification Report</title>
    <style>
        body {{ font-family: system-ui, -apple-system, sans-serif; margin: 2rem; background: #0E041A; color: #E9D5FF; }}
        h1, h2 {{ color: #F5F0FF; }}
        h1 {{ border-bottom: 2px solid #7C3AED; padding-bottom: 0.5rem; }}
        h2 {{ color: #C084FC; }}
        .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin: 1rem 0; }}
        .card {{ background: #1C0A2E; padding: 1rem; border-radius: 0.5rem; text-align: center; border: 1px solid #3D1F6E; }}
        .card .number {{ font-size: 2rem; font-weight: bold; }}
        .pass {{ color: #34D399; }} .fail {{ color: #F87171; }}
        .skip {{ color: #9A84C9; }} .na {{ color: #A78BFA; }} .warn {{ color: #FBBF24; }}
        table {{ width: 100%; border-collapse: collapse; margin: 1rem 0; font-size: 0.875rem; }}
        th {{ background: #1C0A2E; padding: 0.75rem; text-align: left; position: sticky; top: 0; color: #C084FC; border-bottom: 2px solid #7C3AED; }}
        td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #2E1554; }}
        tr:hover {{ background: #2E1554; }}
        code {{ background: #2E1554; padding: 0.125rem 0.25rem; border-radius: 0.25rem; font-size: 0.8rem; color: #C084FC; }}
        .meta {{ color: #9A84C9; margin-bottom: 1rem; }}
    </style>
</head>
<body>
    <h1>{escape(report.app_name)} UI Verification Report</h1>
    <div class="meta">
        Profile: {escape(report.profile_name)} | URL: {escape(report.url)} | Browser: {escape(report.browser)} | Timestamp: {escape(report.timestamp)}
    </div>

    <div class="summary">
        <div class="card"><div class="number">{report.total}</div><div>Total</div></div>
        <div class="card"><div class="number pass">{report.passed}</div><div class="pass">Passed</div></div>
        <div class="card"><div class="number fail">{report.failed}</div><div class="fail">Failed</div></div>
        <div class="card"><div class="number skip">{report.hidden_by_context}</div><div class="skip">Hidden</div></div>
    </div>

    <h2>By Section</h2>
    <table>
        <tr><th>Section</th><th>Total</th><th class="pass">Pass</th><th class="fail">Fail</th><th class="skip">Hidden</th><th class="na">N/A</th><th class="warn">Warn</th><th>Pass Rate</th></tr>
        {''.join(section_rows)}
    </table>

    <h2>Element Details</h2>
    <table>
        <tr>
            <th>ID</th><th>Tag</th><th>Type</th><th>Category</th><th>Section</th>
            <th>Present</th><th>Visible</th><th>Interacted</th><th>Result</th>
            <th>Notes</th><th>Error</th>
        </tr>
        {''.join(rows)}
    </table>
</body>
</html>"""
