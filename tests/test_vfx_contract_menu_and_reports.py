"""Tests for VFX contract audit menu and report viewer integration."""

from __future__ import annotations

import io
import json
import tempfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

from project_control.cli.menu import _quick_actions_menu
from project_control.services.report_service import (
    get_vfx_contract_report_path,
    list_all_reports,
    view_vfx_contract_report,
)
from project_control.services.scan_service import ScanService
from project_control.services.vfx_contract_service import run_vfx_contract_audit
from project_control.ui.state import AppState


def initialize_test_project(project_root: Path) -> None:
    """Initialize a minimal project with .project-control metadata."""
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
    (control_dir / "status.yaml").write_text("tags: {}\n", encoding="utf-8")


class TestVFXContractAuditIntegration(TestCase):
    """Test VFX audit service, report registry, and menu discoverability."""

    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        initialize_test_project(self.project_root)

        (self.project_root / "ColonyVFXManager.js").write_text(
            "export class ColonyVFXManager { dispose() {} }\n",
            encoding="utf-8",
        )
        (self.project_root / "main.js").write_text(
            "import './ColonyVFXManager.js';\n",
            encoding="utf-8",
        )

        ScanService().execute(self.project_root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_run_vfx_contract_audit_writes_outputs(self) -> None:
        result, markdown_path, json_path = run_vfx_contract_audit(self.project_root)

        self.assertTrue(markdown_path.exists())
        self.assertTrue(json_path.exists())
        self.assertEqual(markdown_path, get_vfx_contract_report_path(self.project_root))
        self.assertGreaterEqual(result.summary["total_files"], 1)

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["total_files"], result.summary["total_files"])
        self.assertTrue(any(report["filename"] == "ColonyVFXManager.js" for report in payload["reports"]))

    def test_report_registry_includes_vfx_contract(self) -> None:
        reports = list_all_reports(self.project_root)
        vfx_reports = [report for report in reports if report["type"] == "vfx_contract"]

        self.assertEqual(len(vfx_reports), 1)
        self.assertEqual(vfx_reports[0]["path"], get_vfx_contract_report_path(self.project_root))

    def test_report_viewer_prints_vfx_content(self) -> None:
        run_vfx_contract_audit(self.project_root)

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            view_vfx_contract_report(self.project_root, show_content=True)

        output = buffer.getvalue()
        self.assertIn("VFX CONTRACT AUDIT", output)
        self.assertIn("FULL REPORT CONTENT", output)
        self.assertIn("ColonyVFXManager.js", output)

    def test_quick_actions_menu_shows_vfx_audit(self) -> None:
        buffer = io.StringIO()
        with patch("builtins.input", side_effect=["0"]):
            with redirect_stdout(buffer):
                _quick_actions_menu(self.project_root, AppState())

        output = buffer.getvalue()
        self.assertIn("VFX Audit", output)