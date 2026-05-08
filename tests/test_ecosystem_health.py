from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from project_control.cli.router import cmd_ecosystem_health, dispatch
from project_control.config.patron_path_loader import get_patron_path_contract_path
from project_control.core.pre_flight import HealthReport, HealthStatus
from project_control.core.project_initializer import ensure_project_initialized
from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.pc import build_parser
from project_control.services.ecosystem_health_service import run_ecosystem_health


def _write_project_fixture(root: Path) -> None:
    (root / "main.js").write_text("console.log('hello');\n", encoding="utf-8")


def _healthy_report(project_root: Path) -> HealthReport:
    check = HealthStatus(name="ok", is_healthy=True, message="ok")
    return HealthReport(
        project_root=project_root,
        overall_status="healthy",
        checks=[check],
        errors=[],
        warnings=[],
        suggestions=[],
    )


class EcosystemHealthTests(unittest.TestCase):
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

    def test_parser_exposes_ecosystem_health_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["ecosystem", "health", "--project-root", str(self.project_root)])

        self.assertEqual(args.command, "ecosystem")
        self.assertEqual(args.ecosystem_cmd, "health")
        self.assertEqual(args.project_root, str(self.project_root))

    def test_run_ecosystem_health_writes_outputs(self) -> None:
        with patch("project_control.services.ecosystem_health_service.health_check", return_value=_healthy_report(self.project_root)):
            payload, markdown_path, json_path = run_ecosystem_health(self.project_root)

        self.assertEqual(payload["summary"]["overallStatus"], "healthy")
        self.assertTrue(markdown_path.exists())
        self.assertTrue(json_path.exists())
        self.assertEqual(payload["summary"]["projectControlStatus"], "healthy")
        self.assertEqual(payload["summary"]["nebulaBridgeStatus"], "healthy")
        self.assertEqual(payload["summary"]["downstreamStatus"], "healthy")
        self.assertGreaterEqual(payload["nebulaBridge"]["findingCount"], 1)
        self.assertEqual(payload["downstreamReadiness"]["summary"]["overallStatus"], "healthy")

    def test_run_ecosystem_health_warns_when_downstream_root_missing(self) -> None:
        missing_root = self.workspace / "Missing_Patrons_Path"
        contract = {
            "codebase_nebula_root": str(self.codebase_nebula_root),
            "patrons_path_root": str(missing_root),
            "file_genome": {
                "analyze_url": "https://file-genome.com/analyze",
                "batch_url": "https://file-genome.com/batch",
            },
        }
        contract_path = get_patron_path_contract_path(self.project_root)
        contract_path.write_text(yaml.safe_dump(contract, sort_keys=False), encoding="utf-8")

        with patch("project_control.services.ecosystem_health_service.health_check", return_value=_healthy_report(self.project_root)):
            payload, _, _ = run_ecosystem_health(self.project_root)

        self.assertEqual(payload["summary"]["overallStatus"], "warning")
        self.assertEqual(payload["summary"]["downstreamStatus"], "warning")

    def test_cli_command_writes_exports(self) -> None:
        args = Namespace(project_root=str(self.project_root), output=None, json=False)
        buffer = io.StringIO()

        with patch("project_control.services.ecosystem_health_service.health_check", return_value=_healthy_report(self.project_root)):
            with redirect_stdout(buffer):
                exit_code = cmd_ecosystem_health(args)

        self.assertEqual(exit_code, 0)
        self.assertIn("Ecosystem Health", buffer.getvalue())

    def test_dispatch_ecosystem_health_uses_parser(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["ecosystem", "health", "--project-root", str(self.project_root)])

        with patch("project_control.services.ecosystem_health_service.health_check", return_value=_healthy_report(self.project_root)):
            exit_code = dispatch(args)

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
