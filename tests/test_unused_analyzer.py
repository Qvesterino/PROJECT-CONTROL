"""Tests for unused_analyzer — finds unused systems with 4-signal detection."""

import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile

from project_control.analysis.unused_analyzer import (
    analyze_unused_systems,
    _detect_system_name,
    _check_import_signal,
    _check_instantiation_signal,
    _check_usage_signal,
    _check_entrypoint_signal,
    _calculate_score,
    _classify_score,
)


class UnusedAnalyzerUtilsTests(unittest.TestCase):
    """Test utility functions in unused_analyzer."""

    def test_detect_system_name_from_path(self):
        """Extract system name from file path."""
        path = Path("src/services/UserManager.py")
        self.assertEqual(_detect_system_name(path), "UserManager")

    def test_detect_system_name_from_path_simple(self):
        """Extract system name from simple file path."""
        path = Path("AuthService.js")
        self.assertEqual(_detect_system_name(path), "AuthService")

    def test_calculate_score_all_missing(self):
        """Score 4 when all signals are missing."""
        score = _calculate_score(False, False, False, False)
        self.assertEqual(score, 4)

    def test_calculate_score_two_missing(self):
        """Score 2 when two signals are missing."""
        score = _calculate_score(True, False, False, True)
        self.assertEqual(score, 2)

    def test_calculate_score_one_missing(self):
        """Score 1 when one signal is missing."""
        score = _calculate_score(True, True, True, False)
        self.assertEqual(score, 1)

    def test_calculate_score_none_missing(self):
        """Score 0 when no signals are missing."""
        score = _calculate_score(True, True, True, True)
        self.assertEqual(score, 0)

    def test_classify_score_high(self):
        """Score 4 should classify as high."""
        self.assertEqual(_classify_score(4), "high")

    def test_classify_score_medium(self):
        """Scores 2-3 should classify as medium."""
        self.assertEqual(_classify_score(2), "medium")
        self.assertEqual(_classify_score(3), "medium")

    def test_classify_score_low(self):
        """Score 1 should classify as low."""
        self.assertEqual(_classify_score(1), "low")

    def test_classify_score_zero(self):
        """Score 0 should not be classified (system is used)."""
        self.assertIsNone(_classify_score(0))


class UnusedAnalyzerSignalTests(unittest.TestCase):
    """Test individual signal detection functions."""

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_import_signal_found(self, mock_rg):
        """Import signal should return True when import is found."""
        mock_rg.return_value = [
            {"file": "src/main.py", "line": 5, "text": "from UserManager import UserManager"}
        ]

        has_import, reason = _check_import_signal("UserManager", Path("."))

        self.assertTrue(has_import)
        self.assertIn("Import found", reason)

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_import_signal_not_found(self, mock_rg):
        """Import signal should return False when no import is found."""
        mock_rg.return_value = []

        has_import, reason = _check_import_signal("UserManager", Path("."))

        self.assertFalse(has_import)
        self.assertEqual(reason, "No import found")

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_instantiation_signal_found(self, mock_rg):
        """Instantiation signal should return True when instantiation is found."""
        mock_rg.return_value = [
            {"file": "src/main.py", "line": 10, "text": "manager = new UserManager()"}
        ]

        has_inst, reason = _check_instantiation_signal("UserManager", Path("."))

        self.assertTrue(has_inst)
        self.assertIn("Instantiation found", reason)

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_instantiation_signal_not_found(self, mock_rg):
        """Instantiation signal should return False when no instantiation is found."""
        mock_rg.return_value = []

        has_inst, reason = _check_instantiation_signal("UserManager", Path("."))

        self.assertFalse(has_inst)
        self.assertEqual(reason, "No instantiation found")

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_usage_signal_high_count(self, mock_rg):
        """Usage signal should return True when usage count > 1."""
        mock_rg.return_value = [
            {"file": "src/main.py", "line": 5, "text": "UserManager"},
            {"file": "src/auth.py", "line": 10, "text": "UserManager"},
            {"file": "src/test.py", "line": 15, "text": "UserManager"},
        ]

        has_usage, reason = _check_usage_signal("UserManager", Path("."), Path("src/UserManager.py"))

        self.assertTrue(has_usage)
        self.assertIn("Usage found", reason)

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_usage_signal_low_count(self, mock_rg):
        """Usage signal should return False when usage count <= 1."""
        mock_rg.return_value = [
            {"file": "src/UserManager.py", "line": 5, "text": "UserManager"}  # Self-reference
        ]

        has_usage, reason = _check_usage_signal("UserManager", Path("."), Path("src/UserManager.py"))

        self.assertFalse(has_usage)
        self.assertIn("Usage count: 0", reason)

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_entrypoint_signal_found(self, mock_rg):
        """Entrypoint signal should return True when system is in entrypoint."""
        # Mock finding system in main.py
        mock_rg.return_value = [
            {"file": "main.py", "line": 1, "text": "from UserManager import UserManager"}
        ]

        with patch("pathlib.Path.exists", return_value=True):
            has_entry, reason = _check_entrypoint_signal("UserManager", Path("."))

            self.assertTrue(has_entry)
            self.assertIn("Referenced in entrypoint", reason)

    @patch("project_control.analysis.unused_analyzer.run_rg_json")
    def test_entrypoint_signal_not_found(self, mock_rg):
        """Entrypoint signal should return False when system is not in entrypoint."""
        mock_rg.return_value = []

        with patch("pathlib.Path.exists", return_value=True):
            has_entry, reason = _check_entrypoint_signal("UserManager", Path("."))

            self.assertFalse(has_entry)
            self.assertEqual(reason, "Not referenced in any entrypoint")


class UnusedAnalyzerIntegrationTests(unittest.TestCase):
    """Integration tests for unused_analyzer."""

    @patch("project_control.analysis.unused_analyzer._should_ignore_file")
    @patch("project_control.analysis.unused_analyzer._check_import_signal")
    @patch("project_control.analysis.unused_analyzer._check_instantiation_signal")
    @patch("project_control.analysis.unused_analyzer._check_usage_signal")
    @patch("project_control.analysis.unused_analyzer._check_entrypoint_signal")
    def test_high_priority_system(self, mock_entry, mock_usage, mock_inst, mock_import, mock_ignore):
        """System with score 4 should be in HIGH priority bucket."""
        mock_ignore.return_value = False
        mock_import.return_value = (False, "No import found")
        mock_inst.return_value = (False, "No instantiation found")
        mock_usage.return_value = (False, "Usage count: 0")
        mock_entry.return_value = (False, "Not referenced in entrypoint")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            # Create a system file
            system_file = tmppath / "services" / "UserManager.py"
            system_file.parent.mkdir(parents=True, exist_ok=True)
            system_file.write_text("class UserManager:\n    pass\n")

            result = analyze_unused_systems(tmppath)

            self.assertEqual(len(result["high"]), 1)
            # Use os.path.normpath for cross-platform path comparison
            import os
            expected_path = os.path.join("services", "UserManager.py")
            self.assertEqual(result["high"][0]["file"], expected_path)
            self.assertEqual(result["high"][0]["score"], 4)
            self.assertEqual(len(result["high"][0]["reasons"]), 4)

    @patch("project_control.analysis.unused_analyzer._should_ignore_file")
    @patch("project_control.analysis.unused_analyzer._check_import_signal")
    @patch("project_control.analysis.unused_analyzer._check_instantiation_signal")
    @patch("project_control.analysis.unused_analyzer._check_usage_signal")
    @patch("project_control.analysis.unused_analyzer._check_entrypoint_signal")
    def test_medium_priority_system(self, mock_entry, mock_usage, mock_inst, mock_import, mock_ignore):
        """System with score 2 should be in MEDIUM priority bucket."""
        mock_ignore.return_value = False
        mock_import.return_value = (True, "Import found")  # Has import
        mock_inst.return_value = (False, "No instantiation found")
        mock_usage.return_value = (False, "Usage count: 0")
        mock_entry.return_value = (False, "Not referenced in entrypoint")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            system_file = tmppath / "services" / "AuthService.py"
            system_file.parent.mkdir(parents=True, exist_ok=True)
            system_file.write_text("class AuthService:\n    pass\n")

            result = analyze_unused_systems(tmppath)

            self.assertEqual(len(result["medium"]), 1)
            self.assertEqual(result["medium"][0]["score"], 3)  # import=True, others=False

    @patch("project_control.analysis.unused_analyzer._should_ignore_file")
    @patch("project_control.analysis.unused_analyzer._check_import_signal")
    @patch("project_control.analysis.unused_analyzer._check_instantiation_signal")
    @patch("project_control.analysis.unused_analyzer._check_usage_signal")
    @patch("project_control.analysis.unused_analyzer._check_entrypoint_signal")
    def test_low_priority_system(self, mock_entry, mock_usage, mock_inst, mock_import, mock_ignore):
        """System with score 1 should be in LOW priority bucket."""
        mock_ignore.return_value = False
        mock_import.return_value = (True, "Import found")
        mock_inst.return_value = (True, "Instantiation found")
        mock_usage.return_value = (True, "Usage found")
        mock_entry.return_value = (False, "Not referenced in entrypoint")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            system_file = tmppath / "services" / "DataController.py"
            system_file.parent.mkdir(parents=True, exist_ok=True)
            system_file.write_text("class DataController:\n    pass\n")

            result = analyze_unused_systems(tmppath)

            self.assertEqual(len(result["low"]), 1)
            self.assertEqual(result["low"][0]["score"], 1)

    @patch("project_control.analysis.unused_analyzer._should_ignore_file")
    @patch("project_control.analysis.unused_analyzer._check_import_signal")
    @patch("project_control.analysis.unused_analyzer._check_instantiation_signal")
    @patch("project_control.analysis.unused_analyzer._check_usage_signal")
    @patch("project_control.analysis.unused_analyzer._check_entrypoint_signal")
    def test_used_system_not_included(self, mock_entry, mock_usage, mock_inst, mock_import, mock_ignore):
        """System with score 0 should NOT be included in results."""
        mock_ignore.return_value = False
        mock_import.return_value = (True, "Import found")
        mock_inst.return_value = (True, "Instantiation found")
        mock_usage.return_value = (True, "Usage found")
        mock_entry.return_value = (True, "Referenced in entrypoint")

        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            system_file = tmppath / "services" / "HealthyService.py"
            system_file.parent.mkdir(parents=True, exist_ok=True)
            system_file.write_text("class HealthyService:\n    pass\n")

            result = analyze_unused_systems(tmppath)

            # Score 0 means system is used, should not be in any bucket
            self.assertEqual(len(result["high"]), 0)
            self.assertEqual(len(result["medium"]), 0)
            self.assertEqual(len(result["low"]), 0)

    def test_ignores_test_files(self):
        """Test files should be ignored even if they match system patterns."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            test_file = tmppath / "tests" / "test_UserManager.py"
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("class UserManager:\n    pass\n")

            result = analyze_unused_systems(tmppath)

            # Test files should be ignored
            self.assertEqual(len(result["high"]), 0)
            self.assertEqual(len(result["medium"]), 0)
            self.assertEqual(len(result["low"]), 0)

    def test_result_structure(self):
        """Result should have correct structure with high/medium/low and stats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            result = analyze_unused_systems(tmppath)

            # Check top-level keys
            self.assertIn("high", result)
            self.assertIn("medium", result)
            self.assertIn("low", result)
            self.assertIn("stats", result)

            # Check stats structure
            self.assertIn("total_systems", result["stats"])
            self.assertIn("high_priority", result["stats"])
            self.assertIn("medium_priority", result["stats"])
            self.assertIn("low_priority", result["stats"])


if __name__ == "__main__":
    unittest.main()
