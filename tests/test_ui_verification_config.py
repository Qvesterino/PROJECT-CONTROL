"""Focused tests for configurable UI verification profiles."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.config.ui_verification_config import (
    UISectionRule,
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