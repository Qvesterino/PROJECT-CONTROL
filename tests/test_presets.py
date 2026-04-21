"""Tests for Project Presets system."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.config.presets import (
    BUILTIN_PRESETS,
    FULL_STACK_PRESET,
    REACT_FRONTEND_PRESET,
    PYTHON_BACKEND_PRESET,
    PresetConfig,
    PresetManager,
)


class TestPresetConfig(TestCase):
    """Test PresetConfig dataclass."""

    def test_create_preset(self) -> None:
        """Test creating a preset config."""
        preset = PresetConfig(
            name="test",
            description="Test preset",
            category="custom"
        )
        self.assertEqual(preset.name, "test")
        self.assertEqual(preset.description, "Test preset")
        self.assertEqual(preset.category, "custom")

    def test_preset_with_configs(self) -> None:
        """Test preset with patterns and graph config."""
        patterns = {"extensions": [".py"]}
        graph_config = {"languages": {"python": {"enabled": True}}}

        preset = PresetConfig(
            name="test",
            description="Test",
            patterns=patterns,
            graph_config=graph_config
        )

        self.assertEqual(preset.patterns, patterns)
        self.assertEqual(preset.graph_config, graph_config)


class TestBuiltinPresets(TestCase):
    """Test built-in presets."""

    def test_react_frontend_preset_exists(self) -> None:
        """Test React Frontend preset exists."""
        self.assertIn("react-frontend", BUILTIN_PRESETS)
        preset = BUILTIN_PRESETS["react-frontend"]
        self.assertEqual(preset.category, "builtin")
        self.assertIn("React", preset.description)

    def test_python_backend_preset_exists(self) -> None:
        """Test Python Backend preset exists."""
        self.assertIn("python-backend", BUILTIN_PRESETS)
        preset = BUILTIN_PRESETS["python-backend"]
        self.assertEqual(preset.category, "builtin")
        self.assertIn("Python", preset.description)

    def test_full_stack_preset_exists(self) -> None:
        """Test Full Stack preset exists."""
        self.assertIn("full-stack", BUILTIN_PRESETS)
        preset = BUILTIN_PRESETS["full-stack"]
        self.assertEqual(preset.category, "builtin")
        self.assertIn("Full stack", preset.description)

    def test_react_preset_has_correct_configs(self) -> None:
        """Test React preset has appropriate configurations."""
        preset = REACT_FRONTEND_PRESET

        # Should have JS/TS extensions
        self.assertIn(".js", preset.patterns["extensions"])
        self.assertIn(".ts", preset.patterns["extensions"])
        self.assertIn(".tsx", preset.patterns["extensions"])

        # Should ignore node_modules
        self.assertIn("node_modules", preset.patterns["ignore_dirs"])

        # JS/TS should be enabled in graph config
        self.assertTrue(preset.graph_config["languages"]["js_ts"]["enabled"])
        self.assertFalse(preset.graph_config["languages"]["python"]["enabled"])

    def test_python_preset_has_correct_configs(self) -> None:
        """Test Python preset has appropriate configurations."""
        preset = PYTHON_BACKEND_PRESET

        # Should have .py extension
        self.assertIn(".py", preset.patterns["extensions"])

        # Should ignore __pycache__
        self.assertIn("__pycache__", preset.patterns["ignore_dirs"])

        # Python should be enabled in graph config
        self.assertTrue(preset.graph_config["languages"]["python"]["enabled"])
        self.assertFalse(preset.graph_config["languages"]["js_ts"]["enabled"])

    def test_full_stack_preset_enables_both(self) -> None:
        """Test Full Stack preset enables both languages."""
        preset = FULL_STACK_PRESET

        # Both should be enabled
        self.assertTrue(preset.graph_config["languages"]["js_ts"]["enabled"])
        self.assertTrue(preset.graph_config["languages"]["python"]["enabled"])

        # Should have both types of extensions
        self.assertIn(".js", preset.patterns["extensions"])
        self.assertIn(".py", preset.patterns["extensions"])


class TestPresetManager(TestCase):
    """Test PresetManager class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.manager = PresetManager(self.project_root)

    def tearDown(self) -> None:
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_list_presets_includes_builtin(self) -> None:
        """Test listing presets includes built-in presets."""
        presets = self.manager.list_presets()

        preset_names = [p["name"] for p in presets]
        self.assertIn("react-frontend", preset_names)
        self.assertIn("python-backend", preset_names)
        self.assertIn("full-stack", preset_names)

    def test_list_presets_structure(self) -> None:
        """Test preset list has correct structure."""
        presets = self.manager.list_presets()

        for preset in presets:
            self.assertIn("name", preset)
            self.assertIn("description", preset)
            self.assertIn("category", preset)

    def test_get_builtin_preset(self) -> None:
        """Test getting a built-in preset."""
        preset = self.manager.get_preset("react-frontend")

        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, "react-frontend")
        self.assertEqual(preset.category, "builtin")

    def test_get_nonexistent_preset(self) -> None:
        """Test getting a non-existent preset."""
        preset = self.manager.get_preset("nonexistent")
        self.assertIsNone(preset)

    def test_apply_preset_creates_files(self) -> None:
        """Test applying a preset creates config files."""
        self.manager.apply_preset("react-frontend", backup=False)

        self.assertTrue(self.manager.patterns_file.exists())
        self.assertTrue(self.manager.graph_config_file.exists())

    def test_apply_preset_writes_correct_content(self) -> None:
        """Test applying a preset writes correct content."""
        self.manager.apply_preset("python-backend", backup=False)

        import yaml
        patterns = yaml.safe_load(self.manager.patterns_file.read_text(encoding="utf-8"))
        graph_config = yaml.safe_load(self.manager.graph_config_file.read_text(encoding="utf-8"))

        # Check patterns
        self.assertIn(".py", patterns["extensions"])
        self.assertIn("__pycache__", patterns["ignore_dirs"])

        # Check graph config
        self.assertTrue(graph_config["languages"]["python"]["enabled"])

    def test_apply_preset_with_backup(self) -> None:
        """Test applying preset creates backup."""
        # Create initial config
        self.manager.patterns_file.parent.mkdir(parents=True, exist_ok=True)
        self.manager.patterns_file.write_text("test: value", encoding="utf-8")

        # Apply preset with backup
        self.manager.apply_preset("react-frontend", backup=True)

        # Backup should exist
        backup_dir = self.manager.control_dir / "backups"
        self.assertTrue(backup_dir.exists())
        backup_files = list(backup_dir.glob("*.bak"))
        self.assertTrue(len(backup_files) > 0)

    def test_save_custom_preset(self) -> None:
        """Test saving a custom preset."""
        patterns = {"extensions": [".custom"]}
        graph_config = {"languages": {"js_ts": {"enabled": True}}}

        result = self.manager.save_custom_preset(
            name="my-preset",
            description="My custom preset",
            patterns=patterns,
            graph_config=graph_config
        )

        self.assertTrue(result)

        # Check file was created
        preset_file = self.manager.presets_dir / "my-preset.json"
        self.assertTrue(preset_file.exists())

        # Check content
        data = json.loads(preset_file.read_text(encoding="utf-8"))
        self.assertEqual(data["name"], "my-preset")
        self.assertEqual(data["description"], "My custom preset")
        self.assertEqual(data["patterns"], patterns)
        self.assertEqual(data["graph_config"], graph_config)

    def test_list_presets_includes_custom(self) -> None:
        """Test listing presets includes custom presets."""
        self.manager.save_custom_preset(
            name="custom-test",
            description="Test custom preset"
        )

        presets = self.manager.list_presets()
        preset_names = [p["name"] for p in presets]
        self.assertIn("custom-test", preset_names)

    def test_get_custom_preset(self) -> None:
        """Test getting a custom preset."""
        self.manager.save_custom_preset(
            name="custom-test",
            description="Test"
        )

        preset = self.manager.get_preset("custom-test")
        self.assertIsNotNone(preset)
        self.assertEqual(preset.name, "custom-test")
        self.assertEqual(preset.category, "custom")

    def test_delete_custom_preset(self) -> None:
        """Test deleting a custom preset."""
        self.manager.save_custom_preset(name="to-delete", description="Test")

        result = self.manager.delete_custom_preset("to-delete")
        self.assertTrue(result)

        preset = self.manager.get_preset("to-delete")
        self.assertIsNone(preset)

    def test_cannot_delete_builtin_preset(self) -> None:
        """Test that built-in presets cannot be deleted."""
        result = self.manager.delete_custom_preset("react-frontend")
        self.assertFalse(result)

        # Preset should still exist
        preset = self.manager.get_preset("react-frontend")
        self.assertIsNotNone(preset)

    def test_get_current_preset_name(self) -> None:
        """Test detecting current preset from configuration."""
        # Apply a preset
        self.manager.apply_preset("react-frontend", backup=False)

        # Should detect the preset
        current = self.manager.get_current_preset_name()
        self.assertEqual(current, "react-frontend")

    def test_get_current_preset_none_when_custom(self) -> None:
        """Test returns None when configuration doesn't match any preset."""
        # Create custom config
        self.manager.patterns_file.parent.mkdir(parents=True, exist_ok=True)
        import yaml
        self.manager.patterns_file.write_text(
            yaml.dump({"extensions": [".xyz"], "ignore_dirs": []}),
            encoding="utf-8"
        )

        current = self.manager.get_current_preset_name()
        self.assertIsNone(current)
