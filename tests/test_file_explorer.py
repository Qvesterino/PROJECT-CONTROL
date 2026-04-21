"""Tests for Interactive File Explorer."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.ui.file_explorer import (
    DependencyInfo,
    FileExplorer,
    FileInfo,
)


def initialize_test_project(project_root: Path) -> None:
    """Initialize a test project with .project-control directory."""
    control_dir = project_root / ".project-control"
    control_dir.mkdir(exist_ok=True)

    patterns_file = control_dir / "patterns.yaml"
    if not patterns_file.exists():
        import yaml
        default_patterns = {
            "writers": ["scale", "emissive", "opacity", "position"],
            "entrypoints": ["main.js", "index.ts"],
            "ignore_dirs": [".git", ".project-control", "node_modules", "__pycache__"],
            "extensions": [".py", ".js", ".ts", ".md", ".txt"],
        }
        with patterns_file.open("w", encoding="utf-8") as f:
            yaml.dump(default_patterns, f)


def create_test_graph(project_root: Path) -> None:
    """Create test graph data."""
    out_dir = project_root / ".project-control" / "out"
    out_dir.mkdir(parents=True, exist_ok=True)

    graph_data = {
        "nodes": [
            {"id": 1, "path": "src/main.js"},
            {"id": 2, "path": "src/utils.js"},
            {"id": 3, "path": "src/app.ts"},
        ],
        "edges": [
            {"source": 1, "target": 2},
            {"source": 3, "target": 2},
        ]
    }

    graph_file = out_dir / "graph.snapshot.json"
    graph_file.write_text(json.dumps(graph_data), encoding="utf-8")


class TestFileInfo(TestCase):
    """Test FileInfo dataclass."""

    def test_create_file_info(self) -> None:
        """Test creating file info."""
        info = FileInfo(
            path="test.js",
            name="test.js",
            is_dir=False,
            size=1024,
            modified="2024-01-01 12:00"
        )
        self.assertEqual(info.path, "test.js")
        self.assertFalse(info.is_dir)
        self.assertEqual(info.size, 1024)

    def test_file_info_with_extensions(self) -> None:
        """Test file info with extensions."""
        info = FileInfo(
            path="test.tsx",
            name="test.tsx",
            is_dir=False,
            size=0,
            modified="",
            extensions=[".tsx", ".ts"]
        )
        self.assertIn(".tsx", info.extensions)
        self.assertIn(".ts", info.extensions)


class TestDependencyInfo(TestCase):
    """Test DependencyInfo dataclass."""

    def test_default_values(self) -> None:
        """Test default values."""
        info = DependencyInfo()
        self.assertEqual(info.inbound, [])
        self.assertEqual(info.outbound, [])
        self.assertFalse(info.is_orphan)
        self.assertFalse(info.in_cycle)

    def test_with_dependencies(self) -> None:
        """Test with dependency data."""
        info = DependencyInfo(
            inbound=["file1.js", "file2.js"],
            outbound=["lib.js"],
            is_orphan=False,
            in_cycle=True
        )
        self.assertEqual(len(info.inbound), 2)
        self.assertEqual(len(info.outbound), 1)
        self.assertTrue(info.in_cycle)


class TestFileExplorer(TestCase):
    """Test FileExplorer class."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

        # Initialize project
        initialize_test_project(self.project_root)

        # Create test files
        (self.project_root / "src").mkdir()
        (self.project_root / "src" / "main.js").write_text("import utils from './utils';", encoding="utf-8")
        (self.project_root / "src" / "utils.js").write_text("export function helper() {}", encoding="utf-8")
        (self.project_root / "src" / "app.ts").write_text("import utils from './utils';", encoding="utf-8")
        (self.project_root / "README.md").write_text("# Test", encoding="utf-8")

        # Create test graph
        create_test_graph(self.project_root)

        self.explorer = FileExplorer(self.project_root)

    def tearDown(self) -> None:
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_init(self) -> None:
        """Test explorer initialization."""
        self.assertEqual(self.explorer.project_root, self.project_root)
        self.assertEqual(self.explorer.current_path, self.project_root)
        self.assertIsNotNone(self.explorer.graph_data)

    def test_list_directory(self) -> None:
        """Test listing directory."""
        files = self.explorer.list_directory()

        file_names = [f.name for f in files]
        self.assertIn("src", file_names)
        self.assertIn("README.md", file_names)

    def test_list_directory_includes_dirs_first(self) -> None:
        """Test that directories are listed first."""
        files = self.explorer.list_directory()

        # Find first non-.project-control item
        first_item = None
        for f in files:
            if f.name != ".project-control":
                first_item = f
                break

        # First item should be src (a directory)
        self.assertIsNotNone(first_item)
        if first_item.name == "src":
            self.assertTrue(first_item.is_dir)

    def test_list_subdirectory(self) -> None:
        """Test listing a subdirectory."""
        src_path = self.project_root / "src"
        files = self.explorer.list_directory(src_path)

        file_names = [f.name for f in files]
        self.assertIn("main.js", file_names)
        self.assertIn("utils.js", file_names)
        self.assertIn("app.ts", file_names)

    def test_change_directory(self) -> None:
        """Test changing directory."""
        result = self.explorer.change_directory("src")
        self.assertTrue(result)
        self.assertEqual(self.explorer.current_path, self.project_root / "src")

    def test_change_directory_invalid(self) -> None:
        """Test changing to invalid directory."""
        result = self.explorer.change_directory("nonexistent")
        self.assertFalse(result)
        self.assertEqual(self.explorer.current_path, self.project_root)

    def test_go_up(self) -> None:
        """Test going up one directory."""
        self.explorer.change_directory("src")
        result = self.explorer.go_up()
        self.assertTrue(result)
        self.assertEqual(self.explorer.current_path, self.project_root)

    def test_go_up_at_root(self) -> None:
        """Test going up when already at root."""
        result = self.explorer.go_up()
        self.assertFalse(result)
        self.assertEqual(self.explorer.current_path, self.project_root)

    def test_get_dependency_info(self) -> None:
        """Test getting dependency info."""
        info = self.explorer.get_dependency_info("src/utils.js")

        # utils.js is imported by main.js and app.ts (from test graph)
        self.assertGreaterEqual(len(info.inbound), 0)

    def test_get_dependency_info_nonexistent(self) -> None:
        """Test getting dependency info for nonexistent file."""
        info = self.explorer.get_dependency_info("nonexistent.js")
        self.assertEqual(len(info.inbound), 0)
        self.assertEqual(len(info.outbound), 0)

    def test_render_file_list(self) -> None:
        """Test rendering file list."""
        output = self.explorer.render_file_list()
        self.assertIn("Name", output)
        self.assertIn("Type", output)
        self.assertIn("Size", output)
        self.assertIn("src", output)
        self.assertIn("README.md", output)

    def test_render_file_list_with_table_format(self) -> None:
        """Test that file list uses table formatting."""
        output = self.explorer.render_file_list()
        # Should have table borders
        self.assertIn("│", output)
        self.assertIn("┌", output)
        self.assertIn("┐", output)

    def test_render_file_details(self) -> None:
        """Test rendering file details."""
        details = self.explorer.render_file_details("src/main.js")
        self.assertIn("src/main.js", details)
        self.assertIn("Size:", details)
        self.assertIn("Modified:", details)

    def test_render_file_details_nonexistent(self) -> None:
        """Test rendering details for nonexistent file."""
        details = self.explorer.render_file_details("nonexistent.js")
        self.assertIn("not found", details)

    def test_search_files(self) -> None:
        """Test searching for files."""
        results = self.explorer.search_files("main")
        file_names = [f.name for f in results]
        self.assertIn("main.js", file_names)

    def test_search_files_case_insensitive(self) -> None:
        """Test that search is case-insensitive."""
        results_lower = self.explorer.search_files("main")
        results_upper = self.explorer.search_files("MAIN")
        self.assertEqual(len(results_lower), len(results_upper))

    def test_search_files_no_results(self) -> None:
        """Test search with no results."""
        results = self.explorer.search_files("xyz")
        self.assertEqual(len(results), 0)

    def test_format_size(self) -> None:
        """Test size formatting."""
        self.assertEqual(self.explorer._format_size(100), "100.0 B")
        self.assertEqual(self.explorer._format_size(2048), "2.0 KB")
        self.assertEqual(self.explorer._format_size(3 * 1024 * 1024), "3.0 MB")

    def test_get_current_path(self) -> None:
        """Test getting current path."""
        path = self.explorer.get_current_path()
        self.assertEqual(path, self.project_root)

    def test_explorer_without_graph(self) -> None:
        """Test explorer initialization without graph data."""
        # Remove graph
        graph_file = self.project_root / ".project-control" / "out" / "graph.snapshot.json"
        if graph_file.exists():
            graph_file.unlink()

        explorer = FileExplorer(self.project_root)
        self.assertIsNone(explorer.graph_data)

        # Should still be able to list files
        files = explorer.list_directory()
        self.assertGreater(len(files), 0)

    def test_skip_hidden_files(self) -> None:
        """Test that hidden files are skipped."""
        # Create hidden file
        (self.project_root / ".hidden").write_text("hidden", encoding="utf-8")

        files = self.explorer.list_directory()
        file_names = [f.name for f in files]
        self.assertNotIn(".hidden", file_names)
