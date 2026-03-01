import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from project_control.core.ghost import analyze_ghost


class GhostGraphCoreTests(unittest.TestCase):
    def test_deep_flag_is_noop_and_shallow_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            snapshot_path = tmp_path / "snapshot.json"
            snapshot_path.write_text(json.dumps({"files": []}), encoding="utf-8")

            result = analyze_ghost(
                snapshot={"files": []},
                patterns={},
                snapshot_path=snapshot_path,
                deep=True,
                project_root=tmp_path,
            )
            self.assertEqual(result["graph_orphans"], [])


if __name__ == "__main__":
    unittest.main()
