"""Render VFX contract audit results for CLI and exported reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from project_control.analysis.vfx_contract_audit import (
    VFXContractAuditResult,
    vfx_contract_result_to_dict,
)


def _check_line(report: Dict[str, Any]) -> str:
    return " ".join(f"{check['name']}:{'✅' if check['passed'] else '❌'}" for check in report.get("checks", []))


def render_vfx_contract_console(result: VFXContractAuditResult) -> str:
    data = vfx_contract_result_to_dict(result)
    reports = data["reports"]
    summary = data["summary"]

    lines = []
    lines.append("=" * 70)
    lines.append("VFX CONTRACT AUDIT")
    lines.append("=" * 70)
    lines.append(f"Scanning {summary.get('total_files', 0)} FX files...")
    lines.append("")

    for report in reports:
        box_width = 70
        lines.append("┌" + "─" * box_width + "┐")
        lines.append(f"│ FILE: {report['filename']:<{box_width - 7}}│")
        lines.append(f"│ Category: {report['category']:<{box_width - 11}}│")
        lines.append(f"│ Owner: {report['owner']:<{box_width - 8}}│")
        lines.append(f"│ Trigger: {report['trigger']:<{box_width - 10}}│")
        risk_text = f"{report['risk_level']} (score {report['risk_score']})"
        lines.append(f"│ Risk: {risk_text:<{box_width - 8}}│")
        lines.append(f"│ Verdict: {report['verdict']:<{box_width - 10}}│")
        lines.append("├" + "─" * box_width + "┤")

        check_line = _check_line(report)
        while check_line:
            chunk = check_line[: box_width - 2]
            check_line = check_line[box_width - 2 :]
            lines.append(f"│ {chunk:<{box_width - 2}}│")
        lines.append("└" + "─" * box_width + "┘")
        lines.append("")

    lines.append("=" * 70)
    lines.append("SUMMARY:")
    for verdict in ("keep", "fix", "isolate", "kill"):
        label = verdict.upper()
        lines.append(f"  {label:<10} {summary.get(verdict, 0)} files")
    lines.append("=" * 70)
    return "\n".join(lines)


def render_vfx_contract_markdown(result: VFXContractAuditResult) -> str:
    data = vfx_contract_result_to_dict(result)
    reports = data["reports"]
    summary = data["summary"]

    lines = [
        "# VFX Contract Audit Report",
        "",
        "**Date:** auto-generated  ",
        f"**Files Scanned:** {summary.get('total_files', 0)}  ",
        "",
        "## Summary",
        "",
        f"- **KEEP:** {summary.get('keep', 0)} files",
        f"- **FIX:** {summary.get('fix', 0)} files",
        f"- **ISOLATE:** {summary.get('isolate', 0)} files",
        f"- **KILL:** {summary.get('kill', 0)} files",
        "",
        "## Per-File Details",
        "",
        "| File | Category | Owner | Trigger | Risk | Verdict | Checks |",
        "|------|----------|-------|---------|------|---------|--------|",
    ]

    for report in reports:
        checks = " ".join(f"{check['name']}:{'✅' if check['passed'] else '❌'}" for check in report.get("checks", []))
        lines.append(
            f"| {report['filename']} | {report['category']} | {report['owner']} | {report['trigger']} | "
            f"{report['risk_level']}({report['risk_score']}) | {report['verdict']} | {checks} |"
        )

    lines.append("")
    lines.append("## Risk Details")
    lines.append("")

    for report in reports:
        if report.get("risk_level") not in ("MID", "HIGH"):
            continue
        lines.append(f"### {report['filename']}")
        lines.append(f"- **Risk:** {report['risk_level']} (score {report['risk_score']})")
        lines.append(f"- **Verdict:** {report['verdict']}")
        for check in report.get("checks", []):
            if not check.get("passed"):
                lines.append(f"- **{check['name']}:** ❌ {check.get('detail', '')}")
        lines.append("")

    return "\n".join(lines)


def write_vfx_contract_outputs(result: VFXContractAuditResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = output_dir / "vfx_contract_audit_report.md"
    json_path = output_dir / "vfx_contract_audit_data.json"

    markdown_path.write_text(render_vfx_contract_markdown(result), encoding="utf-8")
    json_path.write_text(json.dumps(vfx_contract_result_to_dict(result), indent=2, ensure_ascii=False), encoding="utf-8")
    return markdown_path, json_path