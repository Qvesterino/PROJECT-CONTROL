"""Tests for the VFX contract audit analyzer and CLI command."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

from project_control.analysis.vfx_contract_audit import analyze_vfx_contract, vfx_contract_result_to_dict
from project_control.cli.router import cmd_audit_vfx
from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.pc import build_parser


def _create_vfx_project(root: Path) -> None:
    (root / "main.js").write_text(
        "import { TestParticleFX } from './TestParticleFX.js';\n"
        "const fx = new TestParticleFX();\n",
        encoding="utf-8",
    )

    (root / "TestParticleFX.js").write_text(
        "/** VFX test asset for contract audit. */\n"
        "export class TestParticleFX {\n"
        "  constructor(scene) {\n"
        "    this.scene = scene;\n"
        "    this.enabled = true;\n"
        "  }\n"
        "\n"
        "  update(deltaTime) {\n"
        "    if (!this.enabled) {\n"
        "      return;\n"
        "    }\n"
        "    console.log('tick', deltaTime);\n"
        "  }\n"
        "\n"
        "  dispose() {\n"
        "    this.geometry.dispose();\n"
        "    this.material.dispose();\n"
        "  }\n"
        "}\n"
        "const points = new THREE.Points();\n"
        "scene.add(points);\n",
        encoding="utf-8",
    )


class VFXContractAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        _create_vfx_project(self.root)

        snapshot = scan_project(str(self.root), ["node_modules", ".git"], [".js"])
        save_snapshot(snapshot, self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parser_exposes_audit_vfx_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "vfx"])

        self.assertEqual(args.command, "audit")
        self.assertEqual(args.audit_cmd, "vfx")

    def test_analyze_vfx_contract_returns_reports(self) -> None:
        result = analyze_vfx_contract(self.root)

        self.assertGreaterEqual(len(result.reports), 1)
        self.assertEqual(result.summary["total_files"], len(result.reports))

        report = result.reports[0]
        self.assertEqual(report.filename, "TestParticleFX.js")
        self.assertEqual(report.owner, "main.js")
        self.assertEqual(report.category, "PARTICLE FX")
        self.assertIn("TRIGGER", {check.name for check in report.checks})
        self.assertIn("DISPOSE", {check.name for check in report.checks})

    def test_cli_command_writes_exports(self) -> None:
        args = Namespace(
            project_root=str(self.root),
            output=None,
            json=False,
        )

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exit_code = cmd_audit_vfx(args)

        self.assertEqual(exit_code, 0)

        export_dir = self.root / ".project-control" / "exports"
        markdown_path = export_dir / "vfx_contract_audit_report.md"
        json_path = export_dir / "vfx_contract_audit_data.json"

        self.assertTrue(markdown_path.exists())
        self.assertTrue(json_path.exists())

        data = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertIn("reports", data)
        self.assertEqual(data["summary"]["total_files"], 1)

    def test_result_serialization_is_stable(self) -> None:
        result = analyze_vfx_contract(self.root)
        payload = vfx_contract_result_to_dict(result)

        self.assertIn("summary", payload)
        self.assertIn("reports", payload)
        self.assertEqual(payload["reports"][0]["filename"], "TestParticleFX.js")


if __name__ == "__main__":
    unittest.main()