"""Locked schema v2 for the Codebase Nebula bridge artifact."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


NEBULA_BRIDGE_SCHEMA_VERSION = 2
SUPPORTED_FINDING_KINDS = (
    "ghost",
    "dead",
    "unused_system",
    "suspicious_pattern",
    "artifact_hygiene",
    "audit_retention",
    "vfx_contract",
    "ui_audit",
)
SUPPORTED_SEVERITIES = (
    "high",
    "medium",
    "low",
    "info",
)


def normalize_relative_path(path_value: str | Path) -> str:
    path_text = str(path_value).replace("\\", "/")
    path = Path(path_text)

    if path.is_absolute():
        raise ValueError(f"Expected a relative path, got absolute path: {path_value}")

    normalized = path.as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]

    if normalized in {"", ".", ".."} or normalized.startswith("../"):
        raise ValueError(f"Expected a normalized relative path, got: {path_value}")

    return normalized


def normalize_project_root(project_root: str | Path) -> str:
    return Path(project_root).resolve().as_posix()


@dataclass(frozen=True)
class NebulaBridgeFinding:
    id: str
    path: str
    kind: str
    severity: str
    title: str
    details: str
    source: str
    line: int | None = None
    end_line: int | None = None
    symbol: str | None = None
    evidence: dict[str, Any] | None = None
    tags: list[str] | None = None

    def __post_init__(self) -> None:
        if self.kind not in SUPPORTED_FINDING_KINDS:
            raise ValueError(f"Unsupported finding kind: {self.kind}")
        if self.severity not in SUPPORTED_SEVERITIES:
            raise ValueError(f"Unsupported severity: {self.severity}")
        object.__setattr__(self, "path", normalize_relative_path(self.path))
        if self.line is not None and self.line < 1:
            raise ValueError("line must be 1-based when present")
        if self.end_line is not None and self.end_line < 1:
            raise ValueError("end_line must be 1-based when present")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": self.id,
            "path": self.path,
            "kind": self.kind,
            "severity": self.severity,
            "title": self.title,
            "details": self.details,
            "source": self.source,
        }
        if self.line is not None:
            data["line"] = self.line
        if self.end_line is not None:
            data["endLine"] = self.end_line
        if self.symbol is not None:
            data["symbol"] = self.symbol
        if self.evidence is not None:
            data["evidence"] = self.evidence
        if self.tags is not None:
            data["tags"] = self.tags
        return data


@dataclass(frozen=True)
class NebulaBridgeSummary:
    finding_count: int
    by_kind: dict[str, int]
    by_severity: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        return {
            "findingCount": self.finding_count,
            "byKind": self.by_kind,
            "bySeverity": self.by_severity,
        }


@dataclass(frozen=True)
class NebulaBridgeSnapshot:
    snapshot_id: str
    file_count: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.snapshot_id,
            "fileCount": self.file_count,
        }


@dataclass(frozen=True)
class NebulaBridgeMetadata:
    pc_version: str
    exported_by: str = "pc nebula export"
    path_style: str = "relative-posix"

    def to_dict(self) -> dict[str, Any]:
        return {
            "pcVersion": self.pc_version,
            "exportedBy": self.exported_by,
            "pathStyle": self.path_style,
        }


@dataclass(frozen=True)
class NebulaBridgeBundle:
    generated_at: str
    project_root: str
    snapshot: NebulaBridgeSnapshot
    summary: NebulaBridgeSummary
    findings: list[NebulaBridgeFinding]
    metadata: NebulaBridgeMetadata
    traces: list[Any] = field(default_factory=list)
    schema_version: int = NEBULA_BRIDGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schemaVersion": self.schema_version,
            "generatedAt": self.generated_at,
            "projectRoot": self.project_root,
            "snapshot": self.snapshot.to_dict(),
            "summary": self.summary.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
            "traces": list(self.traces),
            "metadata": self.metadata.to_dict(),
        }


def sort_findings(findings: list[NebulaBridgeFinding]) -> list[NebulaBridgeFinding]:
    return sorted(
        findings,
        key=lambda finding: (
            finding.path,
            finding.kind,
            finding.line or 0,
            finding.id,
        ),
    )


def build_summary(findings: list[NebulaBridgeFinding]) -> NebulaBridgeSummary:
    by_kind = {kind: 0 for kind in SUPPORTED_FINDING_KINDS}
    by_severity = {severity: 0 for severity in SUPPORTED_SEVERITIES}

    for finding in findings:
        by_kind[finding.kind] += 1
        by_severity[finding.severity] += 1

    return NebulaBridgeSummary(
        finding_count=len(findings),
        by_kind=by_kind,
        by_severity=by_severity,
    )
