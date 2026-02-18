# Import Graph Orphans

## Legend
(Directory tree based on import graph reachability)

# NOTE
This report is static-import based.
Dynamic runtime wiring (FrameScheduler, registries, side-effects) is not detected.

- project_control\__init__.py
- project_control\analysis\__init__.py
- project_control\analysis\duplicate_detector.py
- project_control\analysis\entrypoint_policy.py
- project_control\analysis\graph_anomaly.py
- project_control\analysis\graph_drift.py
- project_control\analysis\graph_exporter.py
- project_control\analysis\graph_metrics.py
- project_control\analysis\graph_trend.py
- project_control\analysis\import_graph_detector.py
- project_control\analysis\import_graph_engine.py
- project_control\analysis\js_import_graph_engine.py
- project_control\analysis\legacy_detector.py
- project_control\analysis\orphan_detector.py
- project_control\analysis\python_import_graph_detector.py
- project_control\analysis\python_import_graph_engine.py
- project_control\analysis\semantic_detector.py
- project_control\analysis\session_detector.py
- project_control\analysis\tree_renderer.py
- project_control\cli\__init__.py
- project_control\cli\diff_cmd.py
- project_control\cli\duplicate_cmd.py
- project_control\cli\ghost_cmd.py
- project_control\cli\graph_cmd.py
- project_control\cli\scan_cmd.py
- project_control\config\__init__.py
- project_control\config\patterns_loader.py
- project_control\core\__init__.py
- project_control\core\content_store.py
- project_control\core\debug.py
- project_control\core\duplicate_service.py
- project_control\core\embedding_service.py
- project_control\core\ghost.py
- project_control\core\ghost_service.py
- project_control\core\graph_service.py
- project_control\core\import_parser.py
- project_control\core\layer_service.py
- project_control\core\markdown_renderer.py
- project_control\core\scanner.py
- project_control\core\semantic_service.py
- project_control\core\snapshot.py
- project_control\core\snapshot_diff_service.py
- project_control\core\snapshot_service.py
- project_control\core\tmp_unused_test.py
- project_control\core\writers.py
- project_control\embedding\__init__.py
- project_control\pc.py
- project_control\render\__init__.py
- project_control\render\json_renderer.py
- project_control\render\markdown_renderer.py
- project_control\render\tree_renderer.py
- project_control\utils\__init__.py
- project_control\utils\fs_helpers.py

## Tree View

Total import graph orphans: 53

project_control/
├── __init__.py
├── analysis/
│   ├── __init__.py
│   ├── duplicate_detector.py
│   ├── entrypoint_policy.py
│   ├── graph_anomaly.py
│   ├── graph_drift.py
│   ├── graph_exporter.py
│   ├── graph_metrics.py
│   ├── graph_trend.py
│   ├── import_graph_detector.py
│   ├── import_graph_engine.py
│   ├── js_import_graph_engine.py
│   ├── legacy_detector.py
│   ├── orphan_detector.py
│   ├── python_import_graph_detector.py
│   ├── python_import_graph_engine.py
│   ├── semantic_detector.py
│   ├── session_detector.py
│   └── tree_renderer.py
├── cli/
│   ├── __init__.py
│   ├── diff_cmd.py
│   ├── duplicate_cmd.py
│   ├── ghost_cmd.py
│   ├── graph_cmd.py
│   └── scan_cmd.py
├── config/
│   ├── __init__.py
│   └── patterns_loader.py
├── core/
│   ├── __init__.py
│   ├── content_store.py
│   ├── debug.py
│   ├── duplicate_service.py
│   ├── embedding_service.py
│   ├── ghost.py
│   ├── ghost_service.py
│   ├── graph_service.py
│   ├── import_parser.py
│   ├── layer_service.py
│   ├── markdown_renderer.py
│   ├── scanner.py
│   ├── semantic_service.py
│   ├── snapshot.py
│   ├── snapshot_diff_service.py
│   ├── snapshot_service.py
│   ├── tmp_unused_test.py
│   └── writers.py
├── embedding/
│   └── __init__.py
├── pc.py
├── render/
│   ├── __init__.py
│   ├── json_renderer.py
│   ├── markdown_renderer.py
│   └── tree_renderer.py
└── utils/
    ├── __init__.py
    └── fs_helpers.py