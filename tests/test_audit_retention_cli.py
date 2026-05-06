from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from project_control.cli.router import cmd_audit_retention
from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.pc import build_parser


class AuditRetentionCLITests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        exports_dir = self.root / ".project-control" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        (exports_dir / "ghost_old.md").write_text("# old", encoding="utf-8")
        (exports_dir / "ghost_new.md").write_text("# new", encoding="utf-8")

        snapshot = scan_project(str(self.root), [".git"], [".md", ".json", ".txt"])
        snapshot["generated_at"] = "2026-05-06T00:00:00+00:00"
        for file_entry in snapshot["files"]:
            if file_entry["path"].endswith("ghost_old.md"):
                file_entry["modified"] = "2026-01-01T00:00:00+00:00"
            elif file_entry["path"].endswith("ghost_new.md"):
                file_entry["modified"] = "2026-05-05T00:00:00+00:00"
        save_snapshot(snapshot, self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parser_exposes_audit_retention_command(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["audits", "retention", "--older-than", "60", "--keep-latest", "1", "--by-family"])

        self.assertEqual(args.command, "audits")
        self.assertEqual(args.audits_cmd, "retention")
        self.assertEqual(args.older_than, 60)
        self.assertEqual(args.keep_latest, 1)
        self.assertTrue(args.by_family)

    def test_parser_rejects_conflicting_output_flags(self) -> None:
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["audits", "retention", "--json", "--delete-list"])

    def test_cli_command_writes_exports(self) -> None:
        args = Namespace(older_than=None, min_score=None, keep_latest=1, by_family=False, json=False, delete_list=False)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
                with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                    with redirect_stdout(buffer):
                        exit_code = cmd_audit_retention(args)

        self.assertEqual(exit_code, 0)

        export_dir = self.root / ".project-control" / "exports"
        markdown_path = export_dir / "audit_retention_candidates.md"
        json_path = export_dir / "audit_retention_candidates.json"
        delete_list_path = export_dir / "audit_delete_candidates.txt"

        self.assertTrue(markdown_path.exists())
        self.assertTrue(json_path.exists())
        self.assertTrue(delete_list_path.exists())

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("space_savings", payload)
        self.assertIn("duplicate_report_groups", payload)
        self.assertEqual(payload["summary"]["families_detected"], 1)
        self.assertIn("Safe To Delete Now", markdown_path.read_text(encoding="utf-8"))
        self.assertIn("Grouped By Family", markdown_path.read_text(encoding="utf-8"))

    def test_cli_json_flag_prints_exported_payload(self) -> None:
        args = Namespace(older_than=None, min_score=None, keep_latest=1, by_family=False, json=True, delete_list=False)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
                with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                    with redirect_stdout(buffer):
                        exit_code = cmd_audit_retention(args)

        self.assertEqual(exit_code, 0)
        payload = json.loads(buffer.getvalue())
        self.assertIn("summary", payload)
        self.assertIn("space_savings", payload)

    def test_cli_delete_list_flag_prints_paths(self) -> None:
        args = Namespace(older_than=None, min_score=None, keep_latest=1, by_family=False, json=False, delete_list=True)

        buffer = io.StringIO()
        with patch("project_control.cli.router.PROJECT_DIR", self.root):
            with patch("project_control.analysis.audit_retention_detector._is_referenced", return_value=False):
                with patch("project_control.analysis.audit_retention_detector._read_git_signals", return_value=(False, True)):
                    with redirect_stdout(buffer):
                        exit_code = cmd_audit_retention(args)

        self.assertEqual(exit_code, 0)
        self.assertEqual(buffer.getvalue().strip(), ".project-control/exports/ghost_old.md")


if __name__ == "__main__":
    unittest.main()
