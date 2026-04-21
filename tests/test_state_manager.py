"""Tests for State Manager and consolidated state."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.persistence.state_manager import (
    AppState,
    StateManager,
    TagState,
    UIState,
    UserPreferences,
    ProjectMetadata,
)


class TestAppState(TestCase):
    """Test AppState dataclass."""

    def test_default_state(self) -> None:
        """Test creating default AppState."""
        state = AppState()
        self.assertIsInstance(state.ui, UIState)
        self.assertIsInstance(state.tags, TagState)
        self.assertIsInstance(state.user, UserPreferences)
        self.assertIsInstance(state.metadata, ProjectMetadata)
        self.assertEqual(state.version, "1.0")

    def test_to_dict(self) -> None:
        """Test converting AppState to dictionary."""
        state = AppState(
            ui=UIState(project_mode="python"),
            tags=TagState(tags={"tag1": ["file1.py"]}),
            user=UserPreferences(favorites=["target1"], history=["action1"]),
        )

        data = state.to_dict()
        self.assertIn("version", data)
        self.assertIn("ui", data)
        self.assertIn("tags", data)
        self.assertIn("user", data)
        self.assertIn("metadata", data)

    def test_from_dict(self) -> None:
        """Test creating AppState from dictionary."""
        data = {
            "version": "1.0",
            "ui": {"project_mode": "python", "graph_profile": "strict",
                   "trace_direction": "inbound", "trace_depth": 100, "trace_all_paths": True},
            "tags": {"tags": {"tag1": ["file1.py"]}},
            "user": {"favorites": ["target1"], "history": ["action1"]},
            "metadata": {},
        }

        state = AppState.from_dict(data)
        self.assertEqual(state.ui.project_mode, "python")
        self.assertEqual(state.tags.tags["tag1"], ["file1.py"])
        self.assertEqual(state.user.favorites, ["target1"])

    def test_from_dict_with_defaults(self) -> None:
        """Test AppState.from_dict with missing fields."""
        data = {"version": "1.0"}

        state = AppState.from_dict(data)
        self.assertEqual(state.ui.project_mode, "js_ts")  # Default
        self.assertEqual(state.ui.trace_depth, 50)  # Default
        self.assertEqual(len(state.user.favorites), 0)  # Default


class TestStateManager(TestCase):
    """Test StateManager class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.manager = StateManager(self.project_root)

    def tearDown(self) -> None:
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_load_default_state(self) -> None:
        """Test loading default state when no file exists."""
        state = self.manager.load()
        self.assertIsInstance(state, AppState)
        self.assertEqual(state.ui.project_mode, "js_ts")

    def test_save_and_load(self) -> None:
        """Test saving and loading state."""
        state = AppState(
            ui=UIState(project_mode="python"),
            user=UserPreferences(favorites=["test.py"]),
        )

        self.manager.save(state)
        loaded_state = self.manager.load()

        self.assertEqual(loaded_state.ui.project_mode, "python")
        self.assertEqual(loaded_state.user.favorites, ["test.py"])

    def test_state_file_creation(self) -> None:
        """Test that state.json file is created."""
        state = AppState()
        self.manager.save(state)

        self.assertTrue(self.manager.state_path.exists())
        self.assertEqual(self.manager.state_path.name, "state.json")

    def test_migrate_from_old_config(self) -> None:
        """Test migration from old config.json."""
        # Create old config.json
        old_config = self.project_root / ".project-control" / "config.json"
        old_config.parent.mkdir(parents=True, exist_ok=True)

        old_data = {
            "project_mode": "python",
            "graph_profile": "strict",
            "trace_direction": "inbound",
            "trace_depth": 100,
            "trace_all_paths": True,
            "favorites": ["old_fav.py"],
            "history": ["old_action"],
        }
        old_config.write_text(json.dumps(old_data), encoding="utf-8")

        # Load should migrate
        state = self.manager.load()

        self.assertEqual(state.ui.project_mode, "python")
        self.assertEqual(state.ui.graph_profile, "strict")
        self.assertEqual(state.ui.trace_direction, "inbound")
        self.assertEqual(state.ui.trace_depth, 100)
        self.assertTrue(state.ui.trace_all_paths)
        self.assertEqual(state.user.favorites, ["old_fav.py"])
        self.assertEqual(state.user.history, ["old_action"])

    def test_migrate_from_old_status(self) -> None:
        """Test migration from old status.yaml."""
        # Create old status.yaml
        old_status = self.project_root / ".project-control" / "status.yaml"
        old_status.parent.mkdir(parents=True, exist_ok=True)

        import yaml
        old_data = {"tags": {"important": ["file1.py", "file2.py"]}}
        old_status.write_text(yaml.dump(old_data), encoding="utf-8")

        # Load should migrate
        state = self.manager.load()

        self.assertIn("important", state.tags.tags)
        self.assertEqual(state.tags.tags["important"], ["file1.py", "file2.py"])

    def test_update_last_scan(self) -> None:
        """Test updating last scan timestamp."""
        self.manager.update_last_scan()

        state = self.manager.load()
        self.assertIsNotNone(state.metadata.last_scan)
        self.assertIn("T", state.metadata.last_scan)  # ISO format

    def test_update_last_graph_build(self) -> None:
        """Test updating last graph build timestamp."""
        self.manager.update_last_graph_build()

        state = self.manager.load()
        self.assertIsNotNone(state.metadata.last_graph_build)

    def test_update_last_analysis(self) -> None:
        """Test updating last analysis timestamp."""
        self.manager.update_last_analysis()

        state = self.manager.load()
        self.assertIsNotNone(state.metadata.last_analysis)

    def test_add_to_history(self) -> None:
        """Test adding actions to history."""
        self.manager.add_to_history("Action 1")
        self.manager.add_to_history("Action 2")
        self.manager.add_to_history("Action 3")

        state = self.manager.load()
        self.assertEqual(len(state.user.history), 3)
        self.assertEqual(state.user.history[0], "Action 3")  # Most recent first

    def test_history_max_items(self) -> None:
        """Test that history respects max_items limit."""
        for i in range(15):
            self.manager.add_to_history(f"Action {i}")

        state = self.manager.load()
        self.assertEqual(len(state.user.history), 10)  # Default max

    def test_add_to_favorites(self) -> None:
        """Test adding items to favorites."""
        self.manager.add_to_favorites("file1.py")
        self.manager.add_to_favorites("file2.py")

        state = self.manager.load()
        self.assertEqual(len(state.user.favorites), 2)
        self.assertIn("file1.py", state.user.favorites)
        self.assertIn("file2.py", state.user.favorites)

    def test_add_duplicate_favorite(self) -> None:
        """Test that duplicate favorites are not added."""
        self.manager.add_to_favorites("file1.py")
        self.manager.add_to_favorites("file1.py")  # Duplicate

        state = self.manager.load()
        self.assertEqual(state.user.favorites.count("file1.py"), 1)

    def test_remove_from_favorites(self) -> None:
        """Test removing items from favorites."""
        self.manager.add_to_favorites("file1.py")
        self.manager.add_to_favorites("file2.py")
        self.manager.remove_from_favorites("file1.py")

        state = self.manager.load()
        self.assertNotIn("file1.py", state.user.favorites)
        self.assertIn("file2.py", state.user.favorites)

    def test_get_tags(self) -> None:
        """Test getting tags."""
        state = AppState(tags=TagState(tags={"tag1": ["file1.py"]}))
        self.manager.save(state)

        tags = self.manager.get_tags()
        self.assertEqual(tags["tag1"], ["file1.py"])

    def test_set_tags(self) -> None:
        """Test setting tags."""
        new_tags = {"important": ["file1.py", "file2.py"], "test": ["file3.py"]}
        self.manager.set_tags(new_tags)

        state = self.manager.load()
        self.assertEqual(state.tags.tags, new_tags)

    def test_add_file_to_tag(self) -> None:
        """Test adding a file to a tag."""
        self.manager.add_file_to_tag("important", "file1.py")
        self.manager.add_file_to_tag("important", "file2.py")

        state = self.manager.load()
        self.assertEqual(len(state.tags.tags["important"]), 2)
        self.assertIn("file1.py", state.tags.tags["important"])

    def test_remove_file_from_tag(self) -> None:
        """Test removing a file from a tag."""
        self.manager.add_file_to_tag("important", "file1.py")
        self.manager.add_file_to_tag("important", "file2.py")
        self.manager.remove_file_from_tag("important", "file1.py")

        state = self.manager.load()
        self.assertNotIn("file1.py", state.tags.tags["important"])
        self.assertIn("file2.py", state.tags.tags["important"])

    def test_cleanup_old_files_with_backup(self) -> None:
        """Test cleaning up old files with backup."""
        # Create old files
        old_config = self.project_root / ".project-control" / "config.json"
        old_status = self.project_root / ".project-control" / "status.yaml"
        old_config.parent.mkdir(parents=True, exist_ok=True)
        old_config.write_text("{}", encoding="utf-8")
        old_status.write_text("tags: {}", encoding="utf-8")

        # Cleanup with backup
        self.manager.cleanup_old_files(backup=True)

        # Old files should be gone
        self.assertFalse(old_config.exists())
        self.assertFalse(old_status.exists())

        # Backups should exist
        backup_dir = self.project_root / ".project-control" / "backups"
        self.assertTrue(backup_dir.exists())
        backup_files = list(backup_dir.glob("*.bak"))
        self.assertTrue(len(backup_files) >= 2)

    def test_corrupted_state_file(self) -> None:
        """Test handling corrupted state file."""
        # Create corrupted state file
        self.manager.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.manager.state_path.write_text("{invalid json}", encoding="utf-8")

        # Should return default state
        state = self.manager.load()
        self.assertIsInstance(state, AppState)
        self.assertEqual(state.ui.project_mode, "js_ts")  # Default
