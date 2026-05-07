from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from project_control.analysis.semantic_detector import analyze
from project_control.core.content_store import ContentStore


class SemanticDetectorTests(unittest.TestCase):
    def test_analyze_uses_project_root_from_snapshot_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            content_dir = control_dir / "content"
            control_dir.mkdir(parents=True, exist_ok=True)
            content_dir.mkdir(parents=True, exist_ok=True)

            snapshot = {
                "files": [
                    {
                        "path": "src/a.py",
                        "sha256": "a" * 64,
                    }
                ]
            }
            snapshot_path = control_dir / "snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            (content_dir / f"{'a' * 64}.blob").write_text("print('hello world')\n" * 10, encoding="utf-8")
            store = ContentStore(snapshot, snapshot_path)

            with patch("project_control.analysis.semantic_detector.EmbeddingService", side_effect=ImportError("missing")) as service_mock:
                analyze(snapshot, {}, store)

        service_mock.assert_called_once_with(project_root)

    def test_analyze_skips_missing_embedding_dependencies_without_stdout_noise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            control_dir = project_root / ".project-control"
            content_dir = control_dir / "content"
            control_dir.mkdir(parents=True, exist_ok=True)
            content_dir.mkdir(parents=True, exist_ok=True)

            snapshot = {
                "files": [
                    {
                        "path": "src/a.py",
                        "sha256": "b" * 64,
                    }
                ]
            }
            snapshot_path = control_dir / "snapshot.json"
            snapshot_path.write_text(json.dumps(snapshot), encoding="utf-8")
            (content_dir / f"{'b' * 64}.blob").write_text("print('hello world')\n" * 10, encoding="utf-8")
            store = ContentStore(snapshot, snapshot_path)
            stdout = io.StringIO()

            with patch("project_control.analysis.semantic_detector.EmbeddingService", side_effect=ImportError("missing")):
                with self.assertLogs("project_control.analysis.semantic_detector", level="WARNING") as logs:
                    with redirect_stdout(stdout):
                        result = analyze(snapshot, {}, store)

        self.assertEqual(result, [])
        self.assertEqual(stdout.getvalue(), "")
        self.assertTrue(any("semantic analysis skipped" in message for message in logs.output))


if __name__ == "__main__":
    unittest.main()
