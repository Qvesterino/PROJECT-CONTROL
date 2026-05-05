"""Focused tests for configurable UI verification profiles."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.config.ui_verification_config import (
    UISectionRule,
    find_ui_verification_profile,
    get_default_ui_verification_config_path,
    get_ui_verification_profiles_dir,
    list_ui_verification_profiles,
    load_ui_verification_config,
)


class TestUIVerificationConfig(TestCase):
    def test_missing_profile_returns_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "missing.yaml"
            config = load_ui_verification_config(config_path)

            self.assertEqual(config.app_name, "UI Verification")
            self.assertEqual(config.profile_name, "default")
            self.assertEqual(config.html_path, (Path(temp_dir) / "index.html").resolve())
            self.assertEqual(config.image_path, (Path(temp_dir) / "assets" / "ATOMA.png").resolve())

    def test_profile_parses_relative_paths_and_hooks(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "profile.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "app_name: Demo UI",
                        "profile_name: demo",
                        "base_url: http://127.0.0.1:9000",
                        "html_path: fixtures/index.html",
                        "image_path: fixtures/image.png",
                        "manifest_path: fixtures/manifest.json",
                        "default_timeout_ms: 9000",
                        "interaction_timeout_ms: 1200",
                        "viewport:",
                        "  width: 800",
                        "  height: 600",
                        "preview_retest_sections:",
                        "  - preview",
                        "sections:",
                        "  - name: toolbar",
                        "    pattern: toolbarButton",
                        "import_steps:",
                        "  - action: wait_for",
                        "    selector: '#imageInput'",
                        "    state: visible",
                        "  - action: set_input_files",
                        "    selector: '#imageInput'",
                        "    value_from: image_path",
                        "preview_setup_steps:",
                        "  - action: click_if_visible",
                        "    selector: '#playButton'",
                        "preview_teardown_steps:",
                        "  - action: press_key",
                        "    key: Escape",
                        "test_values:",
                        "  color: '#00ff00'",
                        "  text: hello-world",
                        "  select_index: 2",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_ui_verification_config(config_path)

            self.assertEqual(config.app_name, "Demo UI")
            self.assertEqual(config.profile_name, "demo")
            self.assertEqual(config.base_url, "http://127.0.0.1:9000")
            self.assertEqual(config.html_path, (root / "fixtures" / "index.html").resolve())
            self.assertEqual(config.image_path, (root / "fixtures" / "image.png").resolve())
            self.assertEqual(config.manifest_path, (root / "fixtures" / "manifest.json").resolve())
            self.assertEqual(config.default_timeout_ms, 9000)
            self.assertEqual(config.interaction_timeout_ms, 1200)
            self.assertEqual(config.viewport.width, 800)
            self.assertEqual(config.viewport.height, 600)
            self.assertEqual(config.preview_retest_sections, ("preview",))
            self.assertEqual(config.test_values.color, "#00ff00")
            self.assertEqual(config.test_values.text, "hello-world")
            self.assertEqual(config.test_values.select_index, 2)
            self.assertEqual(config.sections, (UISectionRule(name="toolbar", pattern="toolbarButton"),))
            self.assertEqual(config.import_steps[1].value_from, "image_path")
            self.assertEqual(config.preview_setup_steps[0].action, "click_if_visible")
            self.assertEqual(config.preview_teardown_steps[0].key, "Escape")

    def test_unknown_hook_actions_are_ignored(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "profile.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "import_steps:",
                        "  - action: wait_for",
                        "    selector: '#imageInput'",
                        "  - action: run_shell",
                        "    selector: '#danger'",
                    ]
                ),
                encoding="utf-8",
            )

            config = load_ui_verification_config(config_path)

            self.assertEqual(len(config.import_steps), 1)
            self.assertEqual(config.import_steps[0].action, "wait_for")

    def test_list_ui_verification_profiles_discovers_legacy_and_directory_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            default_path = get_default_ui_verification_config_path(project_root)
            default_path.parent.mkdir(parents=True)
            default_path.write_text(
                "\n".join(
                    [
                        "app_name: Legacy Demo",
                        "profile_name: legacy-demo",
                    ]
                ),
                encoding="utf-8",
            )

            profiles_dir = get_ui_verification_profiles_dir(project_root)
            profiles_dir.mkdir(parents=True)
            (profiles_dir / "stage.yaml").write_text(
                "\n".join(
                    [
                        "app_name: Stage Demo",
                        "profile_name: stage",
                    ]
                ),
                encoding="utf-8",
            )

            profiles = list_ui_verification_profiles(project_root)

            self.assertEqual([profile.name for profile in profiles], ["legacy-demo", "stage"])
            self.assertEqual(profiles[0].source, "legacy")
            self.assertTrue(profiles[0].is_default)
            self.assertTrue(profiles[1].is_valid)

    def test_list_ui_verification_profiles_marks_invalid_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            profiles_dir = get_ui_verification_profiles_dir(project_root)
            profiles_dir.mkdir(parents=True)
            (profiles_dir / "broken.yaml").write_text("app_name: [broken\n", encoding="utf-8")

            profiles = list_ui_verification_profiles(project_root)

            self.assertEqual(len(profiles), 1)
            self.assertFalse(profiles[0].is_valid)
            self.assertIn("broken", profiles[0].name)
            self.assertIsNotNone(profiles[0].error)

    def test_list_ui_verification_profiles_marks_duplicate_names_invalid(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            profiles_dir = get_ui_verification_profiles_dir(project_root)
            profiles_dir.mkdir(parents=True)
            (profiles_dir / "one.yaml").write_text(
                "\n".join(
                    [
                        "app_name: Demo One",
                        "profile_name: demo",
                    ]
                ),
                encoding="utf-8",
            )
            (profiles_dir / "two.yaml").write_text(
                "\n".join(
                    [
                        "app_name: Demo Two",
                        "profile_name: demo",
                    ]
                ),
                encoding="utf-8",
            )

            profiles = list_ui_verification_profiles(project_root)

            self.assertEqual(len(profiles), 2)
            self.assertFalse(profiles[0].is_valid)
            self.assertFalse(profiles[1].is_valid)
            self.assertIn("Duplicate UI verification profile name", profiles[0].error)

    def test_find_ui_verification_profile_matches_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            profiles_dir = get_ui_verification_profiles_dir(project_root)
            profiles_dir.mkdir(parents=True)
            (profiles_dir / "demo.yaml").write_text(
                "\n".join(
                    [
                        "app_name: Demo UI",
                        "profile_name: demo",
                    ]
                ),
                encoding="utf-8",
            )

            profile = find_ui_verification_profile(project_root, "demo")

            self.assertIsNotNone(profile)
            self.assertEqual(profile.name, "demo")