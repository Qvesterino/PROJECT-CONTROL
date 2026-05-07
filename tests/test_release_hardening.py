from __future__ import annotations

import io
import sys
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

from project_control.cli.graph_cmd import graph_build
from project_control.cli.router import dispatch
from project_control.core.pre_flight import HealthStatus, check_ripgrep_available, check_snapshot_valid, health_check
from project_control.pc import main as pc_main
from project_control.services.help_service import get_command_reference, get_keyboard_shortcuts_help, get_quick_start


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

    def test_removed_ui_command_prints_migration_error(self) -> None:
        stderr = io.StringIO()

        with patch.object(sys, "argv", ["pc", "ui"]):
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exit_info:
                    pc_main()

        self.assertEqual(exit_info.exception.code, 2)
        self.assertIn("pc ui was removed", stderr.getvalue())
        self.assertIn("pc tui", stderr.getvalue())

    def test_removed_ui_verify_command_points_to_tui_verify(self) -> None:
        stderr = io.StringIO()

        with patch.object(sys, "argv", ["pc", "ui", "verify"]):
            with redirect_stderr(stderr):
                with self.assertRaises(SystemExit) as exit_info:
                    pc_main()

        self.assertEqual(exit_info.exception.code, 2)
        self.assertIn("pc tui verify", stderr.getvalue())

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

    def test_help_content_prefers_tui_wording(self) -> None:
        self.assertIn("pc tui", get_quick_start())
        self.assertIn("pc tui", get_command_reference())
        self.assertIn("TUI", get_command_reference())
        self.assertIn("Quick Actions \u2192 10", get_keyboard_shortcuts_help())

    def test_health_check_treats_optional_dependencies_as_warnings(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            healthy = HealthStatus(name="ok", is_healthy=True, message="ok")
            rg_missing = HealthStatus(
                name="ripgrep",
                is_healthy=False,
                message="Ripgrep not found on PATH",
                suggestion="Install ripgrep",
                severity="warning",
            )
            ollama_missing = HealthStatus(
                name="ollama",
                is_healthy=False,
                message="Ollama not found (optional)",
                suggestion="Install Ollama",
                severity="warning",
            )

            with patch("project_control.core.pre_flight.check_project_initialized", return_value=healthy):
                with patch("project_control.core.pre_flight.check_snapshot_exists", return_value=healthy):
                    with patch("project_control.core.pre_flight.check_snapshot_valid", return_value=healthy):
                        with patch("project_control.core.pre_flight.check_graph_exists", return_value=healthy):
                            with patch("project_control.core.pre_flight.check_graph_valid", return_value=healthy):
                                with patch("project_control.core.pre_flight.check_config_valid", return_value=healthy):
                                    with patch("project_control.core.pre_flight.check_ripgrep_available", return_value=rg_missing):
                                        with patch("project_control.core.pre_flight.check_ollama_available", return_value=ollama_missing):
                                            with patch("project_control.core.pre_flight.check_disk_space", return_value=healthy):
                                                report = health_check(project_root)

        self.assertEqual(report.overall_status, "warning")
        self.assertEqual(report.errors, [])
        self.assertTrue(any("ripgrep" in warning.lower() for warning in report.warnings))
        self.assertTrue(any("ollama" in warning.lower() for warning in report.warnings))


if __name__ == "__main__":
    unittest.main()
