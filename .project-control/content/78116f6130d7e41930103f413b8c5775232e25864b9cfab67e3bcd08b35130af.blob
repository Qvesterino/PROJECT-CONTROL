import tempfile
import unittest
from pathlib import Path

from project_control.config.graph_config import GraphConfig
from project_control.graph.builder import GraphBuilder
from project_control.graph.metrics import compute_metrics
from project_control.core.snapshot_service import save_snapshot
from project_control.core.scanner import scan_project
from project_control.core.content_store import ContentStore


IGNORE_DIRS = [".git", ".project-control", "node_modules", "__pycache__"]
EXTS = [".js", ".ts", ".tsx", ".jsx", ".mjs", ".cjs"]


def _create_snapshot(project_root: Path):
    snapshot = scan_project(str(project_root), IGNORE_DIRS, EXTS)
    save_snapshot(snapshot, project_root)
    return snapshot


class GraphCoreTests(unittest.TestCase):
    def test_graph_resolves_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "src").mkdir(parents=True, exist_ok=True)
            (root / "src" / "main.ts").write_text("import './utils'\n", encoding="utf-8")
            (root / "src" / "utils").mkdir()
            (root / "src" / "utils" / "index.tsx").write_text("export const x = 1;\n", encoding="utf-8")

            snapshot = _create_snapshot(root)
            store = ContentStore(snapshot, root / ".project-control" / "snapshot.json")
            config = GraphConfig(entrypoints=["src/main.ts"])
            builder = GraphBuilder(root, snapshot, store, config)
            graph = builder.build()
            edge = next((e for e in graph["edges"] if e["specifier"] == "./utils"), None)
            self.assertIsNotNone(edge)
            self.assertEqual(edge["resolvedPath"], "src/utils/index.tsx")
            self.assertIsNotNone(edge["toId"])

    def test_cycle_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir(parents=True, exist_ok=True)
            (root / "app" / "a.ts").write_text("import './b'\n", encoding="utf-8")
            (root / "app" / "b.ts").write_text("import './c'\n", encoding="utf-8")
            (root / "app" / "c.ts").write_text("import './a'\n", encoding="utf-8")

            snapshot = _create_snapshot(root)
            store = ContentStore(snapshot, root / ".project-control" / "snapshot.json")
            config = GraphConfig(entrypoints=["app/a.ts"])
            graph = GraphBuilder(root, snapshot, store, config).build()
            metrics = compute_metrics(graph, config)
            cycles = metrics.get("cycles", [])
            self.assertTrue(any(set(group) == {"app/a.ts", "app/b.ts", "app/c.ts"} for group in cycles))

    def test_orphan_detection(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir(parents=True, exist_ok=True)
            (root / "app" / "entry.ts").write_text("import './used'\n", encoding="utf-8")
            (root / "app" / "used.ts").write_text("export const y = 2;\n", encoding="utf-8")
            (root / "app" / "unused.ts").write_text("// unused\n", encoding="utf-8")

            snapshot = _create_snapshot(root)
            store = ContentStore(snapshot, root / ".project-control" / "snapshot.json")
            config = GraphConfig(entrypoints=["app/entry.ts"])
            graph = GraphBuilder(root, snapshot, store, config).build()
            metrics = compute_metrics(graph, config)
            orphans = [o["path"] for o in metrics.get("orphanCandidates", []) if o["reason"] == "unreachable"]
            self.assertIn("app/unused.ts", orphans)

    def test_implicit_entrypoints_zero_fan_in(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir(parents=True, exist_ok=True)
            (root / "app" / "a.ts").write_text("import './b'\n", encoding="utf-8")
            (root / "app" / "b.ts").write_text("// leaf\n", encoding="utf-8")
            (root / "app" / "c.ts").write_text("// isolated\n", encoding="utf-8")

            snapshot = _create_snapshot(root)
            store = ContentStore(snapshot, root / ".project-control" / "snapshot.json")
            config = GraphConfig(entrypoints=[])  # triggers implicit roots
            graph = GraphBuilder(root, snapshot, store, config).build()
            # entrypoints should be nodes with zero fan-in: a.ts and c.ts (b has fan-in 1)
            id_to_path = {n["id"]: n["path"] for n in graph["nodes"]}
            ep_paths = sorted(id_to_path[i] for i in graph["entrypoints"])
            self.assertEqual(ep_paths, ["app/a.ts", "app/c.ts"])

    def test_external_specifier_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "app").mkdir(parents=True, exist_ok=True)
            (root / "app" / "a.ts").write_text("import React from 'react';\nimport x from 'lodash';\nimport y from 'react';\n", encoding="utf-8")

            snapshot = _create_snapshot(root)
            store = ContentStore(snapshot, root / ".project-control" / "snapshot.json")
            config = GraphConfig(entrypoints=["app/a.ts"])
            graph = GraphBuilder(root, snapshot, store, config).build()
            metrics = compute_metrics(graph, config)
            externals = metrics.get("externals", {}).get("bySpecifier", {})
            self.assertEqual(externals.get("react"), 2)
            self.assertEqual(externals.get("lodash"), 1)


if __name__ == "__main__":
    unittest.main()
