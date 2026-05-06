"""Artifact hygiene detector for temporary visual assets."""

from __future__ import annotations

import re
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from project_control.core.image_metadata import read_image_metadata
from project_control.utils.fs_helpers import run_rg

if TYPE_CHECKING:
    from project_control.core.content_store import ContentStore


HIGH_CONFIDENCE_SCORE = 10
FILENAME_KEYWORDS = ("screenshot", "image", "untitled", "playwright", "test-result")
NUMERIC_STEM_RE = re.compile(r"^\d+$")
HASH_STEM_RE = re.compile(r"^[a-f0-9]{8,}$", re.IGNORECASE)
PLAYWRIGHT_DIR_PATTERNS = (
    "test-results",
    "playwright-report",
    "playwright-artifacts",
    "playwright/.cache",
)
PLAYWRIGHT_FILENAME_PATTERNS = (
    re.compile(r".+-actual\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r".+-expected\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r".+-diff\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r"test-failed-.+\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r"retry.+\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r".+-chromium\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r".+-webkit\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r".+-firefox\.(png|jpe?g)$", re.IGNORECASE),
    re.compile(r"screenshot-.+\.(png|jpe?g)$", re.IGNORECASE),
)
ONE_MB = 1024 * 1024
FIVE_MB = 5 * ONE_MB


def _normalize_path(path_value: str) -> str:
    return Path(path_value).as_posix()


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _effective_now(snapshot: dict[str, Any]) -> datetime:
    return _parse_iso_datetime(snapshot.get("generated_at")) or datetime.now(timezone.utc)


def _normalize_dir_pattern(raw_value: str) -> str:
    return Path(raw_value.strip().strip("/")).as_posix().lower()


def _path_has_segment_pattern(path_value: str, pattern: str) -> bool:
    normalized_path = f"/{path_value.lower().strip('/')}/"
    normalized_pattern = f"/{pattern.strip('/')}/"
    return normalized_pattern in normalized_path


def _path_is_under(path_value: str, base_dir: str) -> bool:
    normalized_path = path_value.lower().strip("/")
    normalized_base = base_dir.strip("/")
    return normalized_path == normalized_base or normalized_path.startswith(f"{normalized_base}/")


def _reference_extra_args(ignore_dirs: list[str]) -> list[str]:
    args = ["--fixed-strings"]
    all_ignore_dirs = [".project-control", *ignore_dirs]
    seen: set[str] = set()
    for raw_dir in all_ignore_dirs:
        normalized = _normalize_dir_pattern(raw_dir)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        args.extend(["--glob", f"!{normalized}/**"])
        args.extend(["--glob", f"!**/{normalized}/**"])
    return args


def _is_referenced(path_value: str, ignore_dirs: list[str], project_root: Path) -> bool | None:
    if shutil.which("rg") is None:
        return None

    filename = Path(path_value).name
    extra_args = _reference_extra_args(ignore_dirs)
    for needle in (filename, path_value):
        if run_rg(needle, extra_args=extra_args, cwd=project_root).strip():
            return True
    return False


def _run_git_command(project_root: Path, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="ignore",
            cwd=str(project_root),
        )
    except FileNotFoundError:
        return None


def _git_supported(project_root: Path) -> bool:
    result = _run_git_command(project_root, ["rev-parse", "--is-inside-work-tree"])
    return result is not None and result.returncode == 0 and result.stdout.strip() == "true"


def _git_is_tracked(path_value: str, project_root: Path) -> bool | None:
    result = _run_git_command(project_root, ["ls-files", "--error-unmatch", "--", path_value])
    if result is None:
        return None
    if result.returncode == 0:
        return True
    return False


def _git_is_ignored(path_value: str, project_root: Path) -> bool | None:
    result = _run_git_command(project_root, ["check-ignore", "--", path_value])
    if result is None:
        return None
    if result.returncode == 0:
        return True
    return False


def _read_git_signals(
    path_value: str,
    project_root: Path,
    git_supported: bool | None = None,
) -> tuple[bool | None, bool | None]:
    if git_supported is None:
        git_supported = _git_supported(project_root)
    if not git_supported:
        return None, None
    return _git_is_tracked(path_value, project_root), _git_is_ignored(path_value, project_root)


def _has_playwright_directory(path_value: str) -> bool:
    return any(_path_has_segment_pattern(path_value, pattern) for pattern in PLAYWRIGHT_DIR_PATTERNS)


def _has_playwright_filename(filename: str) -> bool:
    return any(pattern.fullmatch(filename) for pattern in PLAYWRIGHT_FILENAME_PATTERNS)


def _candidate_sort_key(candidate: dict[str, Any]) -> tuple[int, int, str]:
    return (-int(candidate["safe_to_delete"]), -int(candidate["score"]), candidate["path"])


def _build_grouped_entries(candidates: list[dict[str, Any]], key_name: str) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for candidate in candidates:
        key = candidate.get(key_name) or "unknown"
        grouped.setdefault(str(key), []).append(candidate)

    entries: list[dict[str, Any]] = []
    for key in sorted(grouped):
        paths = [item["path"] for item in grouped[key]]
        entries.append(
            {
                key_name: key,
                "count": len(paths),
                "paths": sorted(paths),
            }
        )
    return entries


def _bytes_to_mb(size_bytes: int) -> float:
    return round(size_bytes / (1024 * 1024), 2)


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
            member["duplicate_wasted_bytes"] = duplicate_wasted_bytes
            member["is_duplicate_canonical"] = member["path"] == canonical["path"]
            if not member["is_duplicate_canonical"]:
                member["estimated_space_saved_bytes"] = int(member.get("estimated_space_saved_bytes", 0)) + int(
                    member.get("size_bytes", 0)
                )
    duplicate_groups.sort(key=lambda item: (-item["safe_to_delete_count"], -item["count"], item["canonical_path"]))
    return duplicate_groups


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


def _append_if(condition: bool, items: list[str], value: str) -> None:
    if condition:
        items.append(value)


def _build_why(candidate: dict[str, Any]) -> list[str]:
    reasons = set(candidate.get("reasons", []))
    why: list[str] = []
    _append_if("playwright_directory" in reasons, why, "Located in Playwright artifact output directory")
    _append_if("playwright_filename" in reasons, why, "Filename matches Playwright failure screenshot pattern")
    _append_if("playwright_combo" in reasons, why, "Path and filename both match Playwright artifact patterns")
    _append_if("suspicious_directory" in reasons, why, "Located in a suspicious artifact directory")
    _append_if("suspicious_filename_keyword" in reasons, why, "Filename looks like a temporary screenshot or debug image")
    _append_if("numeric_filename" in reasons, why, "Filename is purely numeric")
    _append_if("hash_like_filename" in reasons, why, "Filename looks hash-generated")
    _append_if("older_than_threshold" in reasons, why, "Older than configured threshold")
    _append_if("not_referenced" in reasons, why, "Not referenced anywhere in the repo")
    _append_if(
        "large_file_5mb" in reasons or "large_file_1mb" in reasons,
        why,
        "Large image file that can reclaim noticeable space",
    )
    _append_if("likely_screenshot_resolution" in reasons, why, "Resolution matches a common screenshot size")
    _append_if("likely_asset_resolution" in reasons, why, "Resolution matches a likely asset size")
    _append_if("safe_directory" in reasons, why, "Located under a configured safe asset directory")
    if candidate.get("git_tracked") is True:
        why.append("Tracked by Git, so it is blocked from safe deletion")
    elif candidate.get("git_ignored") is True and candidate.get("git_tracked") is False:
        why.append("Git ignored and not tracked")
    elif candidate.get("git_tracked") is False:
        why.append("Not tracked by Git")
    duplicate_count = int(candidate.get("duplicate_count", 0))
    if duplicate_count > 1:
        why.append(f"Duplicate image content found in {duplicate_count} files")
    if candidate.get("safe_to_delete"):
        if candidate.get("generator_hint") == "playwright":
            why.append("Likely safe to delete because it is an old untracked Playwright artifact")
        else:
            why.append("Likely safe to delete based on age, references, and Git state")
    return why


def analyze(snapshot: dict[str, Any], patterns: dict[str, Any], content_store: "ContentStore") -> dict[str, Any]:
    """Analyze visual artifacts and return structured cleanup candidates."""
    artifacts_config = patterns.get("artifacts", {})
    if not isinstance(artifacts_config, dict):
        artifacts_config = {}

    extensions = {str(ext).lower() for ext in artifacts_config.get("extensions", [])}
    suspicious_dirs = [_normalize_dir_pattern(item) for item in artifacts_config.get("suspicious_dirs", [])]
    safe_dirs = [_normalize_dir_pattern(item) for item in artifacts_config.get("safe_dirs", [])]
    likely_asset_resolutions = {str(item) for item in artifacts_config.get("likely_asset_resolutions", [])}
    likely_screenshot_resolutions = {str(item) for item in artifacts_config.get("likely_screenshot_resolutions", [])}
    older_than_days = int(artifacts_config.get("older_than_days", 30))
    min_score = int(artifacts_config.get("min_score", 8))
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
        stem = path_obj.stem.lower()
        directory = path_obj.parent.as_posix() if path_obj.parent.as_posix() != "." else ""
        score = 0
        reasons: list[str] = []
        playwright_directory_match = _has_playwright_directory(path_value)
        playwright_filename_match = _has_playwright_filename(filename)
        generator_hint: str | None = None

        if any(keyword in stem for keyword in FILENAME_KEYWORDS):
            score += 4
            reasons.append("suspicious_filename_keyword")

        if NUMERIC_STEM_RE.fullmatch(stem):
            score += 3
            reasons.append("numeric_filename")

        if HASH_STEM_RE.fullmatch(stem):
            score += 4
            reasons.append("hash_like_filename")

        if any(_path_has_segment_pattern(path_value, hint) for hint in suspicious_dirs):
            score += 4
            reasons.append("suspicious_directory")

        if playwright_directory_match:
            score += 5
            reasons.append("playwright_directory")
            generator_hint = "playwright"

        if playwright_filename_match:
            score += 5
            reasons.append("playwright_filename")
            generator_hint = "playwright"

        if playwright_directory_match and playwright_filename_match:
            score += 3
            reasons.append("playwright_combo")

        modified_at = _parse_iso_datetime(file_entry.get("modified"))
        age_days: int | None = None
        if modified_at is not None:
            age_days = max(0, (reference_now - modified_at).days)
            if age_days > older_than_days:
                score += 2
                reasons.append("older_than_threshold")

        size = int(file_entry.get("size", 0))
        if size >= FIVE_MB:
            score += 3
            reasons.append("large_file_5mb")
        elif size >= ONE_MB:
            score += 2
            reasons.append("large_file_1mb")

        referenced = _is_referenced(path_value, ignore_dirs, project_root)
        if referenced is False:
            score += 3
            reasons.append("not_referenced")

        git_tracked, git_ignored = _read_git_signals(path_value, project_root, git_supported)

        width: int | None = None
        height: int | None = None
        resolution: str | None = None
        try:
            image_bytes = content_store.get_bytes(path_value)
        except Exception:
            image_bytes = b""
        if image_bytes:
            metadata = read_image_metadata(path_value, image_bytes)
            if metadata is not None:
                width = int(metadata["width"])
                height = int(metadata["height"])
                resolution = str(metadata["resolution"])
                if resolution in likely_screenshot_resolutions:
                    score += 3
                    reasons.append("likely_screenshot_resolution")
                if resolution in likely_asset_resolutions:
                    score -= 3
                    reasons.append("likely_asset_resolution")

        safe_dir_match = next((safe_dir for safe_dir in safe_dirs if _path_is_under(path_value, safe_dir)), None)
        if safe_dir_match is not None:
            score -= 8
            reasons.append("safe_directory")

        score = max(0, score)
        safe_to_delete = (
            (playwright_directory_match or playwright_filename_match)
            and safe_dir_match is None
            and referenced is False
            and age_days is not None
            and age_days > older_than_days
            and git_tracked is False
            and git_ignored is not False
        )

        candidates.append(
            {
                "path": path_value,
                "filename": filename,
                "directory": directory or ".",
                "extension": extension,
                "sha256": file_entry.get("sha256"),
                "size_bytes": size,
                "modified": file_entry.get("modified"),
                "age_days": age_days,
                "score": score,
                "classification": "ignore",
                "cleanup_confidence": "ignore",
                "is_report_candidate": False,
                "referenced": referenced,
                "git_tracked": git_tracked,
                "git_ignored": git_ignored,
                "width": width,
                "height": height,
                "resolution": resolution,
                "generator_hint": generator_hint,
                "safe_dir_match": safe_dir_match,
                "safe_to_delete": safe_to_delete,
                "reasons": reasons,
                "why": [],
                "duplicate_group_id": None,
                "duplicate_count": 0,
                "duplicate_paths": [],
                "duplicate_wasted_bytes": 0,
                "estimated_space_saved_bytes": size if safe_to_delete else 0,
                "is_duplicate_canonical": False,
            }
        )

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
            if member.get("generator_hint") == "playwright":
                member["score"] += 2
                member["reasons"].append("duplicate_playwright_bonus")

    for candidate in candidates:
        candidate["score"] = max(0, int(candidate["score"]))
        candidate["is_report_candidate"] = bool(candidate["safe_to_delete"] or int(candidate["score"]) >= min_score)
        if candidate["safe_to_delete"]:
            candidate["cleanup_confidence"] = "safe"
            candidate["classification"] = "safe"
        elif int(candidate["score"]) >= HIGH_CONFIDENCE_SCORE:
            candidate["cleanup_confidence"] = "high"
            candidate["classification"] = "high_confidence"
        elif int(candidate["score"]) >= min_score:
            candidate["cleanup_confidence"] = "review"
            candidate["classification"] = "review"
        candidate["why"] = _build_why(candidate)

    duplicate_groups = _build_duplicate_groups(candidates)
    for candidate in candidates:
        candidate["why"] = _build_why(candidate)

    candidates.sort(key=_candidate_sort_key)
    safe_to_delete_candidates = [candidate for candidate in candidates if candidate["safe_to_delete"]]
    high_confidence_cleanup_candidates = [
        candidate for candidate in candidates if candidate["cleanup_confidence"] == "high"
    ]
    review_candidates = [candidate for candidate in candidates if candidate["cleanup_confidence"] == "review"]
    report_candidates = [candidate for candidate in candidates if candidate["is_report_candidate"]]
    delete_candidates = [candidate["path"] for candidate in safe_to_delete_candidates]

    safe_to_delete_bytes = sum(int(candidate.get("size_bytes", 0)) for candidate in safe_to_delete_candidates)
    duplicate_wasted_bytes = sum(int(group.get("duplicate_wasted_bytes", 0)) for group in duplicate_groups)
    top_space_saving_directories = _build_directory_space_savings(safe_to_delete_candidates)

    return {
        "summary": {
            "total_assets_scanned": len(candidates),
            "report_candidates": len(report_candidates),
            "safe_to_delete": len(safe_to_delete_candidates),
            "safe_to_delete_bytes": safe_to_delete_bytes,
            "safe_to_delete_mb": _bytes_to_mb(safe_to_delete_bytes),
            "high_confidence_cleanup_candidates": len(high_confidence_cleanup_candidates),
            "review_candidates": len(review_candidates),
            "duplicate_groups": len(duplicate_groups),
            "duplicate_wasted_bytes": duplicate_wasted_bytes,
            "delete_candidates": len(delete_candidates),
        },
        "config_used": {
            "enabled": bool(artifacts_config.get("enabled", True)),
            "older_than_days": older_than_days,
            "min_score": min_score,
            "extensions": sorted(extensions),
            "suspicious_dirs": suspicious_dirs,
            "safe_dirs": safe_dirs,
            "likely_asset_resolutions": sorted(likely_asset_resolutions),
            "likely_screenshot_resolutions": sorted(likely_screenshot_resolutions),
        },
        "candidates": candidates,
        "safe_to_delete_candidates": safe_to_delete_candidates,
        "high_confidence_cleanup_candidates": high_confidence_cleanup_candidates,
        "review_candidates": review_candidates,
        "duplicate_screenshot_groups": duplicate_groups,
        "space_savings": {
            "safe_to_delete_bytes": safe_to_delete_bytes,
            "safe_to_delete_mb": _bytes_to_mb(safe_to_delete_bytes),
            "duplicate_wasted_bytes": duplicate_wasted_bytes,
            "duplicate_wasted_mb": _bytes_to_mb(duplicate_wasted_bytes),
            "top_space_saving_directories": top_space_saving_directories,
        },
        "grouped_by_resolution": _build_grouped_entries(report_candidates, "resolution"),
        "grouped_by_directory": _build_grouped_entries(report_candidates, "directory"),
        "delete_candidates": delete_candidates,
    }
