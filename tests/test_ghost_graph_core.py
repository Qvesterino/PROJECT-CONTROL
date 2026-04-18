"""Tests for canonical ghost core — shallow analysis only."""

import json
import tempfile
import unittest
from pathlib import Path

from project_control.core.ghost import ghost


class GhostCoreTests(unittest.TestCase):
    """Test the canonical ghost() function."""

    def test_ghost_returns_all_keys(self):
        """ghost() must return exactly: orphans, legacy, duplicates, sessions, semantic."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snapshot_path = tmp_path / "snapshot.json"
            snapshot_path.write_text(json.dumps({"files": []}), encoding="utf-8")

            from project_control.core.content_store import ContentStore
            snapshot = {"files": []}
            content_store = ContentStore(snapshot, snapshot_path)

            result = ghost(snapshot, {}, content_store)

            # Must have exactly these keys
            expected_keys = {"orphans", "legacy", "duplicates", "sessions", "semantic"}
            self.assertEqual(set(result.keys()), expected_keys)

            # All values must be lists
            for key in expected_keys:
                self.assertIsInstance(result[key], list, f"Key '{key}' must be a list")

    def test_ghost_empty_snapshot(self):
        """ghost() with empty snapshot returns empty lists."""
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snapshot_path = tmp_path / "snapshot.json"
            snapshot_path.write_text(json.dumps({"files": []}), encoding="utf-8")

            from project_control.core.content_store import ContentStore
            snapshot = {"files": []}
            content_store = ContentStore(snapshot, snapshot_path)

            result = ghost(snapshot, {}, content_store)

            for key in result:
                self.assertEqual(result[key], [], f"Key '{key}' should be empty for empty snapshot")

    def test_ghost_is_pure_function(self):
        """ghost() must not accept deep, mode, debug or other non-canonical params."""
        import inspect
        sig = inspect.signature(ghost)
        param_names = set(sig.parameters.keys())
        # Must only accept: snapshot, patterns, content_store
        self.assertEqual(param_names, {"snapshot", "patterns", "content_store"})
        # Must NOT accept deep params
        forbidden = {"deep", "mode", "debug", "compare_snapshot", "project_root", "graph_config", "force_graph"}
        for param in forbidden:
            self.assertNotIn(param, param_names, f"ghost() must not accept '{param}' parameter")


if __name__ == "__main__":
    unittest.main()
