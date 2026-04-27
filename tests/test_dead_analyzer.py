"""Tests for dead_analyzer — finds files with zero or minimal usage."""

import unittest
from unittest.mock import patch
from pathlib import Path

from project_control.analysis.dead_analyzer import analyze_dead_code, _should_ignore_file


class DeadAnalyzerIgnoreTests(unittest.TestCase):
    """Test file filtering in dead_analyzer."""

    def test_ignores_test_files_python(self):
        """Python test files should be ignored."""
        self.assertTrue(_should_ignore_file(Path("tests/test_utils.py")))
        self.assertTrue(_should_ignore_file(Path("src/utils_test.py")))

    def test_ignores_test_files_js(self):
        """JavaScript/TypeScript test files should be ignored."""
        self.assertTrue(_should_ignore_file(Path("src/utils.test.js")))
        self.assertTrue(_should_ignore_file(Path("src/utils.test.ts")))
        self.assertTrue(_should_ignore_file(Path("src/utils.spec.js")))
        self.assertTrue(_should_ignore_file(Path("src/utils.spec.ts")))

    def test_ignores_node_modules(self):
        """node_modules directory should be ignored."""
        self.assertTrue(_should_ignore_file(Path("node_modules/package/index.js")))
        self.assertTrue(_should_ignore_file(Path("src/node_modules/file.py")))

    def test_ignores_git_dir(self):
        """.git directory should be ignored."""
        self.assertTrue(_should_ignore_file(Path(".git/hooks/pre-commit")))

    def test_ignores_project_control_dir(self):
        """.project-control directory should be ignored."""
        self.assertTrue(_should_ignore_file(Path(".project-control/snapshot.json")))

    def test_ignores_venv_dirs(self):
        """Virtual environment directories should be ignored."""
        self.assertTrue(_should_ignore_file(Path("venv/lib/python3.10/site-packages/pkg.py")))
        self.assertTrue(_should_ignore_file(Path(".venv/lib/python3.10/site-packages/pkg.py")))
        self.assertTrue(_should_ignore_file(Path("env/lib/python3.10/site-packages/pkg.py")))

    def test_ignores_pycache(self):
        """__pycache__ directory should be ignored."""
        self.assertTrue(_should_ignore_file(Path("src/__pycache__/utils.cpython-310.pyc")))

    def test_ignores_config_files(self):
        """Config files should be ignored."""
        self.assertTrue(_should_ignore_file(Path("config.py")))
        self.assertTrue(_should_ignore_file(Path("config.js")))
        self.assertTrue(_should_ignore_file(Path("settings.py")))

    def test_does_not_ignore_normal_files(self):
        """Normal source files should NOT be ignored."""
        self.assertFalse(_should_ignore_file(Path("src/utils.py")))
        self.assertFalse(_should_ignore_file(Path("src/components/Button.tsx")))
        self.assertFalse(_should_ignore_file(Path("index.js")))


class DeadAnalyzerTests(unittest.TestCase):
    """Test dead code analyzer."""

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_orphan_file_high_priority(self, mock_ignore, mock_rg):
        """File with 0 references should be HIGH priority."""
        mock_ignore.return_value = False
        mock_rg.return_value = []  # No references found

        result = analyze_dead_code(["src/utils.py"])

        self.assertEqual(len(result["high"]), 1)
        self.assertEqual(result["high"][0], "src/utils.py")
        self.assertEqual(len(result["medium"]), 0)
        self.assertEqual(result["stats"]["dead"], 1)

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_single_reference_high_priority(self, mock_ignore, mock_rg):
        """File with 1 reference should be HIGH priority."""
        mock_ignore.return_value = False
        mock_rg.return_value = ["src/main.py"]  # 1 reference found

        result = analyze_dead_code(["src/utils.py"])

        self.assertEqual(len(result["high"]), 1)
        self.assertEqual(result["high"][0], "src/utils.py")
        self.assertEqual(result["stats"]["dead"], 1)

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_low_usage_medium_priority(self, mock_ignore, mock_rg):
        """File with 2 references should be MEDIUM priority (default threshold)."""
        mock_ignore.return_value = False
        mock_rg.return_value = ["src/main.py", "src/app.py"]  # 2 references

        result = analyze_dead_code(["src/utils.py"])

        self.assertEqual(len(result["high"]), 0)
        self.assertEqual(len(result["medium"]), 1)
        self.assertEqual(result["medium"][0], "src/utils.py")

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_custom_threshold(self, mock_ignore, mock_rg):
        """Custom threshold should change classification."""
        mock_ignore.return_value = False
        mock_rg.return_value = ["src/main.py", "src/app.py", "src/test.py"]  # 3 references

        # With threshold=5, 3 references is still low usage
        result = analyze_dead_code(["src/utils.py"], low_usage_threshold=5)

        self.assertEqual(len(result["medium"]), 1)
        self.assertEqual(result["medium"][0], "src/utils.py")

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_healthy_file_not_reported(self, mock_ignore, mock_rg):
        """File with many references should not be reported."""
        mock_ignore.return_value = False
        mock_rg.return_value = [
            "src/main.py",
            "src/app.py",
            "src/component1.py",
            "src/component2.py",
            "src/utils.py",  # Self-reference
        ]  # 4 external references

        result = analyze_dead_code(["src/utils.py"])

        self.assertEqual(len(result["high"]), 0)
        self.assertEqual(len(result["medium"]), 0)
        self.assertEqual(result["stats"]["dead"], 0)

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_ignored_files_not_in_results(self, mock_ignore, mock_rg):
        """Ignored files should not be analyzed."""
        mock_ignore.return_value = True  # File should be ignored
        mock_rg.return_value = []  # This should not be called

        result = analyze_dead_code(["tests/test_utils.py"])

        self.assertEqual(len(result["high"]), 0)
        self.assertEqual(len(result["medium"]), 0)

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_multiple_files_mixed_results(self, mock_ignore, mock_rg):
        """Multiple files with different usage levels."""
        def mock_ignore_side_effect(path):
            # Ignore test files
            return "test" in str(path)

        def mock_rg_side_effect(patterns, extra_args=None):
            # Return different counts based on file name
            if any("orphan" in p for p in patterns):
                return []  # No references
            elif any("low_usage" in p for p in patterns):
                return ["src/main.py", "src/app.py"]  # 2 references
            else:
                return ["f1.py", "f2.py", "f3.py", "f4.py"]  # 4 references

        mock_ignore.side_effect = mock_ignore_side_effect
        mock_rg.side_effect = mock_rg_side_effect

        files = [
            "src/orphan.py",
            "src/low_usage.py",
            "src/healthy.py",
            "tests/test_ignored.py",  # Should be ignored
        ]

        result = analyze_dead_code(files)

        # Check results
        self.assertEqual(len(result["high"]), 1)
        self.assertIn("orphan", result["high"][0])

        self.assertEqual(len(result["medium"]), 1)
        self.assertIn("low_usage", result["medium"][0])

        self.assertEqual(result["stats"]["total"], 4)
        self.assertEqual(result["stats"]["dead"], 1)  # Only orphan.py

    def test_result_structure(self):
        """Result should have correct structure."""
        result = analyze_dead_code([])

        # Check top-level keys
        self.assertIn("high", result)
        self.assertIn("medium", result)
        self.assertIn("stats", result)

        # Check stats structure
        self.assertIn("total", result["stats"])
        self.assertIn("dead", result["stats"])

        # Check that high and medium are lists
        self.assertIsInstance(result["high"], list)
        self.assertIsInstance(result["medium"], list)

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_results_are_sorted(self, mock_ignore, mock_rg):
        """Results should be sorted alphabetically."""
        mock_ignore.return_value = False

        def mock_rg_side_effect(patterns, extra_args=None):
            return []  # All files are orphans

        mock_rg.side_effect = mock_rg_side_effect

        files = ["zebra.py", "alpha.py", "middle.py"]
        result = analyze_dead_code(files)

        # Results should be sorted
        self.assertEqual(result["high"], ["alpha.py", "middle.py", "zebra.py"])

    @patch("project_control.analysis.dead_analyzer.run_rg_files_only")
    @patch("project_control.analysis.dead_analyzer._should_ignore_file")
    def test_basename_search(self, mock_ignore, mock_rg):
        """Should search using basename of files."""
        mock_ignore.return_value = False
        mock_rg.return_value = ["src/main.py", "src/app.py"]

        analyze_dead_code(["src/utils/MyUtils.py"])

        # Verify that run_rg_files_only was called with basename patterns
        # It should search for both "MyUtils.py" and "MyUtils"
        mock_rg.assert_called_once()
        call_args = mock_rg.call_args[0][0]  # First positional argument (patterns list)
        self.assertIn("MyUtils.py", call_args)
        self.assertIn("MyUtils", call_args)


if __name__ == "__main__":
    unittest.main()
