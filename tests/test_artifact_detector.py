from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from hashlib import sha256
from pathlib import Path
from unittest.mock import patch

from project_control.analysis.artifact_detector import _read_git_signals, analyze
from project_control.config.patterns_loader import get_default_patterns
from project_control.core.content_store import ContentStore


def _build_snapshot(
    project_root: Path,
    files: list[dict[str, object]],
    *,
    generated_at: str = "2026-02-15T00:00:00+00:00",
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
                "modified": str(file_info.get("modified", "2026-02-14T00:00:00+00:00")),
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


class ArtifactDetectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.patterns = get_default_patterns()

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_suspicious_filename_keyword_adds_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "assets/screenshot.png", "bytes": b"png"}],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=True):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(None, None)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["score"], 4)
        self.assertIn("suspicious_filename_keyword", candidate["reasons"])
        self.assertFalse(candidate["safe_to_delete"])

    def test_playwright_directory_only_sets_generator_hint(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "test-results/output.png", "bytes": b"png", "modified": "2025-01-01T00:00:00+00:00"}],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["generator_hint"], "playwright")
        self.assertIn("playwright_directory", candidate["reasons"])
        self.assertNotIn("playwright_filename", candidate["reasons"])

    def test_playwright_filename_only_sets_generator_hint(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {"path": "images/test-failed-home.png", "bytes": b"b", "modified": "2025-01-01T00:00:00+00:00"},
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["generator_hint"], "playwright")
        self.assertIn("playwright_filename", candidate["reasons"])
        self.assertNotIn("playwright_directory", candidate["reasons"])

    def test_playwright_combo_bonus_and_sorting_are_deterministic(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {"path": "test-results/b/test-failed-home.png", "bytes": b"b", "modified": "2025-01-01T00:00:00+00:00"},
                {"path": "test-results/a/test-failed-home.png", "bytes": b"a", "modified": "2025-01-01T00:00:00+00:00"},
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        self.assertEqual(
            [item["path"] for item in result["candidates"]],
            ["test-results/a/test-failed-home.png", "test-results/b/test-failed-home.png"],
        )
        self.assertTrue(all("playwright_combo" in item["reasons"] for item in result["candidates"]))
        self.assertTrue(all(item["safe_to_delete"] for item in result["candidates"]))
        self.assertEqual(result["summary"]["duplicate_groups"], 0)

    def test_older_than_threshold_adds_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "assets/old.png", "bytes": b"old", "modified": "2025-01-01T00:00:00+00:00"}],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=True):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(None, None)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["score"], 2)
        self.assertIn("older_than_threshold", candidate["reasons"])

    def test_safe_dir_suppresses_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "public/assets/screenshot.png", "bytes": b"png"}],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertEqual(candidate["score"], 0)
        self.assertEqual(candidate["classification"], "ignore")
        self.assertEqual(candidate["safe_dir_match"], "public/assets")

    def test_reference_check_changes_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "images/logo.png", "bytes": b"logo"}],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    unreferenced = analyze(snapshot, self.patterns, store)["candidates"][0]

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=True):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    referenced = analyze(snapshot, self.patterns, store)["candidates"][0]

        self.assertEqual(unreferenced["score"], 3)
        self.assertEqual(referenced["score"], 0)

    def test_resolution_affects_score(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {"path": "images/screen.png", "bytes": b"screen"},
                {"path": "images/icon.png", "bytes": b"icon"},
            ],
        )
        metadata_by_path = {
            "images/screen.png": {"width": 1920, "height": 1080, "resolution": "1920x1080"},
            "images/icon.png": {"width": 64, "height": 64, "resolution": "64x64"},
        }

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=True):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(None, None)):
                with patch(
                    "project_control.analysis.artifact_detector.read_image_metadata",
                    side_effect=lambda path, image_bytes: metadata_by_path.get(path),
                ):
                    result = analyze(snapshot, self.patterns, store)

        scores = {item["path"]: item["score"] for item in result["candidates"]}
        self.assertEqual(scores["images/screen.png"], 3)
        self.assertEqual(scores["images/icon.png"], 0)

    def test_git_tracked_file_blocks_safe_to_delete(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {
                    "path": "test-results/test-failed-home.png",
                    "bytes": b"x" * (2 * 1024 * 1024),
                    "modified": "2025-01-01T00:00:00+00:00",
                }
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(True, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertFalse(candidate["safe_to_delete"])
        self.assertEqual(candidate["cleanup_confidence"], "high")
        self.assertEqual(result["delete_candidates"], [])

    def test_safe_to_delete_candidate_populates_safe_only_delete_list(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {
                    "path": "test-results/test-failed-home.png",
                    "bytes": b"x" * (2 * 1024 * 1024),
                    "modified": "2025-01-01T00:00:00+00:00",
                }
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["safe_to_delete_candidates"][0]
        self.assertTrue(candidate["safe_to_delete"])
        self.assertEqual(candidate["cleanup_confidence"], "safe")
        self.assertEqual(result["delete_candidates"], ["test-results/test-failed-home.png"])
        self.assertEqual(candidate["estimated_space_saved_bytes"], 2 * 1024 * 1024)
        self.assertIn("Likely safe to delete because it is an old untracked Playwright artifact", candidate["why"])

    def test_unignored_untracked_file_is_not_safe_to_delete(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [{"path": "test-results/test-failed-home.png", "bytes": b"x", "modified": "2025-01-01T00:00:00+00:00"}],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, False)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertFalse(candidate["safe_to_delete"])
        self.assertEqual(result["delete_candidates"], [])

    def test_duplicate_groups_add_metadata_and_space_rollups(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {
                    "path": "test-results/test-failed-home.png",
                    "bytes": b"same-bytes",
                    "modified": "2025-01-01T00:00:00+00:00",
                },
                {
                    "path": "playwright-report/retry-home.png",
                    "bytes": b"same-bytes",
                    "modified": "2025-01-01T00:00:00+00:00",
                },
                {
                    "path": "images/logo.png",
                    "bytes": b"logo",
                    "modified": "2025-01-01T00:00:00+00:00",
                },
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        groups = result["duplicate_screenshot_groups"]
        self.assertEqual(len(groups), 1)
        group = groups[0]
        self.assertEqual(group["count"], 2)
        self.assertEqual(group["duplicate_wasted_bytes"], len(b"same-bytes"))
        self.assertEqual(result["summary"]["duplicate_groups"], 1)
        self.assertEqual(result["summary"]["duplicate_wasted_bytes"], len(b"same-bytes"))
        self.assertEqual(result["space_savings"]["duplicate_wasted_bytes"], len(b"same-bytes"))

        duplicate_candidates = [item for item in result["candidates"] if item["duplicate_count"] == 2]
        self.assertEqual(len(duplicate_candidates), 2)
        self.assertTrue(all(item["duplicate_group_id"] for item in duplicate_candidates))
        self.assertTrue(any(item["is_duplicate_canonical"] for item in duplicate_candidates))
        self.assertTrue(any(not item["is_duplicate_canonical"] for item in duplicate_candidates))
        self.assertTrue(all("Duplicate image content found in 2 files" in item["why"] for item in duplicate_candidates))
        self.assertTrue(all("duplicate_content" in item["reasons"] for item in duplicate_candidates))

    def test_duplicate_playwright_bonus_strengthens_score_without_bypassing_safe_rules(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {
                    "path": "test-results/test-failed-home.png",
                    "bytes": b"same",
                    "modified": "2025-01-01T00:00:00+00:00",
                },
                {
                    "path": "test-results/test-failed-copy.png",
                    "bytes": b"same",
                    "modified": "2025-01-01T00:00:00+00:00",
                },
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, False)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        candidate = result["candidates"][0]
        self.assertGreaterEqual(candidate["score"], 22)
        self.assertIn("duplicate_playwright_bonus", candidate["reasons"])
        self.assertFalse(candidate["safe_to_delete"])
        self.assertEqual(result["delete_candidates"], [])

    def test_top_space_saving_directories_aggregate_safe_candidates(self) -> None:
        snapshot, store = _build_snapshot(
            self.project_root,
            [
                {
                    "path": "test-results/a/test-failed-home.png",
                    "bytes": b"a" * 10,
                    "modified": "2025-01-01T00:00:00+00:00",
                },
                {
                    "path": "test-results/a/test-failed-cart.png",
                    "bytes": b"b" * 20,
                    "modified": "2025-01-01T00:00:00+00:00",
                },
                {
                    "path": "playwright-report/test-failed-home.png",
                    "bytes": b"c" * 5,
                    "modified": "2025-01-01T00:00:00+00:00",
                },
            ],
        )

        with patch("project_control.analysis.artifact_detector._is_referenced", return_value=False):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with patch("project_control.analysis.artifact_detector.read_image_metadata", return_value=None):
                    result = analyze(snapshot, self.patterns, store)

        top_dirs = result["space_savings"]["top_space_saving_directories"]
        self.assertEqual(top_dirs[0]["directory"], "test-results/a")
        self.assertEqual(top_dirs[0]["reclaimable_bytes"], 30)
        self.assertEqual(top_dirs[0]["candidate_count"], 2)


class ArtifactDetectorGitSignalTests(unittest.TestCase):
    def test_read_git_signals_returns_none_when_git_is_unavailable(self) -> None:
        with patch("project_control.analysis.artifact_detector.subprocess.run", side_effect=FileNotFoundError):
            tracked, ignored = _read_git_signals("test-results/file.png", Path("."))

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
            tracked, ignored = _read_git_signals("test-results/file.png", Path("."))

        self.assertIsNone(tracked)
        self.assertIsNone(ignored)

    def test_read_git_signals_detects_tracked_file(self) -> None:
        responses = [
            subprocess.CompletedProcess(["git", "rev-parse", "--is-inside-work-tree"], 0, stdout="true\n", stderr=""),
            subprocess.CompletedProcess(["git", "ls-files", "--error-unmatch", "--", "file.png"], 0, stdout="file.png\n", stderr=""),
            subprocess.CompletedProcess(["git", "check-ignore", "--", "file.png"], 1, stdout="", stderr=""),
        ]

        with patch("project_control.analysis.artifact_detector.subprocess.run", side_effect=responses):
            tracked, ignored = _read_git_signals("file.png", Path("."))

        self.assertTrue(tracked)
        self.assertFalse(ignored)

    def test_read_git_signals_detects_ignored_untracked_file(self) -> None:
        responses = [
            subprocess.CompletedProcess(["git", "rev-parse", "--is-inside-work-tree"], 0, stdout="true\n", stderr=""),
            subprocess.CompletedProcess(["git", "ls-files", "--error-unmatch", "--", "file.png"], 1, stdout="", stderr=""),
            subprocess.CompletedProcess(["git", "check-ignore", "--", "file.png"], 0, stdout="file.png\n", stderr=""),
        ]

        with patch("project_control.analysis.artifact_detector.subprocess.run", side_effect=responses):
            tracked, ignored = _read_git_signals("file.png", Path("."))

        self.assertFalse(tracked)
        self.assertTrue(ignored)


if __name__ == "__main__":
    unittest.main()
