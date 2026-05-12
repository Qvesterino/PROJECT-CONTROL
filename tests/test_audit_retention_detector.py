from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from project_control.analysis.audit_retention_detector import _read_git_signals, analyze
from project_control.config.patterns_loader import get_default_patterns
from project_control.core.content_store import ContentStore


def _build_snapshot(
    project_root: Path,
    files: list[dict[str, object]],
    *,
    generated_at: str = "2026-05-06T00:00:00+00:00",
) -> tuple[dict, ContentStore]:
    control_dir = project_root / ".project-control"
    content_dir = control_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    entries = []
    for file_info in files:
        path_value = Path(str(file_info["path"])).as_posix()
        data = bytes(file_info.get("bytes", b""))
        digest = sha256(data).hexdigest()
        (content_dir / f"{digest}.blob").write_bytes(data)
        entries.append(
            {
                "path": path_value,
                "size": int(file_info.get("size", len(data))),
                "modified": str(file_info.get("modified", "2026-05-05T00:00:00+00:00")),
                "sha256": digest,
            }
        )

    entries.sort(key=lambda item: item["path"])
    snapshot = {
        "snapshot_version": 1,
        "snapshot_id": "0" * 64,
        "generated_at": generated_at,
        "file_count": len(entries),
        "files": entries,
    }
    snapshot_path = control_dir / "snapshot.json"
    snapshot_path.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")
    return snapshot, ContentStore(snapshot, snapshot_path)


class AuditRetentionDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.patterns = get_default_patterns()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_generated_directory_and_family_add_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": ".project-control/exports/ghost_candidates.md", "bytes": b"ghost", "modified": "2026-01-01T00:00:00+00:00"}],
        )

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["report_family"], "ghost")
        self.assertIn("internal_generated_directory", candidate["reasons"])
        self.assertIn("family_keyword_match", candidate["reasons"])
        self.assertGreaterEqual(candidate["score"], 14)

    def test_safe_dir_suppresses_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "docs/reference/report.md", "bytes": b"report", "modified": "2026-01-01T00:00:00+00:00"}],
        )

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["safe_dir_match"], "docs/reference")
        self.assertIn("safe_directory", candidate["reasons"])
        self.assertFalse(candidate["safe_to_delete"])

    def test_internal_generated_reports_are_discovered_even_when_missing_from_snapshot(self) -> None:
        exports_dir = self.project_root / ".project-control" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        fallback_report = exports_dir / "ghost_candidates.md"
        fallback_report.write_text("# stale report\n", encoding="utf-8")

        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "src/index.ts", "bytes": b"export const ready = true;\n"}],
        )
        snapshot["generated_at"] = "2026-05-06T00:00:00+00:00"

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                result = analyze(snapshot, self.patterns, store)

        fallback_candidate = next(
            item for item in result["candidates"] if item["path"] == ".project-control/exports/ghost_candidates.md"
        )
        self.assertEqual(fallback_candidate["report_family"], "ghost")
        self.assertIn("internal_generated_directory", fallback_candidate["reasons"])

    def test_keep_latest_per_family_retains_newest_and_marks_older_safe(self) -> None:
        self.patterns["audit_retention"]["keep_latest_per_family"] = 1
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {"path": ".project-control/exports/ghost_2026-01-01.md", "bytes": b"ghost-old", "modified": "2026-01-01T00:00:00+00:00"},
                {"path": ".project-control/exports/ghost_2026-05-05.md", "bytes": b"ghost-new", "modified": "2026-05-05T00:00:00+00:00"},
            ],
        )

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                result = analyze(snapshot, self.patterns, store)

        by_path = {candidate["path"]: candidate for candidate in result["candidates"]}
        newest = by_path[".project-control/exports/ghost_2026-05-05.md"]
        oldest = by_path[".project-control/exports/ghost_2026-01-01.md"]
        self.assertTrue(newest["retained_by_policy"])
        self.assertFalse(newest["safe_to_delete"])
        self.assertTrue(oldest["newer_equivalent_exists"])
        self.assertTrue(oldest["safe_to_delete"])
        self.assertEqual(result["delete_candidates"], [".project-control/exports/ghost_2026-01-01.md"])

    def test_duplicate_reports_add_grouping_and_space_rollup(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {"path": ".project-control/exports/ui_verification_a.json", "bytes": b"same", "modified": "2026-01-01T00:00:00+00:00"},
                {"path": ".project-control/out/ui_verification_b.json", "bytes": b"same", "modified": "2026-01-02T00:00:00+00:00"},
            ],
        )

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                result = analyze(snapshot, self.patterns, store)

        groups = result["duplicate_report_groups"]
        self.assertEqual(len(groups), 1)
        self.assertEqual(groups[0]["count"], 2)
        self.assertEqual(result["summary"]["duplicate_groups"], 1)
        self.assertEqual(result["summary"]["duplicate_wasted_bytes"], len(b"same"))
        duplicate_candidates = [item for item in result["candidates"] if item["duplicate_count"] == 2]
        self.assertEqual(len(duplicate_candidates), 2)
        self.assertTrue(all("duplicate_content" in item["reasons"] for item in duplicate_candidates))

    def test_git_tracked_file_blocks_safe_to_delete(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": ".project-control/exports/checklist.md", "bytes": b"checklist", "modified": "2026-01-01T00:00:00+00:00"}],
        )

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(True, True)):
                result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertFalse(candidate["safe_to_delete"])
        self.assertEqual(result["delete_candidates"], [])
        self.assertIn("Tracked by Git, so it is blocked from safe deletion", candidate["why"])

    def test_sorting_is_deterministic(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {"path": ".project-control/exports/b/report.md", "bytes": b"one", "modified": "2026-01-01T00:00:00+00:00"},
                {"path": ".project-control/exports/a/report.md", "bytes": b"two", "modified": "2026-01-01T00:00:00+00:00"},
            ],
        )
        self.patterns["audit_retention"]["keep_latest_per_family"] = 0

        with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                result = analyze(snapshot, self.patterns, store)

        self.assertEqual(
            [item["path"] for item in result["candidates"]],
            [".project-control/exports/a/report.md", ".project-control/exports/b/report.md"],
        )


class AuditRetentionGitSignalTests(unittest.TestCase):
    def test_read_git_signals_returns_none_when_git_is_unavailable(self) -> None:
        with patch("project_control.analysis.artifact_detector.subprocess.run", side_effect=FileNotFoundError):
            tracked, ignored = _read_git_signals(".project-control/exports/file.md", Path("."))

        self.assertIsNone(tracked)
        self.assertIsNone(ignored)

    def test_read_git_signals_returns_none_when_not_git_repo(self) -> None:
        responses = [
            subprocess.CompletedProcess(
                ["git", "rev-parse", "--is-inside-work-tree"],
                128,
                stdout="",
                stderr="fatal: not a git repository",
            ),
        ]

        with patch("project_control.analysis.artifact_detector.subprocess.run", side_effect=responses):
            tracked, ignored = _read_git_signals(".project-control/exports/file.md", Path("."))

        self.assertIsNone(tracked)
        self.assertIsNone(ignored)


if __name__ == "__main__":
    unittest.main()
