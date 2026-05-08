"""Service wrapper for the Codebase Nebula bridge export."""

from __future__ import annotations

import json
import os
from argparse import Namespace
from contextlib import contextmanager
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterator

from project_control import __version__
from project_control.analysis.dead_analyzer import analyze_dead_code
from project_control.analysis.patterns_analyzer import analyze_patterns
from project_control.analysis.unused_analyzer import analyze_unused_systems
from project_control.config.patterns_loader import load_patterns
from project_control.core.artifact_service import run_artifact_hygiene
from project_control.core.content_store import ContentStore
from project_control.core.ghost import ghost
from project_control.core.markdown_renderer import SEVERITY_MAP
from project_control.core.pre_flight import require_healthy_snapshot
from project_control.core.project_initializer import ensure_project_initialized
from project_control.core.snapshot_service import load_snapshot
from project_control.nebula.schema import (
    NebulaBridgeBundle,
    NebulaBridgeFinding,
    NebulaBridgeMetadata,
    NebulaBridgeSnapshot,
    build_summary,
    normalize_project_root,
    normalize_relative_path,
    sort_findings,
)


@contextmanager
def _working_directory(path: Path) -> Iterator[None]:
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def _iso_utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _fallback_snapshot_id(snapshot: dict[str, Any]) -> str:
    files = snapshot.get("files", [])
    concatenated = "".join(
        f"{entry.get('path', '')}{entry.get('sha256', '')}"
        for entry in files
    )
    return sha256(concatenated.encode("utf-8")).hexdigest()


def _make_snapshot(snapshot: dict[str, Any]) -> NebulaBridgeSnapshot:
    return NebulaBridgeSnapshot(
        snapshot_id=str(snapshot.get("snapshot_id") or _fallback_snapshot_id(snapshot)),
        file_count=int(snapshot.get("file_count", len(snapshot.get("files", [])))),
    )


def _make_finding(
    *,
    finding_id: str,
    path: str,
    kind: str,
    severity: str,
    title: str,
    details: str,
    source: str,
    line: int | None = None,
    end_line: int | None = None,
    symbol: str | None = None,
    evidence: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> NebulaBridgeFinding:
    return NebulaBridgeFinding(
        id=finding_id,
        path=normalize_relative_path(path),
        kind=kind,
        severity=severity,
        title=title,
        details=details,
        source=source,
        line=line,
        end_line=end_line,
        symbol=symbol,
        evidence=evidence,
        tags=tags,
    )


def _ghost_findings(snapshot: dict[str, Any], patterns: dict[str, Any], content_store: ContentStore) -> list[NebulaBridgeFinding]:
    result = ghost(snapshot, patterns, content_store)
    findings: list[NebulaBridgeFinding] = []

    for path in sorted(result.get("orphans", [])):
        normalized_path = normalize_relative_path(path)
        findings.append(
            _make_finding(
                finding_id=f"ghost:{normalized_path}:orphan",
                path=normalized_path,
                kind="ghost",
                severity=SEVERITY_MAP["orphans"].lower(),
                title="Orphan file",
                details="File is not referenced by any known entrypoint.",
                source="pc ghost",
                evidence={"category": "orphans"},
                tags=["orphan"],
            )
        )

    for path in sorted(result.get("legacy", [])):
        normalized_path = normalize_relative_path(path)
        findings.append(
            _make_finding(
                finding_id=f"ghost:{normalized_path}:legacy",
                path=normalized_path,
                kind="ghost",
                severity=SEVERITY_MAP["legacy"].lower(),
                title="Legacy file",
                details="Path matches configured legacy patterns.",
                source="pc ghost",
                evidence={"category": "legacy"},
                tags=["legacy"],
            )
        )

    for path in sorted(result.get("sessions", [])):
        normalized_path = normalize_relative_path(path)
        findings.append(
            _make_finding(
                finding_id=f"ghost:{normalized_path}:session",
                path=normalized_path,
                kind="ghost",
                severity=SEVERITY_MAP["sessions"].lower(),
                title="Session file",
                details="Path looks like a session or temporary experiment file.",
                source="pc ghost",
                evidence={"category": "sessions"},
                tags=["session"],
            )
        )

    duplicate_pairs = sorted(
        [tuple(sorted((normalize_relative_path(left), normalize_relative_path(right)))) for left, right in result.get("duplicates", [])]
    )
    for left, right in duplicate_pairs:
        findings.append(
            _make_finding(
                finding_id=f"ghost:{left}:duplicate:{right}",
                path=left,
                kind="ghost",
                severity=SEVERITY_MAP["duplicates"].lower(),
                title="Duplicate basename candidate",
                details=f"File shares the same basename as {right}.",
                source="pc ghost",
                evidence={"category": "duplicates", "relatedPath": right},
                tags=["duplicate"],
            )
        )
        findings.append(
            _make_finding(
                finding_id=f"ghost:{right}:duplicate:{left}",
                path=right,
                kind="ghost",
                severity=SEVERITY_MAP["duplicates"].lower(),
                title="Duplicate basename candidate",
                details=f"File shares the same basename as {left}.",
                source="pc ghost",
                evidence={"category": "duplicates", "relatedPath": left},
                tags=["duplicate"],
            )
        )

    semantic_findings = sorted(
        [item for item in result.get("semantic", []) if isinstance(item, dict)],
        key=lambda item: (
            str(item.get("path", "")),
            str(item.get("type", "")),
            str(item.get("related_to", "")),
        ),
    )
    for item in semantic_findings:
        item_type = str(item.get("type") or "")
        path = item.get("path")
        if not path:
            continue
        normalized_path = normalize_relative_path(path)
        similarity = item.get("similarity")

        if item_type == "duplicate" and item.get("related_to"):
            related_path = normalize_relative_path(item["related_to"])
            details = f"File is semantically similar to {related_path}."
            evidence = {
                "category": "semantic_duplicates",
                "similarity": similarity,
                "relatedPath": related_path,
            }
            findings.append(
                _make_finding(
                    finding_id=f"ghost:{normalized_path}:semantic-duplicate:{related_path}",
                    path=normalized_path,
                    kind="ghost",
                    severity=SEVERITY_MAP["semantic"].lower(),
                    title="Semantic duplicate candidate",
                    details=details,
                    source="pc ghost",
                    evidence=evidence,
                    tags=["semantic", "duplicate"],
                )
            )
            findings.append(
                _make_finding(
                    finding_id=f"ghost:{related_path}:semantic-duplicate:{normalized_path}",
                    path=related_path,
                    kind="ghost",
                    severity=SEVERITY_MAP["semantic"].lower(),
                    title="Semantic duplicate candidate",
                    details=f"File is semantically similar to {normalized_path}.",
                    source="pc ghost",
                    evidence={
                        "category": "semantic_duplicates",
                        "similarity": similarity,
                        "relatedPath": normalized_path,
                    },
                    tags=["semantic", "duplicate"],
                )
            )
            continue

        findings.append(
            _make_finding(
                finding_id=f"ghost:{normalized_path}:semantic-orphan",
                path=normalized_path,
                kind="ghost",
                severity=SEVERITY_MAP["semantic"].lower(),
                title="Semantic orphan candidate",
                details="File has unusually low semantic similarity to the rest of the codebase.",
                source="pc ghost",
                evidence={
                    "category": "semantic_orphans",
                    "similarity": similarity,
                },
                tags=["semantic", "orphan"],
            )
        )

    return findings


def _dead_findings(snapshot: dict[str, Any], threshold: int = 2) -> list[NebulaBridgeFinding]:
    files = [entry.get("path") for entry in snapshot.get("files", []) if entry.get("path")]
    result = analyze_dead_code(files, low_usage_threshold=threshold)
    findings: list[NebulaBridgeFinding] = []

    for path in result.get("high", []):
        normalized_path = normalize_relative_path(path)
        findings.append(
            _make_finding(
                finding_id=f"dead:{normalized_path}:high",
                path=normalized_path,
                kind="dead",
                severity="high",
                title="Dead code candidate",
                details="File has zero or near-zero references in the repository.",
                source="pc dead",
                evidence={"bucket": "high", "threshold": threshold},
                tags=["dead-code"],
            )
        )

    for path in result.get("medium", []):
        normalized_path = normalize_relative_path(path)
        findings.append(
            _make_finding(
                finding_id=f"dead:{normalized_path}:medium",
                path=normalized_path,
                kind="dead",
                severity="medium",
                title="Low-usage file",
                details=f"File appears only a small number of times in the repository (<= {threshold} references).",
                source="pc dead",
                evidence={"bucket": "medium", "threshold": threshold},
                tags=["dead-code", "low-usage"],
            )
        )

    return findings


def _unused_system_findings(project_root: Path) -> list[NebulaBridgeFinding]:
    result = analyze_unused_systems(project_root)
    findings: list[NebulaBridgeFinding] = []

    for severity in ("high", "medium", "low"):
        for entry in result.get(severity, []):
            path = entry.get("file")
            if not path:
                continue
            normalized_path = normalize_relative_path(path)
            system_name = str(entry.get("system_name") or Path(normalized_path).stem)
            score = int(entry.get("score", 0))
            reasons = [str(reason) for reason in entry.get("reasons", [])]
            details = f"System {system_name} scored {score}/4 on unused-system heuristics."
            if reasons:
                details = f"{details} Reasons: {'; '.join(reasons)}."
            findings.append(
                _make_finding(
                    finding_id=f"unused_system:{normalized_path}:{severity}",
                    path=normalized_path,
                    kind="unused_system",
                    severity=severity,
                    title="Unused system candidate",
                    details=details,
                    source="pc unused",
                    symbol=system_name,
                    evidence={
                        "score": score,
                        "reasons": reasons,
                        "systemName": system_name,
                    },
                    tags=["unused-system"],
                )
            )

    return findings


def _pattern_findings(project_root: Path) -> list[NebulaBridgeFinding]:
    result = analyze_patterns(project_root)
    findings: list[NebulaBridgeFinding] = []

    for pattern_name, pattern_data in sorted(result.get("patterns", {}).items()):
        matches = sorted(
            pattern_data.get("matches", []),
            key=lambda match: (
                str(match.get("file", "")),
                int(match.get("line", 0) or 0),
                str(match.get("text", "")),
            ),
        )
        for match in matches:
            path = match.get("file")
            if not path:
                continue
            normalized_path = normalize_relative_path(path)
            line = int(match.get("line", 0) or 0) or None
            text = str(match.get("text") or "")
            findings.append(
                _make_finding(
                    finding_id=f"suspicious_pattern:{normalized_path}:{line or 0}:{pattern_name}",
                    path=normalized_path,
                    kind="suspicious_pattern",
                    severity="medium",
                    title=f"Suspicious pattern: {pattern_name}",
                    details=f"Matched configured suspicious pattern '{pattern_name}'.",
                    source="pc patterns",
                    line=line,
                    evidence={
                        "pattern": pattern_name,
                        "text": text,
                    },
                    tags=["pattern", pattern_name],
                )
            )

    return findings


def _artifact_severity(candidate: dict[str, Any]) -> str:
    if candidate.get("cleanup_confidence") == "high":
        return "medium"
    if candidate.get("safe_to_delete"):
        return "low"
    return "info"


def _artifact_findings(project_root: Path) -> list[NebulaBridgeFinding]:
    artifact_data = run_artifact_hygiene(Namespace(older_than=None, min_score=None), project_root)
    result = artifact_data["result"]
    findings: list[NebulaBridgeFinding] = []

    candidates = [candidate for candidate in result.get("candidates", []) if candidate.get("is_report_candidate")]
    candidates.sort(key=lambda candidate: str(candidate.get("path", "")))

    for candidate in candidates:
        path = candidate.get("path")
        if not path:
            continue
        normalized_path = normalize_relative_path(path)
        cleanup_confidence = str(candidate.get("cleanup_confidence") or "ignore")
        why = [str(item) for item in candidate.get("why", [])]
        details = why[0] if why else "Potential removable artifact detected by artifact hygiene analysis."
        findings.append(
            _make_finding(
                finding_id=f"artifact_hygiene:{normalized_path}:{cleanup_confidence}",
                path=normalized_path,
                kind="artifact_hygiene",
                severity=_artifact_severity(candidate),
                title="Artifact hygiene candidate",
                details=details,
                source="pc artifacts",
                evidence={
                    "score": int(candidate.get("score", 0)),
                    "cleanupConfidence": cleanup_confidence,
                    "safeToDelete": bool(candidate.get("safe_to_delete")),
                    "classification": candidate.get("classification"),
                    "why": why,
                    "sizeBytes": int(candidate.get("size_bytes", 0)),
                },
                tags=["artifact-hygiene", cleanup_confidence],
            )
        )

    return findings


def build_nebula_bridge(project_root: Path) -> dict[str, Any]:
    ensure_project_initialized(project_root)
    require_healthy_snapshot(project_root, operation="nebula export")

    snapshot = load_snapshot(project_root)
    patterns = load_patterns(project_root)
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    content_store = ContentStore(snapshot, snapshot_path)

    with _working_directory(project_root):
        findings = []
        findings.extend(_ghost_findings(snapshot, patterns, content_store))
        findings.extend(_dead_findings(snapshot))
        findings.extend(_unused_system_findings(project_root))
        findings.extend(_pattern_findings(project_root))
        findings.extend(_artifact_findings(project_root))

    sorted_findings = sort_findings(findings)
    bundle = NebulaBridgeBundle(
        generated_at=_iso_utc_now(),
        project_root=normalize_project_root(project_root),
        snapshot=_make_snapshot(snapshot),
        summary=build_summary(sorted_findings),
        findings=sorted_findings,
        traces=[],
        metadata=NebulaBridgeMetadata(pc_version=__version__),
    )
    return bundle.to_dict()


def run_nebula_export(project_root: Path, output_path: Path | None = None) -> tuple[dict[str, Any], Path]:
    payload = build_nebula_bridge(project_root)
    target_path = output_path or project_root / ".project-control" / "exports" / "nebula_bridge.json"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload, target_path