"""Browser-free tests for reusable UI verification helpers."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from project_control.config.ui_verification_config import (
    UISectionRule,
    UIVerificationConfig,
)
from project_control.services.ui_verification_service import (
    UIElement,
    discover_elements_from_html,
    get_default_ui_verification_config_path,
    list_ui_verification_profiles,
    resolve_ui_verification_config_path,
    run_ui_verification_profile,
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
            UIElement(id="a", tag="button", type=None, selector="#a", category="button", section="toolbar", source_path="src/ui/toolbar.ts", test_result="pass"),
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
        self.assertEqual(report.elements[0]["sourcePath"], "src/ui/toolbar.ts")

    def test_run_ui_verification_profile_requires_project_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)

            with self.assertRaises(RuntimeError) as context:
                run_ui_verification_profile(project_root)

            self.assertIn(str(get_default_ui_verification_config_path(project_root.resolve())), str(context.exception))

    def test_resolve_ui_verification_config_path_requires_selection_for_multiple_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            profiles_dir = project_root / ".project-control" / "ui-profiles"
            profiles_dir.mkdir(parents=True)
            (profiles_dir / "alpha.yaml").write_text("profile_name: alpha\napp_name: Alpha UI\n", encoding="utf-8")
            (profiles_dir / "beta.yaml").write_text("profile_name: beta\napp_name: Beta UI\n", encoding="utf-8")

            with self.assertRaises(RuntimeError) as context:
                resolve_ui_verification_config_path(project_root)

            self.assertIn("Multiple UI verification profiles found", str(context.exception))

    def test_resolve_ui_verification_config_path_selects_named_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            profiles_dir = project_root / ".project-control" / "ui-profiles"
            profiles_dir.mkdir(parents=True)
            selected_path = profiles_dir / "beta.yaml"
            (profiles_dir / "alpha.yaml").write_text("profile_name: alpha\napp_name: Alpha UI\n", encoding="utf-8")
            selected_path.write_text("profile_name: beta\napp_name: Beta UI\n", encoding="utf-8")

            resolved_path = resolve_ui_verification_config_path(project_root, profile_name="beta")

            self.assertEqual(resolved_path, selected_path.resolve())

    def test_list_ui_verification_profiles_passthrough_uses_config_discovery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            default_path = project_root / ".project-control" / "ui-verification.yaml"
            default_path.parent.mkdir(parents=True)
            default_path.write_text("profile_name: legacy\napp_name: Legacy UI\n", encoding="utf-8")

            profiles = list_ui_verification_profiles(project_root)

            self.assertEqual(len(profiles), 1)
            self.assertTrue(profiles[0].is_default)

    def test_run_ui_verification_profile_writes_standard_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            control_dir.mkdir()
            html_path = project_root / "index.html"
            html_path.write_text('<button id="okButton"></button>', encoding="utf-8")

            config_path = control_dir / "ui-verification.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "app_name: Demo UI",
                        "profile_name: demo",
                        "html_path: ../index.html",
                    ]
                ),
                encoding="utf-8",
            )

            report = summarize_verification(
                UIVerificationConfig(app_name="Demo UI", profile_name="demo", html_path=html_path),
                "http://127.0.0.1:9000",
                [
                    UIElement(
                        id="okButton",
                        tag="button",
                        type=None,
                        selector="#okButton",
                        category="button",
                        section="toolbar",
                        test_result="pass",
                    )
                ],
            )

            with patch("project_control.services.ui_verification_service.run_ui_verification", return_value=report):
                result, resolved_config, markdown_path, json_path, html_path = run_ui_verification_profile(
                    project_root,
                    profile_name="demo",
                    include_html=True,
                )

            self.assertEqual(result.app_name, "Demo UI")
            self.assertEqual(resolved_config, config_path.resolve())
            self.assertTrue(markdown_path.exists())
            self.assertTrue(json_path.exists())
            self.assertTrue(html_path is not None and html_path.exists())
            self.assertEqual(markdown_path.name, "ui_verification_report.md")
            self.assertEqual(json_path.name, "ui_verification_data.json")
