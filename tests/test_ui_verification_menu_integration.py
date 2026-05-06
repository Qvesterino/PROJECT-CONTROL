"""Focused menu integration tests for UI verification."""

from __future__ import annotations

import io
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from project_control.cli.menu import _quick_actions_menu, _quick_ui_verify, _reports_menu
from project_control.config.ui_verification_config import UIVerificationProfileInfo
from project_control.ui.state import AppState


def initialize_test_project(project_root: Path) -> None:
    control_dir = project_root / ".project-control"
    control_dir.mkdir(exist_ok=True)
    (control_dir / "status.yaml").write_text("tags: {}\n", encoding="utf-8")


class TestUIVerificationMenuIntegration(TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        initialize_test_project(self.project_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_quick_actions_menu_shows_ui_verify(self) -> None:
        buffer = io.StringIO()
        with patch("builtins.input", side_effect=["0"]):
            with redirect_stdout(buffer):
                _quick_actions_menu(self.project_root, AppState())

        output = buffer.getvalue()
        self.assertIn("UI Verify", output)

    def test_reports_menu_lists_ui_verification_report(self) -> None:
        export_dir = self.project_root / ".project-control" / "exports"
        export_dir.mkdir(parents=True)
        (export_dir / "ui_verification_report.md").write_text("# UI Verification Report\n", encoding="utf-8")

        buffer = io.StringIO()
        with patch("builtins.input", side_effect=[""]):
            with redirect_stdout(buffer):
                _reports_menu(self.project_root)

        output = buffer.getvalue()
        self.assertIn("UI Verification Report", output)

    def test_quick_ui_verify_uses_shared_service_path(self) -> None:
        config_path = self.project_root / ".project-control" / "ui-verification.yaml"
        config_path.write_text("app_name: Demo UI\n", encoding="utf-8")
        markdown_path = self.project_root / ".project-control" / "exports" / "ui_verification_report.md"
        json_path = self.project_root / ".project-control" / "exports" / "ui_verification_data.json"
        html_path = self.project_root / ".project-control" / "exports" / "ui_verification_report.html"

        buffer = io.StringIO()
        with patch(
            "project_control.cli.menu.run_ui_verification_profile",
            return_value=(object(), config_path, markdown_path, json_path, html_path),
        ) as run_mock:
            with patch("project_control.cli.menu.view_ui_verification_report") as view_mock:
                with patch(
                    "project_control.cli.menu.list_ui_verification_profiles",
                    return_value=(
                        UIVerificationProfileInfo(
                            name="ui-verification",
                            app_name="Demo UI",
                            path=config_path,
                            source="legacy",
                            is_default=True,
                            is_valid=True,
                        ),
                    ),
                ):
                    with patch("builtins.input", side_effect=[""]):
                        with redirect_stdout(buffer):
                                result_state = _quick_ui_verify(self.project_root, AppState())

        output = buffer.getvalue()
        self.assertIn("UI verification complete", output)
        run_mock.assert_called_once_with(self.project_root, profile_name="ui-verification", include_html=True)
        view_mock.assert_called_once_with(self.project_root, show_content=True)
        self.assertEqual(result_state.last_ui_verification_profile, "ui-verification")

    def test_quick_ui_verify_uses_remembered_profile_without_prompt(self) -> None:
        markdown_path = self.project_root / ".project-control" / "exports" / "ui_verification_report.md"
        json_path = self.project_root / ".project-control" / "exports" / "ui_verification_data.json"
        html_path = self.project_root / ".project-control" / "exports" / "ui_verification_report.html"
        profiles = (
            UIVerificationProfileInfo(
                name="alpha",
                app_name="Alpha UI",
                path=self.project_root / ".project-control" / "ui-profiles" / "alpha.yaml",
                source="project-profile",
                is_default=False,
                is_valid=True,
            ),
            UIVerificationProfileInfo(
                name="beta",
                app_name="Beta UI",
                path=self.project_root / ".project-control" / "ui-profiles" / "beta.yaml",
                source="project-profile",
                is_default=False,
                is_valid=True,
            ),
        )

        state = AppState(last_ui_verification_profile="beta")
        buffer = io.StringIO()
        with patch("project_control.cli.menu.list_ui_verification_profiles", return_value=profiles):
            with patch(
                "project_control.cli.menu.run_ui_verification_profile",
                return_value=(object(), profiles[1].path, markdown_path, json_path, html_path),
            ) as run_mock:
                with patch("project_control.cli.menu.view_ui_verification_report"):
                    with patch("builtins.input", side_effect=[""]):
                        with redirect_stdout(buffer):
                            result_state = _quick_ui_verify(self.project_root, state)

        run_mock.assert_called_once_with(self.project_root, profile_name="beta", include_html=True)
        self.assertEqual(result_state.last_ui_verification_profile, "beta")

    def test_quick_ui_verify_prompts_for_profile_when_multiple_valid_profiles_exist(self) -> None:
        markdown_path = self.project_root / ".project-control" / "exports" / "ui_verification_report.md"
        json_path = self.project_root / ".project-control" / "exports" / "ui_verification_data.json"
        html_path = self.project_root / ".project-control" / "exports" / "ui_verification_report.html"
        profiles = (
            UIVerificationProfileInfo(
                name="alpha",
                app_name="Alpha UI",
                path=self.project_root / ".project-control" / "ui-profiles" / "alpha.yaml",
                source="project-profile",
                is_default=False,
                is_valid=True,
            ),
            UIVerificationProfileInfo(
                name="beta",
                app_name="Beta UI",
                path=self.project_root / ".project-control" / "ui-profiles" / "beta.yaml",
                source="project-profile",
                is_default=False,
                is_valid=True,
            ),
        )

        buffer = io.StringIO()
        with patch("project_control.cli.menu.list_ui_verification_profiles", return_value=profiles):
            with patch(
                "project_control.cli.menu.run_ui_verification_profile",
                return_value=(object(), profiles[1].path, markdown_path, json_path, html_path),
            ) as run_mock:
                with patch("project_control.cli.menu.view_ui_verification_report"):
                    with patch("builtins.input", side_effect=["2", ""]):
                        with redirect_stdout(buffer):
                            result_state = _quick_ui_verify(self.project_root, AppState())

        run_mock.assert_called_once_with(self.project_root, profile_name="beta", include_html=True)
        self.assertEqual(result_state.last_ui_verification_profile, "beta")
