from __future__ import annotations

import tempfile
import time
import unittest
from pathlib import Path
from tkinter import TclError

from project_control.gui.app import BackgroundRunner, GUIController, ProjectControlGUI


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
        self.assertIn("graph_trace", controller.workflow_handlers)
        self.assertIn("ui_verification", controller.workflow_handlers)

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
            self.assertIn("reports", app.sidebar_actions)
            self.assertIn("settings", app.tab_frames)
        finally:
            app.destroy()
