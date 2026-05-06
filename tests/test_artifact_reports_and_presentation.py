from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from project_control.presentation.adapters import present_report_registry
from project_control.services.report_service import (
    get_artifact_data_path,
    get_artifact_delete_list_path,
    get_artifact_report_path,
    list_all_reports,
)


class ArtifactReportsAndPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        exports_dir = self.project_root / ".project-control" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        get_artifact_report_path(self.project_root).write_text("# Artifact Hygiene Report\n", encoding="utf-8")
        get_artifact_data_path(self.project_root).write_text('{"summary": {"safe_to_delete": 2}}', encoding="utf-8")
        get_artifact_delete_list_path(self.project_root).write_text("test-results/test-failed-home.png\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_report_registry_includes_artifact_entries(self) -> None:
        reports = list_all_reports(self.project_root)
        artifact_types = {report["type"] for report in reports if report["type"].startswith("artifacts")}

        self.assertEqual(
            artifact_types,
            {"artifacts_markdown", "artifacts_json", "artifacts_delete_list"},
        )

    def test_present_report_registry_exposes_artifact_paths(self) -> None:
        result = present_report_registry(self.project_root)

        self.assertIn("artifact_markdown", result.report_paths)
        self.assertIn("artifact_json", result.report_paths)
        self.assertIn("artifact_delete_list", result.report_paths)
        self.assertIn("Artifact Hygiene Report", result.primary_text)


if __name__ == "__main__":
    unittest.main()
