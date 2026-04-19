"""Tests for orphan_detector — core ghost value."""

import unittest
from unittest.mock import patch
from pathlib import Path

from project_control.analysis.orphan_detector import detect_orphans


def _make_snapshot(paths: list[str]) -> dict:
    """Build a minimal snapshot with file entries."""
    return {"files": [{"path": p} for p in paths]}


def _fake_content_store() -> object:
    """ContentStore is not used by orphan_detector, pass a sentinel."""
    return None


class OrphanDetectorTests(unittest.TestCase):
    """Test the orphan detector in isolation."""

    @patch("project_control.analysis.orphan_detector.run_rg")
    def test_unreferenced_code_file_is_orphan(self, mock_rg):
        """A .py file with no imports/requires referencing it should be orphaned."""
        mock_rg.return_value = ""  # rg finds nothing → orphan

        snapshot = _make_snapshot(["src/utils.py"])
        result = detect_orphans(snapshot, {}, _fake_content_store())

        self.assertEqual(result, ["src/utils.py"])

    @patch("project_control.analysis.orphan_detector.run_rg")
    def test_referenced_file_is_not_orphan(self, mock_rg):
        """A file whose stem appears in rg results is NOT orphaned."""
        # rg returns a match → file is referenced
        mock_rg.return_value = "some/file.py:1:from utils import something"

        snapshot = _make_snapshot(["src/utils.py"])
        result = detect_orphans(snapshot, {}, _fake_content_store())

        self.assertEqual(result, [])

    @patch("project_control.analysis.orphan_detector.run_rg")
    def test_entrypoint_skipped_even_if_unreferenced(self, mock_rg):
        """Files listed in patterns['entrypoints'] are never orphans."""
        mock_rg.return_value = ""

        snapshot = _make_snapshot(["app.py", "server.py"])
        patterns = {"entrypoints": ["app.py"]}

        result = detect_orphans(snapshot, patterns, _fake_content_store())

        # app.py is entrypoint → skipped; server.py is orphaned
        self.assertIn("server.py", result)
        self.assertNotIn("app.py", result)

    @patch("project_control.analysis.orphan_detector.run_rg")
    def test_non_code_files_ignored(self, mock_rg):
        """Files with non-code extensions (.json, .md, .txt) are skipped."""
        mock_rg.return_value = ""

        snapshot = _make_snapshot(["data/config.json", "docs/readme.md", "notes.txt"])
        result = detect_orphans(snapshot, {}, _fake_content_store())

        self.assertEqual(result, [])

    @patch("project_control.analysis.orphan_detector.run_rg")
    def test_js_and_ts_files_detected(self, mock_rg):
        """JS and TS files are checked for orphan status."""
        mock_rg.return_value = ""

        snapshot = _make_snapshot(["src/helpers.js", "src/types.ts"])
        result = detect_orphans(snapshot, {}, _fake_content_store())

        self.assertEqual(sorted(result), ["src/helpers.js", "src/types.ts"])

    @patch("project_control.analysis.orphan_detector.run_rg")
    def test_empty_snapshot_returns_empty(self, mock_rg):
        """Empty snapshot produces no orphans."""
        result = detect_orphans({"files": []}, {}, _fake_content_store())
        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
