import unittest

from project_control.graph.extractors.js_ts import JsTsExtractor
from project_control.graph.extractors.python_ast import PythonAstExtractor
from project_control.graph.trace import trace_paths


class ExtractorTests(unittest.TestCase):
    def test_js_extractor_line_numbers(self):
        content = "import React from 'react';\nconst lib = require(\"lib\");\nconst dyn = import('dyn');\n"
        extractor = JsTsExtractor()
        occs = extractor.extract("app.js", content)
        kinds_lines = {(o.kind, o.line) for o in occs}
        self.assertIn(("esm", 1), kinds_lines)
        self.assertIn(("cjs", 2), kinds_lines)
        self.assertIn(("dynamic", 3), kinds_lines)

    def test_python_ast_extractor_lines(self):
        content = "import os\nfrom .utils import helper\nfrom pkg.mod import thing\n"
        extractor = PythonAstExtractor()
        occs = extractor.extract("app.py", content)
        spec_line = {(o.specifier, o.line, o.kind) for o in occs}
        self.assertIn(("os", 1, "py_import"), spec_line)
        self.assertIn((".utils", 2, "py_from"), spec_line)
        self.assertIn(("pkg.mod", 3, "py_from"), spec_line)


class TraceTests(unittest.TestCase):
    def test_cycle_trace_stops(self):
        graph = {
            "nodes": [
                {"id": 1, "path": "a.ts"},
                {"id": 2, "path": "b.ts"},
            ],
            "edges": [
                {
                    "fromId": 1,
                    "toId": 2,
                    "specifier": "./b",
                    "kind": "esm",
                    "line": 1,
                    "lineText": "import './b'",
                    "isExternal": False,
                    "isDynamic": False,
                    "resolvedPath": "b.ts",
                },
                {
                    "fromId": 2,
                    "toId": 1,
                    "specifier": "./a",
                    "kind": "esm",
                    "line": 1,
                    "lineText": "import './a'",
                    "isExternal": False,
                    "isDynamic": False,
                    "resolvedPath": "a.ts",
                },
            ],
            "entrypoints": [1],
        }
        traces = trace_paths(graph, target_node_id=1, direction="outbound", max_depth=5, max_paths=10)
        outbound = traces.get("outbound", [])
        self.assertTrue(outbound, "should return at least one path")
        self.assertTrue(any(tp.ended_by_cycle for tp in outbound))
        self.assertEqual(outbound[0].nodes, [1, 2, 1])


if __name__ == "__main__":
    unittest.main()
