"""Patron's Path integration contract analysis."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable
from urllib.parse import urlparse

from project_control.config.patron_path_loader import (
    get_patron_path_contract_path,
    load_patron_path_contract,
)


@dataclass(frozen=True)
class PatronPathCheck:
    """A single Patron's Path contract check."""

    name: str
    status: str
    message: str
    details: str | None = None
    path: str | None = None
    url: str | None = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
            "path": self.path,
            "url": self.url,
        }


@dataclass(frozen=True)
class PatronPathAuditResult:
    """Serializable Patron's Path audit result."""

    project_root: str
    contract_path: str
    contract: Dict[str, Any]
    nebula_bridge_path: str
    checks: list[PatronPathCheck]
    summary: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "projectRoot": self.project_root,
            "contractPath": self.contract_path,
            "contract": self.contract,
            "nebulaBridgePath": self.nebula_bridge_path,
            "checks": [check.to_dict() for check in self.checks],
            "summary": self.summary,
        }


def _status_for_checks(checks: Iterable[PatronPathCheck]) -> str:
    statuses = {check.status for check in checks}
    if "error" in statuses:
        return "error"
    if "warning" in statuses:
        return "warning"
    return "healthy"


def _make_check(name: str, status: str, message: str, *, details: str | None = None, path: str | None = None, url: str | None = None) -> PatronPathCheck:
    return PatronPathCheck(name=name, status=status, message=message, details=details, path=path, url=url)


def _resolve_contract_path(project_root: Path) -> Path:
    return get_patron_path_contract_path(project_root)


def _nebula_bridge_path(project_root: Path, contract: Dict[str, Any]) -> Path:
    bridge_contract = contract.get("nebula_bridge", {}) if isinstance(contract.get("nebula_bridge", {}), dict) else {}
    bridge_directory = str(bridge_contract.get("directory", ".project-control/exports"))
    bridge_name = str(bridge_contract.get("file_name", "nebula_bridge.json"))
    return (project_root / bridge_directory / bridge_name).resolve()


def _check_path(label: str, raw_value: Any) -> PatronPathCheck:
    if raw_value in (None, ""):
        return _make_check(label, "error", f"{label} is missing", details="Add the path to patron_path.yaml")

    candidate = Path(str(raw_value))
    if not candidate.is_absolute():
        return _make_check(label, "error", f"{label} must be an absolute path", path=str(candidate))

    normalized = candidate.resolve()
    if normalized.exists():
        return _make_check(label, "ok", f"{label} exists", path=normalized.as_posix())

    return _make_check(
        label,
        "warning",
        f"{label} is configured but not present locally",
        details="This is acceptable for smoke tests, but the downstream project is not installed here.",
        path=normalized.as_posix(),
    )


def _check_url(label: str, raw_value: Any) -> PatronPathCheck:
    if raw_value in (None, ""):
        return _make_check(label, "error", f"{label} is missing", details="Add the URL to patron_path.yaml")

    parsed = urlparse(str(raw_value))
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return _make_check(label, "error", f"{label} must be an absolute HTTP(S) URL", url=str(raw_value))

    return _make_check(label, "ok", f"{label} is valid", url=str(raw_value))


def _check_nebula_bridge(project_root: Path, contract: Dict[str, Any]) -> PatronPathCheck:
    bridge_path = _nebula_bridge_path(project_root, contract)

    if not bridge_path.exists():
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export is missing",
            details="Run `pc nebula export` or the ecosystem health check to generate it.",
            path=bridge_path.as_posix(),
        )

    try:
        payload = json.loads(bridge_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export contains invalid JSON",
            details=str(error),
            path=bridge_path.as_posix(),
        )

    if payload.get("schemaVersion") != 1:
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export schema version is not locked to 1",
            details=f"Found: {payload.get('schemaVersion')}",
            path=bridge_path.as_posix(),
        )

    if payload.get("projectRoot") != project_root.resolve().as_posix():
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export targets the wrong project root",
            details=f"Expected {project_root.resolve().as_posix()}",
            path=bridge_path.as_posix(),
        )

    metadata = payload.get("metadata", {})
    if not isinstance(metadata, dict) or metadata.get("pathStyle") != "relative-posix":
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export is not using relative posix paths",
            path=bridge_path.as_posix(),
        )

    findings = payload.get("findings", [])
    if not isinstance(findings, list):
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export findings payload is invalid",
            path=bridge_path.as_posix(),
        )

    if any("\\" in str(finding.get("path", "")) for finding in findings if isinstance(finding, dict)):
        return _make_check(
            "nebula_bridge_export",
            "error",
            "Nebula bridge export still contains backslash paths",
            path=bridge_path.as_posix(),
        )

    summary = payload.get("summary", {})
    finding_count = summary.get("findingCount", len(findings)) if isinstance(summary, dict) else len(findings)
    return _make_check(
        "nebula_bridge_export",
        "ok",
        "Nebula bridge export is valid",
        details=f"{finding_count} findings ready for downstream consumers.",
        path=bridge_path.as_posix(),
    )


def analyze_patron_path(project_root: str | Path) -> PatronPathAuditResult:
    """Analyze the Patron's Path integration contract."""
    root = Path(project_root).resolve()
    contract_path = _resolve_contract_path(root)
    contract = load_patron_path_contract(root)

    checks = [
        _make_check(
            "contract_file",
            "ok" if contract_path.exists() else "warning",
            "Patron's Path contract file is present" if contract_path.exists() else "Using built-in Patron's Path defaults",
            details=None if contract_path.exists() else "Create .project-control/patron_path.yaml to make the contract explicit.",
            path=contract_path.as_posix(),
        ),
        _check_path("codebase_nebula_root", contract.get("codebase_nebula_root")),
        _check_path("patrons_path_root", contract.get("patrons_path_root")),
        _check_url("file_genome.analyze_url", contract.get("file_genome", {}).get("analyze_url")),
        _check_url("file_genome.batch_url", contract.get("file_genome", {}).get("batch_url")),
        _check_nebula_bridge(root, contract),
    ]

    summary = {
        "checkCount": len(checks),
        "okCount": sum(1 for check in checks if check.status == "ok"),
        "warningCount": sum(1 for check in checks if check.status == "warning"),
        "errorCount": sum(1 for check in checks if check.status == "error"),
        "overallStatus": _status_for_checks(checks),
    }

    return PatronPathAuditResult(
        project_root=root.as_posix(),
        contract_path=contract_path.as_posix(),
        contract=contract,
        nebula_bridge_path=_nebula_bridge_path(root, contract).as_posix(),
        checks=checks,
        summary=summary,
    )
