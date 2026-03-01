**Architecture Map**
- **Entry CLI**: `pc.py` builds argparse tree → `router.dispatch`.
- **Snapshots**: `scan`/`ui scan` → `snapshot_service.create_snapshot` (walk + hash) → saved to `.project-control/snapshot.json`.
- **Graph (new engine)**: `graph build/report/trace`, `ui graph report/trace` → load snapshot → `GraphBuilder` → `graph.artifacts.write_artifacts` writes `.project-control/out/graph.snapshot.json`, metrics, report.
- **Ghost (legacy analyzers)**: `ghost` command → `ghost_service.run_ghost` → `GhostWorkflow`/`GhostUseCase` → `analyze_ghost` with detectors; `deep` builds its own JS+PY import graphs (not the new graph artifacts).
- **UI**: `pc ui` loop; forces a user-chosen mode (JS/TS, Python, Mixed) to flip `GraphConfig.languages` before graph/trace actions.

**Command-to-Engine Dependency Table**
- `init`: creates control dirs, writes default patterns/status. Snapshot rebuild: no. Graph rebuild/use: no. FS heavy: no. Ripgrep: no.
- `scan`: builds & saves snapshot (hash every included file). Snapshot rebuild: yes. Graph rebuild/use: no. FS heavy: yes (walk+hash). Ripgrep: no.
- `checklist`: reads snapshot; writes checklist file. Snapshot rebuild: no. Graph: no. FS: low (read snapshot, write md). Ripgrep: no.
- `find <symbol>`: reads snapshot dirs? (no). Calls `run_rg` subprocess. Snapshot/graph rebuild: no. FS: low. Ripgrep: yes.
- `ghost [--deep ...]`: loads snapshot; runs detectors. Snapshot rebuild: no. Graph rebuild: deep builds in-memory graph every run (separate engine), no artifact reuse. Uses existing graph artifact: no. FS: medium (content reads, duplicate/session scans); deep: high (import graph per file). Ripgrep: no.
- `writers`: runs writers analysis (details elsewhere); reads files; writes report. Snapshot/graph rebuild: no. FS: medium. Ripgrep: no.
- `graph build` / `graph report`: load snapshot → always (re)builds graph+metrics, writes snapshot/metrics/report files (overwrites). Snapshot rebuild: no. Graph rebuild: yes. Uses existing graph: no. FS: high (read content of graph-eligible files). Ripgrep: no.
- `graph trace <target>`: loads snapshot; tries to reuse `.project-control/out/graph.snapshot.json` if `snapshotHash` & `configHash` match, else rebuilds graph. Snapshot rebuild: no. Graph rebuild: conditional. Uses existing graph: yes if fresh. FS: medium-high (may rebuild). Ripgrep: yes (for symbol resolution).
- `ui`: interactive loop. Actions:
  - Change mode: toggles language flags in GraphConfig clone (no FS).
  - Scan: same as `scan`.
  - Ghost / Ghost deep: same as `ghost`.
  - Graph report: same as `graph report` but with mode-adjusted config.
  - Trace: same as `graph trace` with mode-adjusted config.
  Snapshot/graph behaviors mirror underlying calls.

**Snapshot & Graph Contract (Lifecycle)**
- Create snapshot: `create_snapshot` in `snapshot_service` (walk + sha256 blobs) → `save_snapshot` to `.project-control/snapshot.json`; blobs stored under `.project-control/content/<hash>.blob`.
- Read snapshot: `router` commands (`scan` read patterns only; others load snapshot), `graph_cmd`, `ghost_service`, UI status panel.
- Snapshot invalidation: no explicit invalidation; only recreated by `scan` overwriting `snapshot.json`.
- Graph rebuild trigger: `graph_build/report` always; `graph_trace` (and UI equivalents) rebuilds when missing or when either config hash or `snapshotHash` differs from current snapshot (`compute_snapshot_hash` compares paths+sha256). Rebuild overwrites `.project-control/out/graph.snapshot.json`, `.project-control/out/graph.metrics.json`, `.project-control/out/graph.report.md`.
- Ghost deep graph: built in-memory each run via `detect_graph_orphans` (JS+PY engines) independent of `.project-control/out/graph.snapshot.json`; does not write snapshotHash or reuse artifacts.
- `snapshotHash` comparison to `graph.meta.snapshotHash`: used in `graph_trace` reuse logic and UI status panel. Stored in graph meta during build.
- Multiple snapshot mechanisms: single snapshot system; ghost deep uses the same snapshot data and content blobs but its own graph computation.

**Performance Hotspots**
- `snapshot_service.create_snapshot`: os.walk all files, sha256 hash each; writes blobs (O(number_of_files), heavy on large repos) — triggered every `scan` (UI or CLI).
- `GraphBuilder._collect_edges`: reads content of every graph-eligible file from blob store; regex/AST per file; resolves imports — triggered on every graph build or trace when cache stale/missing.
- `graph_cmd._load_or_build_graph`: potential redundant rebuild if graph file missing or hash mismatch; single rebuild per trace invocation when stale.
- `ghost_service.run_ghost` (deep): `detect_graph_orphans` runs two engines (Python, JS) over entire snapshot, building graphs anew; occurs every `ghost --deep` run regardless of existing graph artifacts.
- `run_rg` subprocess: invoked by `find` and by `graph_trace` symbol resolution; cost proportional to repo size, called once per command.
- Duplicate content reads: Ghost detectors (`duplicate_detector`, `legacy_detector`, etc.) iterate snapshot files via `ContentStore`; combined with graph builds can double-read blobs in the same session when commands run sequentially.

**Feature Classification**
- **BUILD**: `scan` (snapshot); `graph build/report` (+ UI graph report/trace rebuild path).
- **ANALYZE**: `ghost` (pragmatic/strict modes), `ghost --deep` (import graph based orphan analysis), legacy detectors (orphans/legacy/session/duplicates/semantic).
- **EXPLORE**: `graph report` (renders summary), `graph trace` (path enumeration with line context), metrics fan-in/out/cycles inside graph metrics.
- **MAINTENANCE**: `init`, `checklist`, `writers`, `find`, UI mode toggle, config loading (`patterns_loader`, `graph_config`), snapshotHash/configHash freshness checks.
- **INTERNAL / LEGACY**: Ghost deep graph uses separate engines (`JSImportGraphEngine`, `PythonImportGraphEngine`) parallel to new graph builder; anomalies/trend/drift handling inside ghost workflow distinct from new graph metrics; semantic_detector placeholder; legacy “strict/pragmatic” modes apply only to ghost ignore behavior, not new graph.

**Redundancy & Drift**
- Two graph systems: new `graph.builder/metrics/trace` vs ghost deep’s `detect_graph_orphans` engines and metrics; no shared artifacts → duplicated import parsing and metrics logic.
- Graph reuse mismatch: ghost deep ignores `.project-control/out/graph.snapshot.json`; always rebuilds its own graph, leading to duplicated work and potentially divergent metrics.
- Flags potentially outdated: `--validate-architecture` only gates `validate_architecture` pre-run but bypasses main workflow; `--export-graph` only meaningful with ghost deep and uses ghost graph, not new graph artifacts.
- Metric shape differences: ghost metrics (`GraphMetrics`) vs new graph metrics (`graph/metrics.py`) — consumers relying on one won’t match the other; ghost usecase normalizes graph to include nodes/edges counts when missing, indicating format drift.
- Mode handling: new UI mode flips `GraphConfig.languages`; ghost (legacy) engines still run both JS and Python every time, independent of UI mode — behavioral drift between UI-stated mode and ghost deep internals.

**Command → Engine Dependency (summary)**
- init → file writes (patterns/status)
- scan → snapshot_service.create_snapshot
- checklist → load_snapshot, write checklist
- find → run_rg
- ghost → GhostWorkflow (detectors; deep triggers detect_graph_orphans)
- writers → run_writers_analysis, render_writer_report
- graph build/report → GraphBuilder + graph.metrics + write_artifacts
- graph trace → maybe GraphBuilder (if stale) + trace_paths + run_rg for symbol
- ui → wraps above; mode only affects graph config in graph report/trace, not ghost

**Performance Risks**
- Full repo hash on every `scan`.
- Rebuilding graph on each `graph build/report` even if unchanged.
- Ghost deep recomputes import graph every run; duplicate with graph builder work.
- ContentStore blob reads repeated across commands in same session; no caching beyond OS FS cache.
- `run_rg` scan per trace and per find; large repos may incur noticeable cost.

**Refactor Candidates (priority order)**
1) Unify graph computation between ghost deep and new graph builder (eliminate dual engines and duplicate metrics).
2) Introduce graph reuse in ghost deep or allow it to consume `.project-control/out/graph.snapshot.json`.
3) Avoid unconditional graph rebuild in `graph_report` (reuse freshness check like trace).
4) Optional snapshot reuse across `scan` runs or incremental hashing to cut repeated full hashing.
5) Align UI mode with ghost analyzers (currently only affects new graph paths).

PROJECT CONTROL CURRENT STATE SUMMARY