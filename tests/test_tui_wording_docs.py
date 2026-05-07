from __future__ import annotations

import unittest
from pathlib import Path


class TUIWordingDocsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_root = Path(__file__).resolve().parents[1]

    def test_readme_uses_tui_as_primary_term(self) -> None:
        readme = (self.repo_root / "README.md").read_text(encoding="utf-8")
        self.assertIn("pc tui", readme)
        self.assertIn("was removed in this release", readme)
        self.assertIn(".\\pc.ps1 gui", readme)
        self.assertIn("pipx install .", readme)
        self.assertNotIn("python pc.py gui", readme)
        self.assertNotIn("| `pc ui` |", readme)

    def test_manual_documents_tui_and_hygiene_workflows(self) -> None:
        manual = (self.repo_root / "MANUAL.md").read_text(encoding="utf-8")
        self.assertIn("## TUI", manual)
        self.assertIn("pc tui verify", manual)
        self.assertIn(".\\pc.ps1 gui", manual)
        self.assertIn("pipx install project-control", manual)
        self.assertIn("pc artifacts", manual)
        self.assertIn("pc audits retention", manual)
        self.assertIn("Quick Actions", manual)
        self.assertIn("`10` | Favorites", manual)
        self.assertIn("were removed in this release", manual)

    def test_changelog_contains_removal_and_migration_note(self) -> None:
        changelog = (self.repo_root / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("### Removed", changelog)
        self.assertIn("pc ui", changelog)
        self.assertIn("pc ui verify", changelog)
        self.assertIn("pc tui verify", changelog)

    def test_launcher_scripts_use_tui(self) -> None:
        start_menu = (self.repo_root / "start_menu.bat").read_text(encoding="utf-8")
        start_gui = (self.repo_root / "start_gui.bat").read_text(encoding="utf-8")
        open_launcher = (self.repo_root / "OPEN_PROJECT_CONTROL.bat").read_text(encoding="utf-8")
        root_launcher = (self.repo_root / "pc.py").read_text(encoding="utf-8")
        ps_launcher = (self.repo_root / "pc.ps1").read_text(encoding="utf-8")
        cmd_launcher = (self.repo_root / "pc.cmd").read_text(encoding="utf-8")

        self.assertIn("pc.cmd\" tui", start_menu)
        self.assertNotIn("pc.py ui", start_menu)
        self.assertIn("pc.cmd", start_gui)
        self.assertIn(".\\pc.cmd tui", open_launcher)
        self.assertIn("python .\\pc.py tui", open_launcher)
        self.assertNotIn("python pc.py ui", open_launcher)
        self.assertIn("python .\\\\pc.py tui", root_launcher)
        self.assertIn(".\\\\pc.cmd tui", root_launcher)
        self.assertIn("pc.py", ps_launcher)
        self.assertIn("pc.py", cmd_launcher)


if __name__ == "__main__":
    unittest.main()
