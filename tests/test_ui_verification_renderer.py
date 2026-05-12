"""Focused tests for UI verification report rendering."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.render.ui_verification_renderer import (
    render_ui_verification_console_summary,
    render_ui_verification_html,
    render_ui_verification_markdown,
    write_ui_verification_html_report,
    write_ui_verification_json_report,
    write_ui_verification_outputs,
)
from project_control.services.ui_verification_service import VerificationReport


class TestUIVerificationRenderer(TestCase):
    def _build_report(self) -> VerificationReport:
        report = VerificationReport(
            timestamp="2026-05-05T12:00:00Z",
            app_name="Demo UI",
            profile_name="demo",
            url="http://127.0.0.1:9000",
            browser="chromium",
            html_path="/tmp/index.html",
            manifest_path="/tmp/manifest.json",
            total=2,
            passed=1,
            failed=1,
            hidden_by_context=0,
            not_applicable=0,
            warned=0,
            elements=[
                {"id": "okButton", "section": "toolbar", "tag": "button", "type": None, "category": "button", "present": True, "visible": True, "interacted": True, "test_result": "pass", "notes": ["Clicked successfully"], "error": None, "sourcePath": "src/ui/toolbar.ts"},
                {"id": "badButton", "section": "toolbar", "tag": "button", "type": None, "category": "button", "present": True, "visible": True, "interacted": False, "test_result": "fail", "notes": [], "error": "Click failed", "sourcePath": "src/ui/toolbar.ts"},
            ],
            summary={
                "pass_rate": 50.0,
                "by_section": {"toolbar": {"total": 2, "pass": 1, "fail": 1, "warn": 0, "not-applicable": 0, "hidden-by-context": 0}},
            },
        )
        return report

    def test_console_summary_includes_failed_elements(self) -> None:
        report = self._build_report()
        text = render_ui_verification_console_summary(report)

        self.assertIn("Demo UI UI Verification", text)
        self.assertIn("FAILED ELEMENTS", text)
        self.assertIn("badButton", text)

    def test_html_renderer_includes_profile_metadata(self) -> None:
        report = self._build_report()
        html = render_ui_verification_html(report)

        self.assertIn("Demo UI UI Verification Report", html)
        self.assertIn("Profile: demo", html)
        self.assertIn("okButton", html)
        self.assertIn("badButton", html)

    def test_markdown_renderer_includes_summary_and_elements(self) -> None:
        report = self._build_report()
        markdown = render_ui_verification_markdown(report)

        self.assertIn("# UI Verification Report", markdown)
        self.assertIn("**Application:** Demo UI", markdown)
        self.assertIn("| toolbar | 2 | 1 | 1 | 0 | 0 | 0 |", markdown)
        self.assertIn("badButton", markdown)

    def test_json_and_html_writers_create_reports(self) -> None:
        report = self._build_report()
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            json_path = write_ui_verification_json_report(report, out_dir)
            html_path = write_ui_verification_html_report(report, out_dir)

            self.assertTrue(json_path.exists())
            self.assertTrue(html_path.exists())
            self.assertEqual(json_path.name, "ui_verification_data.json")
            self.assertEqual(html_path.name, "ui_verification_report.html")
            payload = json.loads(json_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["app_name"], "Demo UI")
            self.assertEqual(payload["elements"][0]["sourcePath"], "src/ui/toolbar.ts")

    def test_standard_writer_creates_markdown_json_and_optional_html(self) -> None:
        report = self._build_report()
        with tempfile.TemporaryDirectory() as temp_dir:
            out_dir = Path(temp_dir)
            markdown_path, json_path, html_path = write_ui_verification_outputs(report, out_dir, include_html=True)

            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(html_path is not None and html_path.exists())
            self.assertEqual(markdown_path.name, "ui_verification_report.md")
