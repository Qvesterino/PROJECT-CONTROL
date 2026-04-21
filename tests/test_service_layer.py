"""Tests for Service Layer Protocol and services."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.services.base import Service, ServiceResult, with_error_handling
from project_control.services.scan_service import ScanService
from project_control.core.error_handler import ProjectControlError, ValidationError


def initialize_test_project(project_root: Path) -> None:
    """Initialize a test project with .project-control directory."""
    control_dir = project_root / ".project-control"
    control_dir.mkdir(exist_ok=True)

    patterns_file = control_dir / "patterns.yaml"
    if not patterns_file.exists():
        default_patterns = {
            "writers": ["scale", "emissive", "opacity", "position"],
            "entrypoints": ["main.js", "index.ts"],
            "ignore_dirs": [".git", ".project-control", "node_modules", "__pycache__"],
            "extensions": [".py", ".js", ".ts", ".md", ".txt"],
        }
        import yaml
        with patterns_file.open("w", encoding="utf-8") as f:
            yaml.dump(default_patterns, f)

    status_file = control_dir / "status.yaml"
    if not status_file.exists():
        import yaml
        with status_file.open("w", encoding="utf-8") as f:
            yaml.dump({"tags": {}}, f)


class TestServiceResult(TestCase):
    """Test ServiceResult dataclass."""

    def test_success_result(self) -> None:
        """Test creating a successful ServiceResult."""
        result = ServiceResult(
            success=True,
            message="Operation completed",
            data={"key": "value"},
            exit_code=0
        )
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Operation completed")
        self.assertEqual(result.data, {"key": "value"})
        self.assertEqual(result.exit_code, 0)

    def test_failure_result(self) -> None:
        """Test creating a failed ServiceResult."""
        result = ServiceResult(
            success=False,
            message="Operation failed",
            exit_code=1
        )
        self.assertFalse(result.success)
        self.assertEqual(result.message, "Operation failed")
        self.assertIsNone(result.data)
        self.assertEqual(result.exit_code, 1)

    def test_default_values(self) -> None:
        """Test default values for ServiceResult."""
        result = ServiceResult(success=True, message="Test")
        self.assertIsNone(result.data)
        self.assertEqual(result.exit_code, 0)


class TestScanService(TestCase):
    """Test ScanService implementation."""

    def setUp(self) -> None:
        """Set up test environment."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

        # Initialize project
        initialize_test_project(self.project_root)

        # Create some test files
        (self.project_root / "test1.py").write_text("print('hello')", encoding="utf-8")
        (self.project_root / "test2.js").write_text("console.log('hello')", encoding="utf-8")
        (self.project_root / "subdir").mkdir()
        (self.project_root / "subdir" / "test3.md").write_text("# Hello", encoding="utf-8")

    def tearDown(self) -> None:
        """Clean up test environment."""
        self.temp_dir.cleanup()

    def test_execute_success(self) -> None:
        """Test successful scan execution."""
        service = ScanService()
        result = service.execute(self.project_root)

        self.assertTrue(result.success)
        self.assertIn("files indexed", result.message)
        self.assertGreater(result.data["file_count"], 0)
        self.assertEqual(result.exit_code, 0)

    def test_execute_creates_snapshot(self) -> None:
        """Test that scan creates snapshot file."""
        service = ScanService()
        result = service.execute(self.project_root)

        snapshot_path = self.project_root / ".project-control" / "snapshot.json"
        self.assertTrue(snapshot_path.exists())

        # Verify snapshot content
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        self.assertIn("file_count", snapshot)
        self.assertIn("files", snapshot)

    def test_execute_with_missing_root(self) -> None:
        """Test scan with non-existent project root."""
        service = ScanService()
        non_existent = Path("/non/existent/path")
        result = service.execute(non_existent)

        # Should handle gracefully and return failure result
        self.assertFalse(result.success)


class TestWithErrorHandling(TestCase):
    """Test with_error_handling decorator."""

    def test_success_no_exception(self) -> None:
        """Test decorator with successful function."""
        @with_error_handling
        def success_func() -> ServiceResult:
            return ServiceResult(success=True, message="Success")

        result = success_func()
        self.assertTrue(result.success)
        self.assertEqual(result.message, "Success")

    def test_catches_project_control_error(self) -> None:
        """Test decorator catches ProjectControlError."""
        @with_error_handling
        def raises_error() -> ServiceResult:
            raise ValidationError("Test validation error")

        result = raises_error()
        self.assertFalse(result.success)
        self.assertIn("validation error", result.message)
        self.assertEqual(result.exit_code, 2)

    def test_catches_generic_exception(self) -> None:
        """Test decorator catches generic exceptions."""
        @with_error_handling
        def raises_exception() -> ServiceResult:
            raise ValueError("Test error")

        result = raises_exception()
        self.assertFalse(result.success)
        self.assertIn("Unexpected error", result.message)
        self.assertEqual(result.exit_code, 1)

    def test_preserves_return_on_success(self) -> None:
        """Test that successful returns are preserved."""
        @with_error_handling
        def returns_data() -> ServiceResult:
            return ServiceResult(
                success=True,
                message="OK",
                data={"count": 42}
            )

        result = returns_data()
        self.assertTrue(result.success)
        self.assertEqual(result.data["count"], 42)
