from __future__ import annotations

import io
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from project_control.cli.graph_cmd import graph_build
from project_control.cli.router import dispatch
from project_control.core.pre_flight import check_ripgrep_available, check_snapshot_valid


class ReleaseHardeningTests(unittest.TestCase):
    def test_check_ripgrep_available_handles_missing_binary(self) -> None:
        with patch("project_control.core.pre_flight.subprocess.run", side_effect=FileNotFoundError()):
            status = check_ripgrep_available()

        self.assertFalse(status.is_healthy)
        self.assertIn("Ripgrep not found", status.message)

    def test_check_snapshot_valid_uses_generated_at_for_staleness(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            control_dir.mkdir(parents=True, exist_ok=True)
            snapshot_path = control_dir / "snapshot.json"
            snapshot_path.write_text(
                (
                    "{\n"
                    '  "snapshot_version": 1,\n'
                    '  "snapshot_id": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",\n'
                    '  "generated_at": "2026-04-01T00:00:00+00:00",\n'
                    '  "file_count": 0,\n'
                    '  "files": []\n'
                    "}\n"
                ),
                encoding="utf-8",
            )

            with patch("project_control.core.pre_flight.datetime") as datetime_mock:
                datetime_mock.fromisoformat.side_effect = datetime.fromisoformat
                datetime_mock.now.return_value = datetime(2026, 5, 6, tzinfo=timezone.utc)
                status = check_snapshot_valid(project_root)

        self.assertTrue(status.is_healthy)
        self.assertIn("stale", status.message.lower())

    def test_dispatch_tui_runs_menu_without_deprecation_notice(self) -> None:
        args = Namespace(command="tui", tui_cmd=None)
        buffer = io.StringIO()

        with patch("project_control.cli.router.run_menu") as run_menu:
            with redirect_stdout(buffer):
                exit_code = dispatch(args)

        self.assertEqual(exit_code, 0)
        self.assertNotIn("deprecated", buffer.getvalue().lower())
        run_menu.assert_called_once()

    def test_dispatch_ui_alias_emits_deprecation_notice(self) -> None:
        args = Namespace(command="ui", ui_cmd=None)
        buffer = io.StringIO()

        with patch("project_control.cli.router.run_menu") as run_menu:
            with redirect_stdout(buffer):
                exit_code = dispatch(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("deprecated", buffer.getvalue().lower())
        self.assertIn("pc tui", buffer.getvalue())
        run_menu.assert_called_once()

    def test_graph_build_missing_snapshot_returns_validation_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            control_dir.mkdir(parents=True, exist_ok=True)
            (control_dir / "patterns.yaml").write_text("extensions: ['.py']\n", encoding="utf-8")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = graph_build(project_root, None)

        self.assertEqual(exit_code, 2)
        self.assertIn("pc scan", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
