"""Browser-free tests for reusable UI verification helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.config.ui_verification_config import (
    UISectionRule,
    UIVerificationConfig,
)
from project_control.services.ui_verification_service import (
    UIElement,
    discover_elements_from_html,
    summarize_verification,
)


class TestUIVerificationService(TestCase):
    def test_discover_elements_from_html_uses_configured_sections(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            html_path = Path(temp_dir) / "index.html"
            html_path.write_text(
                "\n".join(
                    [
                        '<button id="toolbarButton"></button>',
                        '<input id="speedInput" type="range" />',
                        '<input id="uploadInput" type="file" />',
                        '<select id="presetSelect"></select>',
                        '<button id="toolbarButton"></button>',
                    ]
                ),
                encoding="utf-8",
            )
            config = UIVerificationConfig(
                html_path=html_path,
                sections=(
                    UISectionRule(name="toolbar", pattern="toolbarButton"),
                    UISectionRule(name="preview", pattern="speedInput|presetSelect"),
                ),
            )

            elements = discover_elements_from_html(html_path, config)

            self.assertEqual([element.id for element in elements], ["toolbarButton", "speedInput", "uploadInput", "presetSelect"])
            self.assertEqual(elements[0].section, "toolbar")
            self.assertEqual(elements[1].category, "slider")
            self.assertEqual(elements[1].section, "preview")
            self.assertEqual(elements[2].category, "file")
            self.assertEqual(elements[3].category, "select")

    def test_summarize_verification_builds_section_and_category_stats(self) -> None:
        config = UIVerificationConfig(app_name="Demo", profile_name="demo", html_path=Path("index.html"))
        elements = [
            UIElement(id="a", tag="button", type=None, selector="#a", category="button", section="toolbar", test_result="pass"),
            UIElement(id="b", tag="button", type=None, selector="#b", category="button", section="toolbar", test_result="fail"),
            UIElement(id="c", tag="input", type="range", selector="#c", category="slider", section="preview", test_result="hidden-by-context"),
            UIElement(id="d", tag="input", type="file", selector="#d", category="file", section="imports", test_result="not-applicable"),
            UIElement(id="e", tag="select", type=None, selector="#e", category="select", section="preview", test_result="warn"),
        ]

        report = summarize_verification(config, "http://127.0.0.1:9000", elements)

        self.assertEqual(report.app_name, "Demo")
        self.assertEqual(report.profile_name, "demo")
        self.assertEqual(report.total, 5)
        self.assertEqual(report.passed, 1)
        self.assertEqual(report.failed, 1)
        self.assertEqual(report.hidden_by_context, 1)
        self.assertEqual(report.not_applicable, 1)
        self.assertEqual(report.warned, 1)
        self.assertEqual(report.summary["pass_rate"], 33.3)
        self.assertEqual(report.summary["by_section"]["toolbar"]["pass"], 1)
        self.assertEqual(report.summary["by_section"]["toolbar"]["fail"], 1)
        self.assertEqual(report.summary["by_category"]["button"]["total"], 2)