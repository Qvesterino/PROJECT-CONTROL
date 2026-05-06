from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from tkinter import TclError

from project_control.gui.app import BackgroundRunner, GUIController, ProjectControlGUI
from project_control.presentation.adapters import present_artifacts


class GUIAppTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_controller_exposes_expected_workflows(self) -> None:
        controller = GUIController(self.project_root)
        self.assertIn("scan", controller.workflow_handlers)
        self.assertIn("ghost", controller.workflow_handlers)
        self.assertIn("artifacts", controller.workflow_handlers)
        self.assertIn("graph_trace", controller.workflow_handlers)
        self.assertIn("ui_verification", controller.workflow_handlers)

    def test_present_artifacts_normalizes_summary_and_paths(self) -> None:
        exports_dir = self.project_root / ".project-control" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        fake_payload = {
            "result": {
                "summary": {
                    "safe_to_delete": 3,
                    "safe_to_delete_mb": 12.5,
                    "duplicate_groups": 2,
                    "high_confidence_cleanup_candidates": 4,
                },
                "safe_to_delete_candidates": [
                    {"path": "test-results/a.png", "size_bytes": 12},
                    {"path": "test-results/b.png", "size_bytes": 8},
                ],
            },
            "paths": {
                "markdown": exports_dir / "artifact_candidates.md",
                "json": exports_dir / "artifact_candidates.json",
                "delete_list": exports_dir / "delete_candidates.txt",
            },
        }

        from unittest.mock import patch

        with patch("project_control.presentation.adapters.run_artifact_hygiene", return_value=fake_payload):
            result = present_artifacts(self.project_root)

        self.assertEqual(result.workflow, "artifacts")
        self.assertEqual(result.title, "Artifact Hygiene")
        self.assertEqual(result.summary["safe_to_delete"], 3)
        self.assertEqual(result.summary["reclaimable_mb"], 12.5)
        self.assertIn("delete_list", result.report_paths)
        self.assertIn("Top Safe Delete Candidates", result.primary_text)

    def test_background_runner_delivers_result(self) -> None:
        runner = BackgroundRunner()
        runner.submit("scan", lambda: "done")

        deadline = time.time() + 2
        events = []
        while time.time() < deadline and not events:
            events = runner.poll()
            if not events:
                time.sleep(0.05)

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].kind, "result")
        self.assertEqual(events[0].payload, "done")

    def test_gui_builds_root_and_sidebar_actions(self) -> None:
        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            self.assertIn("scan", app.sidebar_actions)
            self.assertIn("artifacts", app.sidebar_actions)
            self.assertIn("reports", app.sidebar_actions)
            self.assertIn("settings", app.tab_frames)
        finally:
            app.destroy()

    def test_gui_reports_preview_lists_artifact_outputs(self) -> None:
        export_dir = self.project_root / ".project-control" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "artifact_candidates.md").write_text("# Artifact Hygiene Report\n", encoding="utf-8")
        (export_dir / "artifact_candidates.json").write_text('{"summary": {"safe_to_delete": 1}}', encoding="utf-8")
        (export_dir / "delete_candidates.txt").write_text("test-results/test-failed-home.png\n", encoding="utf-8")

        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            labels = list(app.report_paths_cache.keys())
            self.assertTrue(any("Artifact Hygiene Report" in label for label in labels))
            self.assertTrue(any("Artifact Hygiene Data" in label for label in labels))
            self.assertTrue(any("Artifact Delete Candidate List" in label for label in labels))
        finally:
            app.destroy()
