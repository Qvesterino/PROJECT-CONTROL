"""Cross-project ecosystem health checks for PROJECT_CONTROL."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from project_control.analysis.patron_path_analyzer import analyze_patron_path
from project_control.core.pre_flight import HealthReport, health_check
from project_control.services.nebula_export_service import run_nebula_export


def _serialize_health_report(report: HealthReport) -> Dict[str, Any]:
    return {
        "projectRoot": report.project_root.as_posix(),
        "overallStatus": report.overall_status,
        "checks": [
            {
                "name": check.name,
                "isHealthy": check.is_healthy,
                "message": check.message,
                "details": check.details,
                "suggestion": check.suggestion,
                "severity": check.severity,
            }
            for check in report.checks
        ],
        "errors": list(report.errors),
        "warnings": list(report.warnings),
        "suggestions": list(report.suggestions),
    }


def _status_rank(*statuses: str) -> str:
    if any(status == "error" for status in statuses):
        return "error"
    if any(status == "warning" for status in statuses):
        return "warning"
    return "healthy"


def _nebula_bridge_payload_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
    summary = payload.get("summary", {}) if isinstance(payload.get("summary", {}), dict) else {}
    metadata = payload.get("metadata", {}) if isinstance(payload.get("metadata", {}), dict) else {}
    return {
        "schemaVersion": payload.get("schemaVersion"),
        "projectRoot": payload.get("projectRoot"),
        "findingCount": summary.get("findingCount", 0),
        "pathStyle": metadata.get("pathStyle"),
        "exportedBy": metadata.get("exportedBy"),
    }


def _render_markdown(payload: Dict[str, Any]) -> str:
    lines: list[str] = [
        "# Ecosystem Health Report",
        "",
        f"Project root: {payload['projectRoot']}",
        "",
        "## Summary",
        f"- Overall status: {payload['summary']['overallStatus']}",
        f"- Project Control: {payload['summary']['projectControlStatus']}",
        f"- Nebula bridge export: {payload['summary']['nebulaBridgeStatus']}",
        f"- Downstream readiness: {payload['summary']['downstreamStatus']}",
        "",
        "## Sections",
    ]

    for section in payload["sections"]:
        lines.append(f"- [{section['status'].upper()}] {section['name']}: {section['message']}")
        for key, value in section.get("details", {}).items():
            lines.append(f"  {key}: {value}")

    return "\n".join(lines)


def run_ecosystem_health(project_root: Path, output_dir: Path | None = None) -> tuple[Dict[str, Any], Path, Path]:
    """Validate Project Control, Nebula export, and downstream readiness."""
    root = project_root.resolve()
    project_report = health_check(root)

    nebula_payload, nebula_path = run_nebula_export(root)
    nebula_details = _nebula_bridge_payload_summary(nebula_payload)
    nebula_status = "healthy"
    if nebula_details["schemaVersion"] != 1 or nebula_details["pathStyle"] != "relative-posix":
        nebula_status = "error"

    patron_result = analyze_patron_path(root)

    sections = [
        {
            "name": "project_control",
            "status": project_report.overall_status,
            "message": "Project Control health checks completed.",
            "details": _serialize_health_report(project_report),
        },
        {
            "name": "nebula_bridge_export",
            "status": nebula_status,
            "message": "Nebula bridge export contract validated.",
            "details": {**nebula_details, "artifactPath": nebula_path.resolve().as_posix()},
        },
        {
            "name": "downstream_readiness",
            "status": patron_result.summary["overallStatus"],
            "message": "Patron's Path and File Genome readiness validated.",
            "details": patron_result.to_dict(),
        },
    ]

    summary = {
        "overallStatus": _status_rank(project_report.overall_status, nebula_status, patron_result.summary["overallStatus"]),
        "projectControlStatus": project_report.overall_status,
        "nebulaBridgeStatus": nebula_status,
        "downstreamStatus": patron_result.summary["overallStatus"],
        "sectionCount": len(sections),
    }

    payload: Dict[str, Any] = {
        "projectRoot": root.as_posix(),
        "nebulaBridgePath": nebula_path.resolve().as_posix(),
        "projectControl": _serialize_health_report(project_report),
        "nebulaBridge": nebula_details,
        "downstreamReadiness": patron_result.to_dict(),
        "sections": sections,
        "summary": summary,
    }

    target_dir = output_dir or root / ".project-control" / "exports"
    target_dir.mkdir(parents=True, exist_ok=True)
    markdown_path = target_dir / "ecosystem_health_report.md"
    json_path = target_dir / "ecosystem_health_data.json"
    markdown_path.write_text(_render_markdown(payload) + "\n", encoding="utf-8")
    json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload, markdown_path, json_path
