"""Tests for duplicate_detector — validates Windows path fix."""

import unittest

from project_control.analysis.duplicate_detector import detect_duplicates


def _make_snapshot(paths: list[str]) -> dict:
    """Build a minimal snapshot with file entries."""
    return {"files": [{"path": p} for p in paths]}


def _fake_content_store() -> object:
    """ContentStore is not used by duplicate_detector, pass a sentinel."""
    return None


class DuplicateDetectorTests(unittest.TestCase):
    """Test the duplicate detector in isolation."""

    def test_same_name_different_dirs_is_duplicate(self):
        """Files with identical names in different directories are duplicates."""
        snapshot = _make_snapshot([
            "src/utils.py",
            "tests/utils.py",
        ])
        result = detect_duplicates(snapshot, {}, _fake_content_store())

        self.assertEqual(len(result), 1)
        pair = result[0]
        self.assertIn("src/utils.py", pair)
        self.assertIn("tests/utils.py", pair)

    def test_different_names_no_duplicates(self):
        """Files with different names produce no duplicates."""
        snapshot = _make_snapshot([
            "src/helpers.py",
            "src/utils.py",
        ])
        result = detect_duplicates(snapshot, {}, _fake_content_store())

        self.assertEqual(result, [])

    def test_windows_backslash_paths_work(self):
        """Windows-style backslash paths must still group correctly.

        This is the regression test for the bug fixed in Priority 1:
        rsplit('/', 1) failed on Windows paths → now uses Path(path).name.
        """
        snapshot = _make_snapshot([
            r"src\components\Button.tsx",
            r"src\widgets\Button.tsx",
        ])
        result = detect_duplicates(snapshot, {}, _fake_content_store())

        self.assertEqual(len(result), 1)
        pair = result[0]
        self.assertIn(r"src\components\Button.tsx", pair)
        self.assertIn(r"src\widgets\Button.tsx", pair)

    def test_case_insensitive_matching(self):
        """Duplicate detection is case-insensitive (names lowered)."""
        snapshot = _make_snapshot([
            "src/Utils.py",
            "tests/utils.py",
        ])
        result = detect_duplicates(snapshot, {}, _fake_content_store())

        self.assertEqual(len(result), 1)

    def test_three_same_names_produce_three_pairs(self):
        """Three files with same name → C(3,2) = 3 pairs."""
        snapshot = _make_snapshot([
            "a/config.json",
            "b/config.json",
            "c/config.json",
        ])
        result = detect_duplicates(snapshot, {}, _fake_content_store())

        self.assertEqual(len(result), 3)

    def test_empty_snapshot_returns_empty(self):
        """Empty snapshot produces no duplicates."""
        result = detect_duplicates({"files": []}, {}, _fake_content_store())
        self.assertEqual(result, [])

    def test_single_file_no_duplicates(self):
        """A single file can never be a duplicate."""
        snapshot = _make_snapshot(["lonely.py"])
        result = detect_duplicates(snapshot, {}, _fake_content_store())

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
