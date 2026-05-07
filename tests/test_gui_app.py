from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from tkinter import TclError
import tkinter as tk

from project_control.gui.app import BackgroundRunner, GUIController, ProjectControlGUI
from project_control.presentation.adapters import present_artifacts
from tests.test_presentation_adapters import initialize_test_project


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
        self.assertIn("audit_retention", controller.workflow_handlers)
        self.assertIn("graph_trace", controller.workflow_handlers)
        self.assertIn("ui_verification", controller.workflow_handlers)

    def test_controller_run_scan_auto_initializes_fresh_project(self) -> None:
        controller = GUIController(self.project_root)
        (self.project_root / "app.py").write_text("print('ok')\n", encoding="utf-8")

        result = controller.run_scan()

        self.assertEqual(result.workflow, "scan")
        self.assertTrue((self.project_root / ".project-control" / "patterns.yaml").exists())
        self.assertTrue((self.project_root / ".project-control" / "snapshot.json").exists())
        self.assertIn("initialized this project", result.primary_text)

    def test_present_artifacts_normalizes_summary_and_paths(self) -> None:
        initialize_test_project(self.project_root)
        exports_dir = self.project_root / ".project-control" / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        (self.project_root / ".project-control" / "snapshot.json").write_text('{"files": [], "file_count": 0}', encoding="utf-8")
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
            self.assertIn("audit_retention", app.sidebar_actions)
            self.assertIn("reports", app.sidebar_actions)
            self.assertIn("overview", app.tab_buttons)
            self.assertIn("audits", app.tab_buttons)
            self.assertIn("settings", app.tab_frames)
        finally:
            app.destroy()

    def test_gui_seeds_graph_tab_with_onboarding_state(self) -> None:
        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            graph_text = app.tab_text_widgets["graph"].get("1.0", "end")
            self.assertIn("Run Scan", graph_text)
            self.assertIn("Run Graph Report", graph_text)
            self.assertIn("Next steps", graph_text)
        finally:
            app.destroy()

    def test_gui_reports_empty_state_is_guided(self) -> None:
        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            self.assertIn("No reports are generated yet", app.report_summary_var.get())
            preview_text = app.report_preview.get("1.0", "end")
            self.assertIn("Run the related workflow first", preview_text)
        finally:
            app.destroy()

    def test_gui_busy_state_disables_actions_and_restores_after_result(self) -> None:
        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            app._set_visual_state("running", "scan", "Scanning project files.")
            self.assertTrue(app.busy)
            self.assertFalse(app.sidebar_actions["ghost"].enabled)
            self.assertTrue(app.sidebar_actions["scan"].running)

            result = present_artifacts(self.project_root)
            app._handle_result(result)

            self.assertFalse(app.busy)
            self.assertTrue(app.sidebar_actions["ghost"].enabled)
            self.assertFalse(app.sidebar_actions["scan"].running)
        finally:
            app.destroy()

    def test_gui_custom_tab_selection_switches_visible_frame(self) -> None:
        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            app._select_tab("reports")
            self.assertEqual(app.selected_tab, "reports")
            self.assertTrue(app.tab_buttons["reports"].selected)
            self.assertTrue(app.tab_frames["reports"].winfo_manager())
            self.assertEqual(app.tab_frames["overview"].winfo_manager(), "")
        finally:
            app.destroy()

    def test_gui_error_event_formats_status_and_restores_ready_controls(self) -> None:
        try:
            root = ProjectControlGUI.create_root()
            root.withdraw()
        except TclError as exc:
            self.skipTest(f"Tk unavailable in this environment: {exc}")

        app = ProjectControlGUI(self.project_root, root=root)
        try:
            app._set_visual_state("running", "graph_report", "Building graph.")
            app._handle_error("graph_report", RuntimeError("Graph not found"))
            self.assertEqual(app.status_var.get(), "Graph Report failed")
            self.assertTrue(app.sidebar_actions["scan"].enabled)
            graph_text = app.tab_text_widgets["graph"].get("1.0", tk.END)
            self.assertIn("Run Graph Report", graph_text)
        finally:
            app.destroy()

    def test_gui_reports_preview_lists_artifact_outputs(self) -> None:
        export_dir = self.project_root / ".project-control" / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        (export_dir / "artifact_candidates.md").write_text("# Artifact Hygiene Report\n", encoding="utf-8")
        (export_dir / "artifact_candidates.json").write_text('{"summary": {"safe_to_delete": 1}}', encoding="utf-8")
        (export_dir / "delete_candidates.txt").write_text("test-results/test-failed-home.png\n", encoding="utf-8")
        (export_dir / "audit_retention_candidates.md").write_text("# Audit Retention Report\n", encoding="utf-8")
        (export_dir / "audit_retention_candidates.json").write_text('{"summary": {"safe_to_delete": 1}}', encoding="utf-8")
        (export_dir / "audit_delete_candidates.txt").write_text(".project-control/exports/ghost_old.md\n", encoding="utf-8")

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
            self.assertTrue(any("Audit Retention Report" in label for label in labels))
            self.assertTrue(any("Audit Retention Data" in label for label in labels))
            self.assertTrue(any("Audit Delete Candidate List" in label for label in labels))
            self.assertIn("report artifacts are available", app.report_summary_var.get())
        finally:
            app.destroy()
