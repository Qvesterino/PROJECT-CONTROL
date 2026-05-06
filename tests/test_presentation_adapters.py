from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from project_control.presentation.adapters import (
    present_scan,
    present_ui_verification,
    present_vfx_audit,
)


def initialize_test_project(project_root: Path) -> None:
    control_dir = project_root / ".project-control"
    control_dir.mkdir(exist_ok=True)
    (control_dir / "patterns.yaml").write_text(
        "\n".join(
            [
                "writers:",
                "  - scale",
                "  - emissive",
                "  - opacity",
                "  - position",
                "entrypoints:",
                "  - main.js",
                "  - index.ts",
                "ignore_dirs:",
                "  - .git",
                "  - .project-control",
                "  - node_modules",
                "  - __pycache__",
                "extensions:",
                "  - .py",
                "  - .js",
                "  - .ts",
                "  - .md",
                "  - .txt",
            ]
        ),
        encoding="utf-8",
    )


class PresentationAdapterTests(unittest.TestCase):
    def test_present_scan_returns_summary_and_snapshot_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            initialize_test_project(project_root)
            (project_root / "main.py").write_text("print('ok')\n", encoding="utf-8")

            result = present_scan(project_root)

            self.assertEqual(result.workflow, "scan")
            self.assertGreaterEqual(result.summary["file_count"], 1)
            self.assertTrue(result.report_paths["snapshot"].exists())
            self.assertTrue(result.primary_text)

    def test_present_vfx_audit_preserves_report_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            markdown_path = project_root / "vfx.md"
            json_path = project_root / "vfx.json"
            fake_result = object()

            with patch("project_control.presentation.adapters.run_vfx_contract_audit", return_value=(fake_result, markdown_path, json_path)):
                with patch(
                    "project_control.presentation.adapters.vfx_contract_result_to_dict",
                    return_value={"summary": {"total_files": 4, "keep": 2, "fix": 1, "isolate": 1, "kill": 0}},
                ):
                    with patch("project_control.presentation.adapters.render_vfx_contract_console", return_value="vfx output"):
                        result = present_vfx_audit(project_root)

            self.assertEqual(result.summary["total_files"], 4)
            self.assertEqual(result.report_paths["markdown"], markdown_path)
            self.assertEqual(result.report_paths["json"], json_path)
            self.assertEqual(result.primary_text, "vfx output")

    def test_present_ui_verification_preserves_report_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            config_path = project_root / "ui.yaml"
            markdown_path = project_root / "ui.md"
            json_path = project_root / "ui.json"
            html_path = project_root / "ui.html"
            fake_report = SimpleNamespace(
                profile_name="demo",
                passed=8,
                failed=1,
                warned=2,
                summary={"pass_rate": 88.9},
            )

            with patch(
                "project_control.presentation.adapters.run_ui_verification_profile",
                return_value=(fake_report, config_path, markdown_path, json_path, html_path),
            ):
                with patch(
                    "project_control.presentation.adapters.render_ui_verification_console_summary",
                    return_value="ui output",
                ):
                    result = present_ui_verification(project_root, profile_name="demo")

            self.assertEqual(result.summary["profile"], "demo")
            self.assertEqual(result.report_paths["config"], config_path)
            self.assertEqual(result.report_paths["markdown"], markdown_path)
            self.assertEqual(result.report_paths["json"], json_path)
            self.assertEqual(result.report_paths["html"], html_path)
            self.assertEqual(result.primary_text, "ui output")
