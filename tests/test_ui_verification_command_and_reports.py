"""Browser-free integration tests for the first-class UI verification command and reports."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from project_control.cli.router import cmd_ui_verify
from project_control.config.ui_verification_config import UIVerificationProfileInfo
from project_control.services.report_service import (
    get_ui_verification_report_path,
    list_all_reports,
    view_ui_verification_report,
)
from project_control.services.ui_verification_service import VerificationReport


class UIVerificationCommandAndReportsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.export_dir = self.project_root / ".project-control" / "exports"
        self.export_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def _build_report(self) -> VerificationReport:
        return VerificationReport(
            timestamp="2026-05-05T12:00:00Z",
            app_name="Demo UI",
            profile_name="demo",
            url="http://127.0.0.1:9000",
            browser="chromium",
            html_path="/tmp/index.html",
            manifest_path=None,
            total=2,
            passed=1,
            failed=1,
            hidden_by_context=0,
            not_applicable=0,
            warned=0,
            elements=[],
            summary={"pass_rate": 50.0},
        )

    def test_cmd_ui_verify_prints_summary_and_paths(self) -> None:
        report = self._build_report()
        config_path = self.project_root / ".project-control" / "ui-verification.yaml"
        config_path.write_text("app_name: Demo UI\n", encoding="utf-8")
        markdown_path = self.export_dir / "ui_verification_report.md"
        markdown_path.write_text("# UI Verification Report\n", encoding="utf-8")
        json_path = self.export_dir / "ui_verification_data.json"
        json_path.write_text(json.dumps({"app_name": report.app_name, "summary": report.summary}), encoding="utf-8")
        html_path = self.export_dir / "ui_verification_report.html"
        html_path.write_text("<html></html>", encoding="utf-8")

        args = Namespace(
            project_root=str(self.project_root),
            config=None,
            url=None,
            image=None,
            screenshots=None,
            output=None,
            html=True,
            json=False,
            list_profiles=False,
            profile=None,
            headless=True,
            ui_cmd="verify",
        )

        buffer = io.StringIO()
        with patch(
            "project_control.cli.router.run_ui_verification_profile",
            return_value=(report, config_path, markdown_path, json_path, html_path),
        ):
            with redirect_stdout(buffer):
                exit_code = cmd_ui_verify(args)

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("Demo UI UI Verification", output)
        self.assertIn("UI verification report:", output)
        self.assertIn(str(markdown_path), output)

    def test_cmd_ui_verify_lists_profiles_in_text_mode(self) -> None:
        args = Namespace(
            project_root=str(self.project_root),
            config=None,
            profile=None,
            list_profiles=True,
            url=None,
            image=None,
            screenshots=None,
            output=None,
            html=False,
            json=False,
            headless=True,
            ui_cmd="verify",
        )

        buffer = io.StringIO()
        profiles = (
            UIVerificationProfileInfo(
                name="demo",
                app_name="Demo UI",
                path=self.project_root / ".project-control" / "ui-profiles" / "demo.yaml",
                source="project-profile",
                is_default=False,
                is_valid=True,
            ),
        )
        with patch("project_control.cli.router.list_ui_verification_profiles", return_value=profiles):
            with redirect_stdout(buffer):
                exit_code = cmd_ui_verify(args)

        output = buffer.getvalue()
        self.assertEqual(exit_code, 0)
        self.assertIn("UI VERIFICATION PROFILES", output)
        self.assertIn("demo", output)
        self.assertIn("Demo UI", output)

    def test_cmd_ui_verify_lists_profiles_in_json_mode(self) -> None:
        args = Namespace(
            project_root=str(self.project_root),
            config=None,
            profile=None,
            list_profiles=True,
            url=None,
            image=None,
            screenshots=None,
            output=None,
            html=False,
            json=True,
            headless=True,
            ui_cmd="verify",
        )

        buffer = io.StringIO()
        profiles = (
            UIVerificationProfileInfo(
                name="legacy-demo",
                app_name="Legacy Demo",
                path=self.project_root / ".project-control" / "ui-verification.yaml",
                source="legacy",
                is_default=True,
                is_valid=True,
            ),
        )
        with patch("project_control.cli.router.list_ui_verification_profiles", return_value=profiles):
            with redirect_stdout(buffer):
                exit_code = cmd_ui_verify(args)

        payload = json.loads(buffer.getvalue())
        self.assertEqual(exit_code, 0)
        self.assertEqual(payload[0]["name"], "legacy-demo")
        self.assertTrue(payload[0]["is_default"])

    def test_report_registry_includes_ui_verification(self) -> None:
        report_path = self.export_dir / "ui_verification_report.md"
        report_path.write_text("# UI Verification Report\n", encoding="utf-8")

        reports = list_all_reports(self.project_root)
        ui_reports = [report for report in reports if report["type"] == "ui_verification"]

        self.assertEqual(len(ui_reports), 1)
        self.assertEqual(ui_reports[0]["path"], get_ui_verification_report_path(self.project_root))

    def test_report_viewer_prints_ui_verification_content(self) -> None:
        report_path = self.export_dir / "ui_verification_report.md"
        report_path.write_text("# UI Verification Report\n\nDemo content\n", encoding="utf-8")
        (self.export_dir / "ui_verification_data.json").write_text(
            json.dumps(
                {
                    "app_name": "Demo UI",
                    "profile_name": "demo",
                    "passed": 1,
                    "failed": 1,
                    "hidden_by_context": 0,
                    "warned": 0,
                    "summary": {"pass_rate": 50.0},
                }
            ),
            encoding="utf-8",
        )

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            view_ui_verification_report(self.project_root, show_content=True)

        output = buffer.getvalue()
        self.assertIn("UI VERIFICATION REPORT", output)
        self.assertIn("FULL REPORT CONTENT", output)
        self.assertIn("Demo content", output)


if __name__ == "__main__":
    unittest.main()