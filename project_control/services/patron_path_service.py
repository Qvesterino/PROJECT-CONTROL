"""Service wrapper for Patron's Path integration contract audits."""

from __future__ import annotations

import json
from pathlib import Path

from project_control.analysis.patron_path_analyzer import PatronPathAuditResult, analyze_patron_path


def _render_markdown(result: PatronPathAuditResult) -> str:
    lines: list[str] = [
        "# Patron's Path Integration Contract",
        "",
        f"Project root: {result.project_root}",
        f"Contract file: {result.contract_path}",
        f"Nebula bridge export: {result.nebula_bridge_path}",
        "",
        "## Summary",
        f"- Overall status: {result.summary['overallStatus']}",
        f"- Checks: {result.summary['checkCount']}",
        f"- OK: {result.summary['okCount']}",
        f"- Warnings: {result.summary['warningCount']}",
        f"- Errors: {result.summary['errorCount']}",
        "",
        "## Checks",
    ]

    for check in result.checks:
        marker = check.status.upper()
        lines.append(f"- [{marker}] {check.name}: {check.message}")
        if check.path:
            lines.append(f"  Path: {check.path}")
        if check.url:
            lines.append(f"  URL: {check.url}")
        if check.details:
            lines.append(f"  Details: {check.details}")

    return "\n".join(lines)


def run_patron_path_audit(project_root: Path, output_dir: Path | None = None) -> tuple[PatronPathAuditResult, Path, Path]:
    """Run the Patron's Path contract audit and write markdown/JSON outputs."""
    result = analyze_patron_path(project_root)
    target_dir = output_dir or project_root / ".project-control" / "exports"
    target_dir.mkdir(parents=True, exist_ok=True)

    markdown_path = target_dir / "patron_path_contract_report.md"
    json_path = target_dir / "patron_path_contract_data.json"

    markdown_path.write_text(_render_markdown(result) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(result.to_dict(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return result, markdown_path, json_path
