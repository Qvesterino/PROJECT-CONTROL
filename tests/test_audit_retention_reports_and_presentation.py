from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from project_control.presentation.adapters import present_audit_retention, present_report_registry
from project_control.services.report_service import (
    get_audit_delete_list_path,
    get_audit_retention_data_path,
    get_audit_retention_report_path,
    list_all_reports,
)


class AuditRetentionReportsAndPresentationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        exports_dir = self.project_root / ".project-control" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        get_audit_retention_report_path(self.project_root).write_text("# Audit Retention Report\n", encoding="utf-8")
        get_audit_retention_data_path(self.project_root).write_text('{"summary": {"safe_to_delete": 2}}', encoding="utf-8")
        get_audit_delete_list_path(self.project_root).write_text(".project-control/exports/ghost_old.md\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_present_audit_retention_normalizes_summary_and_paths(self) -> None:
        fake_payload = {
            "result": {
                "summary": {
                    "safe_to_delete": 3,
                    "safe_to_delete_mb": 1.5,
                    "duplicate_groups": 2,
                    "high_confidence_cleanup_candidates": 2,
                    "families_detected": 4,
                },
                "safe_to_delete_candidates": [
                    {"path": ".project-control/exports/ghost_old.md", "size_bytes": 120},
                ],
            },
            "paths": {
                "markdown": get_audit_retention_report_path(self.project_root),
                "json": get_audit_retention_data_path(self.project_root),
                "delete_list": get_audit_delete_list_path(self.project_root),
            },
        }

        with patch("project_control.presentation.adapters.run_audit_retention", return_value=fake_payload):
            result = present_audit_retention(self.project_root)

        self.assertEqual(result.workflow, "audit_retention")
        self.assertEqual(result.title, "Audit Retention")
        self.assertEqual(result.summary["safe_to_delete"], 3)
        self.assertEqual(result.summary["high_confidence"], 2)
        self.assertEqual(result.summary["families_detected"], 4)
        self.assertIn("delete_list", result.report_paths)
        self.assertIn("Top Safe Delete Candidates", result.primary_text)

    def test_report_registry_includes_audit_retention_entries(self) -> None:
        reports = list_all_reports(self.project_root)
        retention_types = {report["type"] for report in reports if report["type"].startswith("audit_retention")}

        self.assertEqual(
            retention_types,
            {"audit_retention_markdown", "audit_retention_json", "audit_retention_delete_list"},
        )

    def test_present_report_registry_exposes_audit_retention_paths(self) -> None:
        result = present_report_registry(self.project_root)

        self.assertIn("audit_retention_markdown", result.report_paths)
        self.assertIn("audit_retention_json", result.report_paths)
        self.assertIn("audit_retention_delete_list", result.report_paths)
        self.assertIn("Audit Retention Report", result.primary_text)


if __name__ == "__main__":
    unittest.main()
