**New CLI Router Structure (proposed files/responsibilities)**
- `pc.py`: single entry; if no args → launch interactive menu; otherwise delegates to router for direct commands (kept for backward compatibility minus deep flags).
- `project_control/cli/router.py`: thin routing only; no business logic. Calls service facades.
- `project_control/cli/menu.py` (new): renders menu, loops, calls services.
- `project_control/services/scan_service.py`: wraps snapshot_service.create_snapshot/save_snapshot.
- `project_control/services/graph_service.py`: wraps ensure_graph/GraphBuilder + metrics/report access; no duplication of build logic.
- `project_control/services/trace_service.py`: wraps graph_trace with config freshness guard.
- `project_control/services/ghost_service.py`: runs detectors (orphan/legacy/session/duplicate/semantic) without deep graph; consumes snapshot only.
- `project_control/services/writers_service.py`: wraps writers analysis.

**Command Flow Diagram (text)**
- `pc` (no args) → `menu.run()`:
  - Scan project → scan_service.scan()
  - Build graph → graph_service.build_or_reuse()
  - Show graph report → graph_service.report() (reuse graph; no rebuild if fresh)
  - Trace node → trace_service.trace(target, direction, limits)
  - Run ghost detectors → ghost_service.run(snapshot-only)
  - Writers analysis → writers_service.run()
  - Exit → quit loop
- `pc scan|graph build|graph report|graph trace|ghost|writers` (direct) → router → corresponding service (same implementations as menu).

**Removal Plan for Legacy Ghost Deep Engine**
- Delete or fully stop using:
  - `project_control/analysis/import_graph_detector.py`
  - `project_control/analysis/js_import_graph_engine.py`
  - `project_control/analysis/python_import_graph_engine.py`
  - Any references to `detect_graph_orphans`, `GraphMetrics` (legacy), `GraphAnomalyAnalyzer`, `graph_trend`, `graph_drift`, `compare_snapshots`, `GraphTrendAnalyzer`.
- Remove `--deep`, `--compare-snapshot`, `--export-graph`, `--tree-only`, `--debug`, `--mode` (strict/pragmatic) flags from CLI parsing and router handling.
- Ghost now only runs shallow detectors: orphan_detector, legacy_detector, session_detector, duplicate_detector, semantic_detector.
- Ensure no code path imports the deleted modules; add sentinel comments if kept temporarily.

**Graph Engine Exclusivity**
- GraphBuilder + ensure_graph is the single source of graph artifacts.
- `graph.metrics.json` is the sole metrics source; ghost reads from it if/when needed (but not rebuilding).
- Reuse rule: if `.project-control/out/graph.snapshot.json` exists and meta.snapshotHash/configHash match current snapshot/config → no rebuild; else rebuild via GraphBuilder once.

**Exact Code Modifications Needed**
- `pc.py`: when no command → start menu; strip ghost deep flags from argparse; keep backward-compatible shallow `ghost`.
- `project_control/cli/router.py`: remove handling of deep flags; route menu invocation; route ghost to shallow service; route graph commands to graph_service (which uses ensure_graph).
- Add `project_control/cli/menu.py`: prints required menu, calls services.
- Add `project_control/services/{scan,graph,trace,ghost,writers}_service.py`:
  - `graph_service.build_or_reuse(project_root, config_path=None)` → ensure_graph.
  - `graph_service.report(...)` → ensure_graph then print/report paths (no rebuild if fresh).
  - `trace_service.trace(...)` → ensure_graph for freshness then call graph_trace (no extra build logic).
  - `ghost_service.run(...)` → load snapshot, run detectors only; no deep/graph work.
- `project_control/core/ghost_service.py`, `usecases/ghost_workflow.py`, `usecases/ghost_usecase.py`, `core/ghost.py`: remove parameters/logic for deep graph, compare_snapshot, anomalies, drift, trend; strip force_graph and graph_config; ensure analyze_ghost never touches graph/metrics.
- Delete/dep-ref legacy analysis modules listed above; clean imports elsewhere.
- Tests: remove or rewrite any deep ghost tests; add menu routing test and ensure_graph reuse test.

**Graph Metrics Consumption**
- Ghost and menu reporting must use:
  - `totals.nodeCount`, `totals.edgeCount`
  - `cycles` (list) already in metrics
  - `orphanCandidates` (reason == "unreachable")
  - `fanIn`, `fanOut`, `depth` if displayed
- No expectation of `node_count` or legacy keys.

**Migration Notes (breaking changes)**
- `pc ghost --deep` and related flags are removed; shallow ghost only.
- Legacy graph drift/anomaly exports removed; consumers of those files must switch to new graph metrics.
- Any tooling depending on `import_graph_orphans.md`, DOT/Mermaid exports, or trend/drift data will break.
- Config modes (strict/pragmatic) no longer affect ghost; ignores controlled only by snapshot/patterns if retained.
- Ensure users run `pc scan` then `pc graph build` once; subsequent operations reuse artifacts if hashes match.

**Updated Command Flow (concise)**
- Menu-first UX; direct commands still available but deep options gone.
- Single graph engine path via ensure_graph; no other graph builders in codebase.

**What to remove/mark deprecated**
- All deep/graph drift/anomaly/trend code in ghost stack.
- Deep-related CLI flags and help text.
- Legacy import graph engine modules and their tests/fixtures.