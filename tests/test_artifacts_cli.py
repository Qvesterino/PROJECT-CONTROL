from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from project_control.cli.router import cmd_artifacts
from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.pc import build_parser


class ArtifactsCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        (self.root / "test-results").mkdir(parents=True, exist_ok=True)
        (self.root / "test-results" / "test-failed-home.png").write_bytes(b"x" * (2 * 1024 * 1024))

        snapshot = scan_project(str(self.root), [".git", ".project-control"], [".png"])
        snapshot["generated_at"] = "2026-02-15T00:00:00+00:00"
        snapshot["files"][0]["modified"] = "2025-01-01T00:00:00+00:00"
        save_snapshot(snapshot, self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parser_exposes_artifacts_command(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["artifacts", "--older-than", "45", "--by-resolution"])

        self.assertEqual(args.command, "artifacts")
        self.assertEqual(args.older_than, 45)
        self.assertTrue(args.by_resolution)

    def test_parser_rejects_conflicting_output_flags(self) -> None:
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["artifacts", "--json", "--delete-list"])

    def test_cli_command_writes_exports(self) -> None:
        args = Namespace(older_than=None, min_score=None, by_resolution=False, json=False, delete_list=False)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with redirect_stdout(buffer):
                    exit_code = cmd_artifacts(args)

        self.assertEqual(exit_code, 0)

        export_dir = self.root / ".project-control" / "exports"
        markdown_path = export_dir / "artifact_candidates.md"
        json_path = export_dir / "artifact_candidates.json"
        delete_list_path = export_dir / "delete_candidates.txt"

        self.assertTrue(markdown_path.exists())
        self.assertTrue(json_path.exists())
        self.assertTrue(delete_list_path.exists())

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["safe_to_delete"], 1)
        self.assertIn("space_savings", payload)
        self.assertIn("duplicate_screenshot_groups", payload)
        self.assertIn("safe_to_delete_candidates", payload)
        self.assertEqual(payload["safe_to_delete_candidates"][0]["cleanup_confidence"], "safe")
        self.assertFalse(payload["safe_to_delete_candidates"][0]["git_tracked"])
        self.assertTrue(payload["safe_to_delete_candidates"][0]["git_ignored"])
        self.assertIn("why", payload["safe_to_delete_candidates"][0])
        self.assertGreaterEqual(payload["summary"]["safe_to_delete_mb"], 2.0)
        self.assertIn("Safe To Delete Now", markdown_path.read_text(encoding="utf-8"))
        self.assertIn("Space Savings", markdown_path.read_text(encoding="utf-8"))
        self.assertIn("Duplicate Screenshots", markdown_path.read_text(encoding="utf-8"))
        self.assertIn("test-results/test-failed-home.png", delete_list_path.read_text(encoding="utf-8"))

    def test_cli_json_flag_prints_exported_payload(self) -> None:
        args = Namespace(older_than=None, min_score=None, by_resolution=False, json=True, delete_list=False)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with redirect_stdout(buffer):
                    exit_code = cmd_artifacts(args)

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertIn("summary", payload)
        self.assertIn("space_savings", payload)
        self.assertIn("why", payload["safe_to_delete_candidates"][0])

    def test_cli_summary_mentions_space_savings_and_duplicate_groups(self) -> None:
        args = Namespace(older_than=None, min_score=None, by_resolution=False, json=False, delete_list=False)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with redirect_stdout(buffer):
                    exit_code = cmd_artifacts(args)

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Reclaimable MB:", output)
        self.assertIn("Duplicate groups:", output)

    def test_cli_delete_list_flag_prints_paths(self) -> None:
        args = Namespace(older_than=None, min_score=None, by_resolution=False, json=False, delete_list=True)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.artifact_detector._read_git_signals", return_value=(False, True)):
                with redirect_stdout(buffer):
                    exit_code = cmd_artifacts(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(buffer.getvalue().strip(), "test-results/test-failed-home.png")


if __name__ == "__main__":
    unittest.main()
