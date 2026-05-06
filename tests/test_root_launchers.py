"""Tests for root-level convenience launchers."""

from __future__ import annotations

import runpy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]


class RootLauncherTests(unittest.TestCase):
    def test_root_pc_launcher_delegates_to_package_main(self) -> None:
        launcher = ROOT / "pc.py"

        with patch("project_control.pc.main") as main_mock:
            runpy.run_path(str(launcher), run_name="__main__")

        main_mock.assert_called_once_with()

    def test_root_gui_launcher_injects_gui_command(self) -> None:
        launcher = ROOT / "gui.py"
        original_argv = sys.argv[:]

        try:
            sys.argv = ["gui.py"]
            with patch("pc.main") as main_mock:
                runpy.run_path(str(launcher), run_name="__main__")
        finally:
            sys.argv = original_argv

        main_mock.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
