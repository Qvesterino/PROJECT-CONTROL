"""Retention detector for stale generated audits, reports, and exports."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from project_control.analysis.artifact_detector import (
    _build_grouped_entries,
    _bytes_to_mb,
    _effective_now,
    _is_referenced,
    _normalize_dir_pattern,
    _normalize_path,
    _parse_iso_datetime,
    _path_has_segment_pattern,
    _path_is_under,
    _read_git_signals,
    _git_supported,
)

if TYPE_CHECKING:
    from project_control.core.content_store import ContentStore


HIGH_CONFIDENCE_SCORE = 10
INTERNAL_GENERATED_DIRS = (".project-control/exports", ".project-control/out")


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, str]:
    return (-int(candidate["safe_to_delete"]), -int(candidate["score"]), candidate["path"])


def _family_sort_key(candidate: dict[str, Any]) -> tuple[float, str]:
    modified_at = _parse_iso_datetime(candidate.get("modified"))
    timestamp = modified_at.timestamp() if modified_at is not None else float("-inf")
    return (-timestamp, candidate["path"])


def _build_directory_space_savings(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        directory = str(candidate.get("directory") or ".")
        entry = grouped.setdefault(
            directory,
            {
                "directory": directory,
                "reclaimable_bytes": 0,
                "candidate_count": 0,
            },
        )
        entry["reclaimable_bytes"] += int(candidate.get("estimated_space_saved_bytes", 0))
        entry["candidate_count"] += 1

    results = [entry for entry in grouped.values() if entry["reclaimable_bytes"] > 0]
    for entry in results:
        entry["reclaimable_mb"] = _bytes_to_mb(int(entry["reclaimable_bytes"]))
    results.sort(key=lambda item: (-int(item["reclaimable_bytes"]), item["directory"]))
    return results


def _match_report_family(path_value: str, family_keywords: dict[str, list[str]]) -> str:
    lowered_path = path_value.lower()
    stem = Path(path_value).stem.lower()
    for family, keywords in family_keywords.items():
        for keyword in keywords:
            lowered_keyword = str(keyword).lower()
            if lowered_keyword and (lowered_keyword in lowered_path or lowered_keyword in stem):
                return family
    return "unknown"


def _build_duplicate_groups(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_sha: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        sha_value = candidate.get("sha256")
        if not sha_value:
            continue
        by_sha.setdefault(str(sha_value), []).append(candidate)

    duplicate_groups: list[dict[str, Any]] = []
    for sha_value in sorted(by_sha):
        members = by_sha[sha_value]
        if len(members) < 2:
            continue
        sorted_members = sorted(members, key=_candidate_sort_key)
        canonical = sorted_members[0]
        duplicate_paths = [item["path"] for item in sorted_members]
        duplicate_wasted_bytes = sum(int(item.get("size_bytes", 0)) for item in sorted_members[1:])
        group_id = sha_value[:12]
        safe_count = sum(1 for item in sorted_members if item.get("safe_to_delete"))
        duplicate_groups.append(
            {
                "duplicate_group_id": group_id,
                "sha256": sha_value,
                "count": len(sorted_members),
                "canonical_path": canonical["path"],
                "duplicate_paths": duplicate_paths,
                "safe_to_delete_count": safe_count,
                "total_size_bytes": sum(int(item.get("size_bytes", 0)) for item in sorted_members),
                "duplicate_wasted_bytes": duplicate_wasted_bytes,
            }
        )
        for member in sorted_members:
            member["duplicate_group_id"] = group_id
            member["duplicate_count"] = len(sorted_members)
            member["duplicate_paths"] = list(duplicate_paths)
            member["is_duplicate_canonical"] = member["path"] == canonical["path"]
            if not member["is_duplicate_canonical"]:
                member["estimated_space_saved_bytes"] = int(member.get("estimated_space_saved_bytes", 0)) + int(
                    member.get("size_bytes", 0)
                )
    duplicate_groups.sort(key=lambda item: (-item["safe_to_delete_count"], -item["count"], item["canonical_path"]))
    return duplicate_groups


def _build_why(candidate: dict[str, Any]) -> list[str]:
    reasons = set(candidate.get("reasons", []))
    why: list[str] = []
    if "internal_generated_directory" in reasons:
        why.append("Located in an internal generated output directory")
    if "suspicious_directory" in reasons:
        why.append("Located in a suspicious audit or report directory")
    if "family_keyword_match" in reasons:
        why.append(f"Matches the '{candidate.get('report_family', 'unknown')}' report family")
    if "older_than_threshold" in reasons:
        why.append("Older than configured retention threshold")
    if "not_referenced" in reasons:
        why.append("Not referenced anywhere in the repo")
    if "git_ignored_untracked" in reasons:
        why.append("Git ignored and not tracked")
    elif candidate.get("git_tracked") is True:
        why.append("Tracked by Git, so it is blocked from safe deletion")
    elif candidate.get("git_tracked") is False:
        why.append("Not tracked by Git")
    if "duplicate_content" in reasons:
        why.append(f"Duplicate report content found in {candidate.get('duplicate_count', 0)} files")
    if "newer_equivalent_exists" in reasons:
        why.append("A newer report of the same family exists")
    if candidate.get("retained_by_policy"):
        why.append("Retained by keep-latest policy")
    if "safe_directory" in reasons:
        why.append("Located under a configured safe documentation directory")
    if candidate.get("safe_to_delete"):
        why.append("Likely safe to delete because it is an old generated report outside the retention set")
    return why


def analyze(snapshot: dict[str, Any], patterns: dict[str, Any], content_store: "ContentStore") -> dict[str, Any]:
    """Analyze stale generated reports and return structured retention candidates."""
    config = patterns.get("audit_retention", {})
    if not isinstance(config, dict):
        config = {}

    extensions = {str(ext).lower() for ext in config.get("extensions", [])}
    suspicious_dirs = [_normalize_dir_pattern(item) for item in config.get("suspicious_dirs", [])]
    safe_dirs = [_normalize_dir_pattern(item) for item in config.get("safe_dirs", [])]
    family_keywords = {
        str(family): [str(keyword) for keyword in keywords]
        for family, keywords in config.get("family_keywords", {}).items()
        if isinstance(keywords, list)
    }
    older_than_days = int(config.get("older_than_days", 45))
    min_score = int(config.get("min_score", 8))
    keep_latest_per_family = int(config.get("keep_latest_per_family", 3))
    ignore_dirs = [_normalize_dir_pattern(item) for item in patterns.get("ignore_dirs", [])]
    project_root = content_store.snapshot_path.parent.parent
    reference_now = _effective_now(snapshot)
    git_supported = _git_supported(project_root)

    candidates: list[dict[str, Any]] = []

    for file_entry in snapshot.get("files", []):
        raw_path = file_entry.get("path")
        if not raw_path:
            continue

        path_value = _normalize_path(raw_path)
        path_obj = Path(path_value)
        extension = path_obj.suffix.lower()
        if extension not in extensions:
            continue

        filename = path_obj.name
        directory = path_obj.parent.as_posix() if path_obj.parent.as_posix() != "." else "."
        report_family = _match_report_family(path_value, family_keywords)
        score = 0
        reasons: list[str] = []

        suspicious_directory_match = any(_path_has_segment_pattern(path_value, hint) for hint in suspicious_dirs)
        if suspicious_directory_match:
            score += 4
            reasons.append("suspicious_directory")

        if any(_path_is_under(path_value, internal_dir) for internal_dir in INTERNAL_GENERATED_DIRS):
            score += 3
            reasons.append("internal_generated_directory")

        if report_family != "unknown":
            score += 4
            reasons.append("family_keyword_match")

        modified_at = _parse_iso_datetime(file_entry.get("modified"))
        age_days: int | None = None
        if modified_at is not None:
            age_days = max(0, (reference_now - modified_at).days)
            if age_days > older_than_days:
                score += 3
                reasons.append("older_than_threshold")

        referenced = _is_referenced(path_value, ignore_dirs, project_root)
        if referenced is False:
            score += 3
            reasons.append("not_referenced")

        git_tracked, git_ignored = _read_git_signals(path_value, project_root, git_supported)
        if git_tracked is False and git_ignored is True:
            score += 3
            reasons.append("git_ignored_untracked")

        safe_dir_match = next((safe_dir for safe_dir in safe_dirs if _path_is_under(path_value, safe_dir)), None)
        if safe_dir_match is not None:
            score -= 8
            reasons.append("safe_directory")

        candidates.append(
            {
                "path": path_value,
                "filename": filename,
                "directory": directory,
                "extension": extension,
                "sha256": file_entry.get("sha256"),
                "size_bytes": int(file_entry.get("size", 0)),
                "modified": file_entry.get("modified"),
                "age_days": age_days,
                "score": max(0, score),
                "referenced": referenced,
                "git_tracked": git_tracked,
                "git_ignored": git_ignored,
                "report_family": report_family,
                "newer_equivalent_exists": False,
                "retained_by_policy": False,
                "safe_dir_match": safe_dir_match,
                "safe_to_delete": False,
                "cleanup_confidence": "ignore",
                "classification": "ignore",
                "reasons": reasons,
                "why": [],
                "duplicate_group_id": None,
                "duplicate_count": 0,
                "duplicate_paths": [],
                "estimated_space_saved_bytes": 0,
                "is_duplicate_canonical": False,
            }
        )

    family_groups: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        family_groups.setdefault(candidate["report_family"], []).append(candidate)

    for family, members in family_groups.items():
        if family == "unknown":
            continue
        sorted_members = sorted(members, key=_family_sort_key)
        for index, member in enumerate(sorted_members):
            if index < keep_latest_per_family:
                member["retained_by_policy"] = True
                continue
            member["newer_equivalent_exists"] = True
            member["score"] += 4
            member["reasons"].append("newer_equivalent_exists")

    duplicate_index: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        sha_value = candidate.get("sha256")
        if not sha_value:
            continue
        duplicate_index.setdefault(str(sha_value), []).append(candidate)

    for members in duplicate_index.values():
        if len(members) < 2:
            continue
        for member in members:
            member["score"] += 3
            member["reasons"].append("duplicate_content")

    for candidate in candidates:
        recognized_family = candidate["report_family"] != "unknown"
        suspicious_or_family = any(
            reason in candidate["reasons"] for reason in ("suspicious_directory", "internal_generated_directory")
        ) or recognized_family
        candidate["score"] = max(0, int(candidate["score"]))
        candidate["safe_to_delete"] = bool(
            candidate["safe_dir_match"] is None
            and candidate["age_days"] is not None
            and int(candidate["age_days"]) > older_than_days
            and candidate["referenced"] is False
            and candidate["git_tracked"] is False
            and candidate["git_ignored"] is not False
            and suspicious_or_family
            and not candidate["retained_by_policy"]
        )
        if candidate["safe_to_delete"]:
            candidate["estimated_space_saved_bytes"] = int(candidate["size_bytes"])

    duplicate_groups = _build_duplicate_groups(candidates)

    for candidate in candidates:
        is_report_candidate = candidate["safe_to_delete"] or int(candidate["score"]) >= min_score
        candidate["is_report_candidate"] = is_report_candidate
        if candidate["safe_to_delete"]:
            candidate["cleanup_confidence"] = "safe"
            candidate["classification"] = "safe"
        elif int(candidate["score"]) >= HIGH_CONFIDENCE_SCORE:
            candidate["cleanup_confidence"] = "high"
            candidate["classification"] = "high_confidence"
        elif int(candidate["score"]) >= min_score:
            candidate["cleanup_confidence"] = "review"
            candidate["classification"] = "review"
        else:
            candidate["cleanup_confidence"] = "ignore"
            candidate["classification"] = "ignore"
        candidate["why"] = _build_why(candidate)

    candidates.sort(key=_candidate_sort_key)
    safe_to_delete_candidates = [candidate for candidate in candidates if candidate["safe_to_delete"]]
    high_confidence_cleanup_candidates = [
        candidate for candidate in candidates if candidate["cleanup_confidence"] == "high"
    ]
    review_candidates = [candidate for candidate in candidates if candidate["cleanup_confidence"] == "review"]
    report_candidates = [candidate for candidate in candidates if candidate.get("is_report_candidate")]
    delete_candidates = [candidate["path"] for candidate in safe_to_delete_candidates]

    safe_to_delete_bytes = sum(int(candidate.get("size_bytes", 0)) for candidate in safe_to_delete_candidates)
    duplicate_wasted_bytes = sum(int(group.get("duplicate_wasted_bytes", 0)) for group in duplicate_groups)
    families_detected = len({candidate["report_family"] for candidate in candidates if candidate["report_family"] != "unknown"})

    return {
        "summary": {
            "total_reports_scanned": len(candidates),
            "report_candidates": len(report_candidates),
            "safe_to_delete": len(safe_to_delete_candidates),
            "safe_to_delete_bytes": safe_to_delete_bytes,
            "safe_to_delete_mb": _bytes_to_mb(safe_to_delete_bytes),
            "high_confidence_cleanup_candidates": len(high_confidence_cleanup_candidates),
            "review_candidates": len(review_candidates),
            "duplicate_groups": len(duplicate_groups),
            "duplicate_wasted_bytes": duplicate_wasted_bytes,
            "families_detected": families_detected,
            "delete_candidates": len(delete_candidates),
        },
        "config_used": {
            "enabled": bool(config.get("enabled", True)),
            "older_than_days": older_than_days,
            "min_score": min_score,
            "keep_latest_per_family": keep_latest_per_family,
            "extensions": sorted(extensions),
            "suspicious_dirs": suspicious_dirs,
            "safe_dirs": safe_dirs,
            "family_keywords": family_keywords,
        },
        "candidates": candidates,
        "safe_to_delete_candidates": safe_to_delete_candidates,
        "high_confidence_cleanup_candidates": high_confidence_cleanup_candidates,
        "review_candidates": review_candidates,
        "grouped_by_family": _build_grouped_entries(report_candidates, "report_family"),
        "grouped_by_directory": _build_grouped_entries(report_candidates, "directory"),
        "duplicate_report_groups": duplicate_groups,
        "space_savings": {
            "safe_to_delete_bytes": safe_to_delete_bytes,
            "safe_to_delete_mb": _bytes_to_mb(safe_to_delete_bytes),
            "duplicate_wasted_bytes": duplicate_wasted_bytes,
            "duplicate_wasted_mb": _bytes_to_mb(duplicate_wasted_bytes),
            "top_space_saving_directories": _build_directory_space_savings(safe_to_delete_candidates),
        },
        "delete_candidates": delete_candidates,
    }
