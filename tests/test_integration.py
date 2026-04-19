"""Minimal integration test: scan → ghost → graph build.

Validates that the three major pipelines work end-to-end on a real temp project.
"""

import json
import tempfile
import unittest
from pathlib import Path

from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.core.content_store import ContentStore
from project_control.core.ghost import ghost
from project_control.config.graph_config import GraphConfig
from project_control.graph.builder import GraphBuilder


def _create_mini_project(root: Path) -> None:
    """Create a small but realistic project structure for testing."""
    # Python package
    src = root / "myapp"
    src.mkdir()
    (src / "__init__.py").write_text("", encoding="utf-8")
    (src / "main.py").write_text(
        "from myapp.utils import helper\n\ndef run():\n    helper()\n",
        encoding="utf-8",
    )
    (src / "utils.py").write_text(
        "def helper():\n    return 42\n",
        encoding="utf-8",
    )

    # Standalone orphan file (never imported)
    (src / "orphan.py").write_text(
        "# This file is never imported by anyone\nprint('lonely')\n",
        encoding="utf-8",
    )

    # Duplicate-named file in different directory
    tests = root / "tests"
    tests.mkdir()
    (tests / "utils.py").write_text(
        "from myapp.utils import helper\n\ndef test_helper():\n    assert helper() == 42\n",
        encoding="utf-8",
    )


class IntegrationTests(unittest.TestCase):
    """End-to-end: scan → ghost → graph build on a temp project."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        _create_mini_project(self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_produces_valid_snapshot(self):
        """scan_project must return a snapshot with files and deterministic ID."""
        snapshot = scan_project(str(self.root), ["node_modules", ".git"], [".py"])

        self.assertIn("files", snapshot)
        self.assertIn("snapshot_id", snapshot)
        self.assertIn("snapshot_version", snapshot)
        self.assertGreaterEqual(snapshot["file_count"], 4)
        self.assertTrue(snapshot["snapshot_id"])

    def test_ghost_finds_duplicates_and_orphans(self):
        """ghost() must detect the duplicate utils.py and (optionally) orphan.py."""
        snapshot = scan_project(str(self.root), ["node_modules", ".git"], [".py"])
        save_snapshot(snapshot, self.root)

        snapshot_path = self.root / ".project-control" / "snapshot.json"
        content_store = ContentStore(snapshot, snapshot_path)

        result = ghost(snapshot, {}, content_store)

        # Verify canonical keys
        self.assertEqual(set(result.keys()), {"orphans", "legacy", "duplicates", "sessions", "semantic"})

        # Must find the duplicate: myapp/utils.py vs tests/utils.py
        dup_paths = set()
        for a, b in result["duplicates"]:
            dup_paths.add(a)
            dup_paths.add(b)
        self.assertTrue(
            any("utils.py" in p for p in dup_paths),
            f"Expected duplicate utils.py, got: {result['duplicates']}",
        )

    def test_graph_build_produces_valid_structure(self):
        """GraphBuilder must produce nodes, edges, and entrypoints."""
        snapshot = scan_project(str(self.root), ["node_modules", ".git"], [".py"])
        save_snapshot(snapshot, self.root)

        snapshot_path = self.root / ".project-control" / "snapshot.json"
        content_store = ContentStore(snapshot, snapshot_path)

        # Enable Python in graph config (disabled by default)
        languages = {
            "js_ts": {"enabled": False, "include_exts": [".js", ".ts"]},
            "python": {"enabled": True, "include_exts": [".py"]},
        }
        config = GraphConfig(languages=languages)
        builder = GraphBuilder(self.root, snapshot, content_store, config)
        graph = builder.build()

        # Must have canonical graph keys
        self.assertIn("nodes", graph)
        self.assertIn("edges", graph)
        self.assertIn("entrypoints", graph)
        self.assertIn("meta", graph)

        # Must have found our Python files as nodes
        node_paths = {n["path"] for n in graph["nodes"]}
        self.assertTrue(
            any("main.py" in p for p in node_paths),
            f"Expected main.py in nodes, got: {node_paths}",
        )

        # Must have at least one edge (main.py imports utils.py)
        self.assertGreaterEqual(len(graph["edges"]), 1, "Expected at least one import edge")


if __name__ == "__main__":
    unittest.main()
