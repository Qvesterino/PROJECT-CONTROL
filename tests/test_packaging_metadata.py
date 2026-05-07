from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


class PackagingMetadataTests(unittest.TestCase):
    def test_pyproject_dependencies_are_in_project_table(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

        project = pyproject["project"]
        self.assertIn("dependencies", project)
        self.assertIsInstance(project["dependencies"], list)
        self.assertNotIn("dependencies", project["urls"])

    def test_project_urls_are_strings(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        pyproject = tomllib.loads((repo_root / "pyproject.toml").read_text(encoding="utf-8"))

        for value in pyproject["project"]["urls"].values():
            self.assertIsInstance(value, str)


if __name__ == "__main__":
    unittest.main()
