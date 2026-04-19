# Smart Ghost Report

## Summary

- Orphans (HIGH): 31
- Legacy snippets (MEDIUM): 0
- Session files (LOW): 0
- Duplicates (INFO): 0
- Semantic findings (MEDIUM): 61

### Orphans [HIGH]

- project_control\__init__.py
- project_control\analysis\__init__.py
- project_control\analysis\duplicate_detector.py
- project_control\analysis\graph_exporter.py
- project_control\analysis\graph_trend.py
- project_control\analysis\layer_boundary_validator.py
- project_control\analysis\python_import_graph_detector.py
- project_control\analysis\self_architecture_validator.py
- project_control\analysis\session_detector.py
- project_control\analysis\tree_renderer.py
- project_control\cli\__init__.py
- project_control\config\__init__.py
- project_control\core\__init__.py
- project_control\core\drift_history_store.py
- project_control\core\dto.py
- project_control\core\import_parser.py
- project_control\core\result_dto.py
- project_control\core\snapshot_validator.py
- project_control\core\tmp_unused_test.py
- project_control\embedding\__init__.py
- project_control\graph\__init__.py
- project_control\persistence\__init__.py
- project_control\persistence\drift_history_repository.py
- project_control\render\__init__.py
- project_control\usecases\__init__.py
- project_control\usecases\ghost_usecase.py
- project_control\usecases\ghost_workflow.py
- project_control\utils\__init__.py
- tests\__init__.py
- tests\test_extractors_trace.py
- tests\test_graph_core.py


### Legacy snippets [MEDIUM]

_No entries found._


### Semantic Findings [MEDIUM]

**Semantic Orphans** (low similarity to codebase):
- project_control\core\debug.py (similarities: 0.00)
- project_control\core\exit_codes.py (similarities: 0.00)
- project_control\analysis\tree_renderer.py (similarities: 0.00)
- project_control\core\embedding_service.py (similarities: 0.00)
- project_control\analysis\graph_trend.py (similarities: 0.00)
- project_control\core\snapshot_validator.py (similarities: 0.00)
- project_control\core\result_dto.py (similarities: 0.00)
- project_control\utils\fs_helpers.py (similarities: 0.00)
- project_control\core\content_store.py (similarities: 0.00)
- project_control\core\drift_history_store.py (similarities: 0.00)
- project_control\persistence\drift_history_repository.py (similarities: 0.00)
- project_control\graph\resolver.py (similarities: 0.00)
- project_control\config\patterns_loader.py (similarities: 0.00)
- project_control\core\writers.py (similarities: 0.00)
- project_control\core\dto.py (similarities: 0.00)
- project_control\analysis\layer_boundary_validator.py (similarities: 0.00)
- project_control\graph\trace.py (similarities: 0.00)
- project_control\graph\extractors\python_ast.py (similarities: 0.00)
- project_control\core\markdown_renderer.py (similarities: 0.00)
- project_control\analysis\duplicate_detector.py (similarities: 0.00)
- project_control\analysis\semantic_detector.py (similarities: 0.00)
- project_control\graph\extractor.py (similarities: 0.00)
- project_control\graph\extractors\registry.py (similarities: 0.00)
- project_control\cli\router.py (similarities: 0.00)
- project_control\graph\extractors\js_ts.py (similarities: 0.00)
- project_control\ui.py (similarities: 0.00)
- project_control\core\scanner.py (similarities: 0.00)
- project_control\analysis\graph_drift.py (similarities: 0.00)
- project_control\pc.py (similarities: 0.00)
- project_control\analysis\graph_anomaly.py (similarities: 0.00)
- project_control\analysis\self_architecture_validator.py (similarities: 0.00)
- project_control\core\import_parser.py (similarities: 0.00)
- project_control\analysis\graph_exporter.py (similarities: 0.00)
- project_control\core\snapshot.py (similarities: 0.00)
- project_control\core\snapshot_service.py (similarities: 0.00)
- project_control\analysis\session_detector.py (similarities: 0.00)
- project_control\core\ghost_service.py (similarities: 0.00)
- project_control\graph\metrics.py (similarities: 0.00)
- project_control\analysis\graph_metrics.py (similarities: 0.00)
- project_control\analysis\entrypoint_policy.py (similarities: 0.00)
- project_control\cli\graph_cmd.py (similarities: 0.00)
- project_control\analysis\legacy_detector.py (similarities: 0.00)
- project_control\graph\artifacts.py (similarities: 0.00)
- project_control\graph\extractors\base.py (similarities: 0.00)
- tests\test_extractors_trace.py (similarities: 0.00)
- project_control\analysis\python_import_graph_engine.py (similarities: 0.00)
- project_control\usecases\ghost_workflow.py (similarities: 0.00)
- project_control\config\graph_config.py (similarities: 0.00)
- project_control\analysis\orphan_detector.py (similarities: 0.00)
- tests\test_graph_core.py (similarities: 0.00)
- project_control\analysis\python_import_graph_detector.py (similarities: 0.00)
- project_control\core\ghost.py (similarities: 0.00)
- project_control\analysis\js_import_graph_engine.py (similarities: 0.00)
- project_control\analysis\import_graph_detector.py (similarities: 0.00)
- project_control\usecases\ghost_usecase.py (similarities: 0.00)
- project_control\graph\builder.py (similarities: 0.00)
- project_control\graph\__init__.py (similarities: 0.00)
- project_control\analysis\import_graph_engine.py (similarities: 0.00)

**Semantic Duplicates** (high similarity to other files):
- project_control\graph\extractor.py ↔ project_control\graph\extractors\js_ts.py (similarities: 0.93)
- project_control\usecases\ghost_usecase.py ↔ project_control\usecases\ghost_workflow.py (similarities: 0.93)
- project_control\core\drift_history_store.py ↔ project_control\persistence\drift_history_repository.py (similarities: 0.96)

### Session files [LOW]

_No entries found._


### Duplicates [INFO]

_No entries found._
