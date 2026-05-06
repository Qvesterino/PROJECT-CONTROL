from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import yaml

from project_control.config.patterns_loader import get_default_patterns, get_scan_extensions, load_patterns
from project_control.core.snapshot_service import load_snapshot
from project_control.services.scan_service import ScanService


class ArtifactConfigTests(unittest.TestCase):
    def test_default_patterns_include_artifacts(self) -> None:
        patterns = get_default_patterns()

        self.assertIn("artifacts", patterns)
        self.assertIn(".png", patterns["artifacts"]["extensions"])
        self.assertTrue(patterns["artifacts"]["enabled"])

    def test_nested_artifact_config_merge_preserves_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            control_dir.mkdir(parents=True, exist_ok=True)
            (control_dir / "patterns.yaml").write_text(
                yaml.dump({"artifacts": {"min_score": 11}}, sort_keys=False),
                encoding="utf-8",
            )

            patterns = load_patterns(project_root)

        self.assertEqual(patterns["artifacts"]["min_score"], 11)
        self.assertEqual(patterns["artifacts"]["older_than_days"], 30)
        self.assertIn(".svg", patterns["artifacts"]["extensions"])

    def test_scan_includes_artifact_extensions_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            control_dir.mkdir(parents=True, exist_ok=True)
            (project_root / "capture.png").write_bytes(b"artifact")
            (control_dir / "patterns.yaml").write_text(
                yaml.dump(
                    {
                        "writers": ["scale"],
                        "entrypoints": ["main.py"],
                        "ignore_dirs": [".git", ".project-control"],
                        "extensions": [".py"],
                    },
                    sort_keys=False,
                ),
                encoding="utf-8",
            )

            service = ScanService()
            result = service.execute(project_root)
            snapshot = load_snapshot(project_root)
            scan_extensions = get_scan_extensions(load_patterns(project_root))

        self.assertTrue(result.success)
        self.assertIn(".png", scan_extensions)
        self.assertEqual(snapshot["file_count"], 1)
        self.assertEqual(snapshot["files"][0]["path"], "capture.png")


if __name__ == "__main__":
    unittest.main()
