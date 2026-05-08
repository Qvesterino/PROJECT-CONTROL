from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from project_control.cli.router import cmd_audit_patron, dispatch
from project_control.config.patron_path_loader import get_patron_path_contract_path
from project_control.core.project_initializer import ensure_project_initialized
from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.pc import build_parser
from project_control.services.nebula_export_service import run_nebula_export
from project_control.services.patron_path_service import run_patron_path_audit
from project_control.services.report_service import list_all_reports


def _write_project_fixture(root: Path) -> None:
    (root / "main.js").write_text("console.log('hello');\n", encoding="utf-8")


class PatronPathAuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.project_root = self.workspace / "project"
        self.codebase_nebula_root = self.workspace / "Codebase_Nebula"
        self.patrons_path_root = self.workspace / "Patrons_Path"

        self.codebase_nebula_root.mkdir(parents=True, exist_ok=True)
        self.patrons_path_root.mkdir(parents=True, exist_ok=True)

        ensure_project_initialized(self.project_root)
        _write_project_fixture(self.project_root)

        snapshot = scan_project(str(self.project_root), [".git", ".project-control"], [".js"])
        save_snapshot(snapshot, self.project_root)
        run_nebula_export(self.project_root)

        contract = {
            "codebase_nebula_root": str(self.codebase_nebula_root),
            "patrons_path_root": str(self.patrons_path_root),
            "file_genome": {
                "analyze_url": "https://file-genome.com/analyze",
                "batch_url": "https://file-genome.com/batch",
            },
        }
        contract_path = get_patron_path_contract_path(self.project_root)
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parser_exposes_audit_patron_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["audit", "patron", "--project-root", str(self.project_root)])

        self.assertEqual(args.command, "audit")
        self.assertEqual(args.audit_cmd, "patron")
        self.assertEqual(args.project_root, str(self.project_root))

    def test_run_patron_path_audit_writes_outputs(self) -> None:
        result, markdown_path, json_path = run_patron_path_audit(self.project_root)

        self.assertEqual(result.summary["overallStatus"], "healthy")
        self.assertTrue(markdown_path.exists())
        self.assertTrue(json_path.exists())
        self.assertEqual(markdown_path.name, "patron_path_contract_report.md")
        self.assertEqual(json_path.name, "patron_path_contract_data.json")

        payload = json.loads(json_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["summary"]["errorCount"], 0)
        self.assertEqual(payload["contract"]["codebase_nebula_root"], str(self.codebase_nebula_root))
        self.assertEqual(payload["contract"]["patrons_path_root"], str(self.patrons_path_root))
        self.assertEqual(payload["contract"]["file_genome"]["analyze_url"], "https://file-genome.com/analyze")
        self.assertEqual(payload["contract"]["file_genome"]["batch_url"], "https://file-genome.com/batch")
        self.assertTrue(Path(payload["nebulaBridgePath"]).exists())

    def test_cli_command_writes_exports(self) -> None:
        args = Namespace(project_root=str(self.project_root), output=None, json=False)
        buffer = io.StringIO()

        with redirect_stdout(buffer):
            exit_code = cmd_audit_patron(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("Patron's Path Integration Contract", buffer.getvalue())

    def test_report_registry_includes_patron_path_contract(self) -> None:
        reports = list_all_reports(self.project_root)
        report_types = {report["type"] for report in reports}

        self.assertIn("patron_path_contract", report_types)
        self.assertIn("patron_path_contract_json", report_types)


if __name__ == "__main__":
    unittest.main()
