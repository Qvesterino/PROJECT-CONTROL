"""Tests for the Codebase Nebula bridge export."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from argparse import Namespace
from contextlib import redirect_stdout
from pathlib import Path

import yaml

from project_control.cli.router import cmd_nebula_export, dispatch
from project_control.config.patterns_loader import get_scan_extensions, load_patterns
from project_control.core.project_initializer import ensure_project_initialized
from project_control.core.scanner import scan_project
from project_control.core.snapshot_service import save_snapshot
from project_control.pc import build_parser
from project_control.services.nebula_export_service import run_nebula_export


def _write_fixture_project(root: Path) -> None:
    (root / "src").mkdir(parents=True, exist_ok=True)
    (root / "src" / "dup").mkdir(parents=True, exist_ok=True)
    (root / "src" / "other").mkdir(parents=True, exist_ok=True)
    (root / "src" / "ui").mkdir(parents=True, exist_ok=True)
    (root / "test-results").mkdir(parents=True, exist_ok=True)
    (root / ".project-control" / "exports").mkdir(parents=True, exist_ok=True)

    (root / "main.js").write_text(
        "import { UsedManager } from './src/UsedManager.js';\n"
        "const manager = new UsedManager();\n"
        "eval('manager.run()');\n",
        encoding="utf-8",
    )

    (root / "src" / "UsedManager.js").write_text(
        "export class UsedManager {\n"
        "  run() {\n"
        "    return true;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    (root / "src" / "UnusedManager.js").write_text(
        "export class UnusedManager {\n"
        "  dispose() {\n"
        "    return false;\n"
        "  }\n"
        "}\n",
        encoding="utf-8",
    )

    (root / "src" / "orphan.js").write_text(
        "export const orphanValue = 1;\n",
        encoding="utf-8",
    )

    (root / "src" / "legacy-helper.js").write_text(
        "export const legacyHelper = () => 'legacy';\n",
        encoding="utf-8",
    )

    (root / "src" / "session-tool.js").write_text(
        "export const sessionTool = () => 'session';\n",
        encoding="utf-8",
    )

    (root / "src" / "dup" / "Thing.js").write_text(
        "export const thing = 'left';\n",
        encoding="utf-8",
    )

    (root / "src" / "other" / "Thing.js").write_text(
        "export const thing = 'right';\n",
        encoding="utf-8",
    )

    (root / "src" / "ui" / "toolbar.ts").write_text(
        "export const toolbar = true;\n",
        encoding="utf-8",
    )

    (root / "test-results" / "screenshot-failed.png").write_bytes(b"not-a-real-png")
    (root / ".project-control" / "exports" / "ghost_old.md").write_text("# old ghost report\n", encoding="utf-8")
    (root / ".project-control" / "exports" / "ui_verification_data.json").write_text(
        json.dumps(
            {
                "timestamp": "2026-05-10T12:00:00Z",
                "app_name": "Demo UI",
                "profile_name": "demo",
                "url": "http://127.0.0.1:9000",
                "browser": "chromium",
                "html_path": str((root / "index.html").resolve()),
                "manifest_path": str((root / "src" / "shared" / "release-verification-manifest.json").resolve()),
                "total": 2,
                "passed": 0,
                "failed": 1,
                "hidden_by_context": 0,
                "not_applicable": 0,
                "warned": 1,
                "elements": [
                    {
                        "id": "toolbarButton",
                        "selector": "#toolbarButton",
                        "section": "toolbar",
                        "category": "button",
                        "criticality": "critical",
                        "proofType": "interaction",
                        "sourcePath": "src/ui/toolbar.ts",
                        "test_result": "fail",
                        "error": "Click failed",
                        "notes": ["Toolbar button did not react"],
                    },
                    {
                        "id": "previewPanel",
                        "selector": "#previewPanel",
                        "section": "preview",
                        "category": "panel",
                        "test_result": "warn",
                        "notes": ["Missing source path should keep this out of Nebula"],
                    },
                ],
                "summary": {
                    "pass_rate": 0.0,
                    "by_section": {},
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def _prepare_project(root: Path) -> None:
    ensure_project_initialized(root)
    _write_fixture_project(root)

    patterns = load_patterns(root)
    patterns["legacy_patterns"] = ["legacy"]
    patterns["patterns"] = {
        "forbidden_eval": [r"eval\\("],
    }

    patterns_path = root / ".project-control" / "patterns.yaml"
    patterns_path.write_text(yaml.safe_dump(patterns, sort_keys=False), encoding="utf-8")

    reloaded_patterns = load_patterns(root)
    snapshot = scan_project(
        str(root),
        reloaded_patterns.get("ignore_dirs", []),
        get_scan_extensions(reloaded_patterns),
    )
    for file_entry in snapshot["files"]:
        if file_entry["path"].endswith("ghost_old.md"):
            file_entry["modified"] = "2026-01-01T00:00:00+00:00"
    save_snapshot(snapshot, root)


class NebulaExportTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        _prepare_project(self.root)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_parser_exposes_nebula_export_command(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["nebula", "export"])

        self.assertEqual(args.command, "nebula")
        self.assertEqual(args.nebula_cmd, "export")

    def test_run_nebula_export_writes_locked_artifact(self) -> None:
        payload, output_path = run_nebula_export(self.root)

        self.assertTrue(output_path.exists())
        self.assertEqual(output_path.name, "nebula_bridge.json")
        self.assertEqual(payload["schemaVersion"], 2)
        self.assertEqual(payload["metadata"]["exportedBy"], "pc nebula export")
        self.assertEqual(payload["metadata"]["pathStyle"], "relative-posix")
        self.assertEqual(payload["traces"], [])
        self.assertEqual(payload["projectRoot"], self.root.resolve().as_posix())

        self.assertEqual(
            set(payload["summary"]["byKind"].keys()),
            {"ghost", "dead", "unused_system", "suspicious_pattern", "artifact_hygiene", "audit_retention", "vfx_contract", "ui_audit"},
        )
        self.assertEqual(
            set(payload["summary"]["bySeverity"].keys()),
            {"high", "medium", "low", "info"},
        )

        findings = payload["findings"]
        self.assertGreater(len(findings), 0)
        self.assertEqual(payload["summary"]["findingCount"], len(findings))

        kinds = {finding["kind"] for finding in findings}
        self.assertIn("ghost", kinds)
        self.assertIn("dead", kinds)
        self.assertIn("unused_system", kinds)
        self.assertIn("suspicious_pattern", kinds)
        self.assertIn("artifact_hygiene", kinds)
        self.assertIn("audit_retention", kinds)
        self.assertIn("ui_audit", kinds)

        ui_findings = [finding for finding in findings if finding["kind"] == "ui_audit"]
        self.assertEqual(len(ui_findings), 1)
        self.assertEqual(ui_findings[0]["path"], "src/ui/toolbar.ts")
        self.assertEqual(ui_findings[0]["severity"], "high")
        self.assertEqual(ui_findings[0]["evidence"]["sourcePath"], "src/ui/toolbar.ts")
        self.assertNotIn("previewPanel", {finding["title"] for finding in ui_findings})

        retention_findings = [finding for finding in findings if finding["kind"] == "audit_retention"]
        self.assertGreaterEqual(len(retention_findings), 1)
        self.assertTrue(any(finding["path"].endswith("ghost_old.md") for finding in retention_findings))

        for finding in findings:
            self.assertNotIn("\\", finding["path"])
            self.assertFalse(Path(finding["path"]).is_absolute())
            self.assertFalse(finding["path"].startswith("./"))

        written_payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertEqual(written_payload, payload)

    def test_parser_exposes_nebula_export_project_root(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["nebula", "export", "--project-root", str(self.root)])

        self.assertEqual(args.command, "nebula")
        self.assertEqual(args.nebula_cmd, "export")
        self.assertEqual(args.project_root, str(self.root))

    def test_dispatch_nebula_export_uses_project_root(self) -> None:
        parser = build_parser()
        args = parser.parse_args(["nebula", "export", "--project-root", str(self.root)])

        output_buffer = io.StringIO()
        original_cwd = Path.cwd()
        try:
            import os
            os.chdir(tempfile.gettempdir())
            with redirect_stdout(output_buffer):
                exit_code = dispatch(args)
        finally:
            os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        export_path = self.root / ".project-control" / "exports" / "nebula_bridge.json"
        self.assertTrue(export_path.exists())
        self.assertIn("Artifact:", output_buffer.getvalue())

    def test_cli_command_writes_exports(self) -> None:
        args = Namespace()
        original_cwd = Path.cwd()

        try:
            import os

            os.chdir(self.root)
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                exit_code = cmd_nebula_export(args)
        finally:
            os.chdir(original_cwd)

        self.assertEqual(exit_code, 0)
        export_path = self.root / ".project-control" / "exports" / "nebula_bridge.json"
        self.assertTrue(export_path.exists())


if __name__ == "__main__":
    unittest.main()
