from __future__ import annotations

import argparse
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from project_control.cli.menu import run_menu
from project_control.cli.router import (
    _handle_explore_command,
    _handle_wizard_command,
    _safe_print as router_safe_print,
    cmd_quick,
)
from project_control.cli.menu import _safe_print as menu_safe_print
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR


class CLIRuntimeFixTests(unittest.TestCase):
    def test_run_menu_starts_without_nameerror(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            buffer = io.StringIO()
            with patch("project_control.cli.menu.should_show_onboarding", return_value=False):
                with patch("project_control.cli.menu.should_run_wizard", return_value=False):
                    with patch("builtins.input", side_effect=["0"]):
                        with redirect_stdout(buffer):
                            run_menu(project_root)

        output = buffer.getvalue()
        self.assertIn("PROJECT CONTROL", output)
        self.assertIn("Goodbye.", output)

    def test_cmd_quick_uses_current_graph_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            exports_dir = control_dir / "exports"
            exports_dir.mkdir(parents=True, exist_ok=True)
            metrics_path = control_dir / "graph.metrics.json"
            metrics_path.write_text(
                json.dumps({"totals": {"nodeCount": 3, "edgeCount": 2}}),
                encoding="utf-8",
            )
            report_path = control_dir / "graph.report.md"
            report_path.write_text("# Graph Report\n", encoding="utf-8")
            graph_path = control_dir / "graph.snapshot.json"
            graph_path.write_text("{}", encoding="utf-8")

            args = argparse.Namespace(health=False, orphans=False, tree=False)
            buffer = io.StringIO()
            with patch("project_control.cli.router.PROJECT_DIR", project_root):
                with patch("project_control.cli.router.CONTROL_DIR", control_dir):
                    with patch("project_control.cli.router.EXPORTS_DIR", exports_dir):
                        with patch("project_control.cli.router.run_scan"):
                            with patch("project_control.cli.router.load_snapshot", return_value={"files": [{"path": "a.py"}]}):
                                with patch(
                                    "project_control.cli.router.run_ghost",
                                    return_value={
                                        "result": {},
                                        "counts": {
                                            "orphans": 0,
                                            "legacy": 0,
                                            "sessions": 0,
                                            "duplicates": 0,
                                            "semantic": 0,
                                        },
                                        "limit_violation": None,
                                    },
                                ):
                                    with patch("project_control.cli.router.write_ghost_report"):
                                        with patch(
                                            "project_control.cli.router.ensure_graph",
                                            return_value=(graph_path, metrics_path, report_path),
                                        ) as ensure_graph_mock:
                                            with redirect_stdout(buffer):
                                                result = cmd_quick(args)

            self.assertEqual(result, EXIT_OK)
            ensure_graph_mock.assert_called_once()
            self.assertIn("Graph built with 3 nodes", buffer.getvalue())

    def test_handle_wizard_command_uses_current_wizard_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = argparse.Namespace(project_root=temp_dir, reset=False)
            with patch("project_control.ui.wizard.run_wizard", return_value={"project_type": "js_ts"}):
                with patch("project_control.ui.wizard.mark_wizard_completed") as mark_mock:
                    result = _handle_wizard_command(args)

        self.assertEqual(result, EXIT_OK)
        mark_mock.assert_called_once()

    def test_handle_wizard_command_uses_error_handler_for_unexpected_errors(self) -> None:
        args = argparse.Namespace(project_root=".", reset=False)

        with patch("project_control.ui.wizard.run_wizard", side_effect=RuntimeError("boom")):
            with patch("project_control.cli.router.ErrorHandler.handle", return_value=EXIT_VALIDATION_ERROR) as handle_mock:
                result = _handle_wizard_command(args)

        self.assertEqual(result, EXIT_VALIDATION_ERROR)
        handle_mock.assert_called_once()

    def test_router_safe_print_handles_missing_stdout_encoding(self) -> None:
        dummy_stdout = type("DummyStdout", (), {"encoding": None})()
        unicode_error = UnicodeEncodeError("utf-8", "x", 0, 1, "boom")

        with patch.object(sys, "stdout", dummy_stdout):
            with patch("builtins.print", side_effect=[unicode_error, None]) as print_mock:
                router_safe_print("ž")

        self.assertEqual(print_mock.call_count, 2)

    def test_menu_safe_print_handles_missing_stdout_encoding(self) -> None:
        dummy_stdout = type("DummyStdout", (), {"encoding": None})()
        unicode_error = UnicodeEncodeError("utf-8", "x", 0, 1, "boom")

        with patch.object(sys, "stdout", dummy_stdout):
            with patch("builtins.print", side_effect=[unicode_error, None]) as print_mock:
                menu_safe_print("ž")

        self.assertEqual(print_mock.call_count, 2)

    def test_handle_explore_command_uses_central_error_handler_for_missing_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            args = argparse.Namespace(project_root=temp_dir, path="missing-file.py")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                result = _handle_explore_command(args)

        self.assertEqual(result, EXIT_VALIDATION_ERROR)
        self.assertIn("Explore path not found", stderr.getvalue())
