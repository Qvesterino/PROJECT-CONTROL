# PROJECT CONTROL — FUNCTIONAL ARCHITECTURE AUDIT

**Date:** 2025-02-24  
**Type:** Structural Functional Audit (No code style, no lint, no refactor)  
**Scope:** Complete system architecture before UX refactor

---

## EXECUTIVE SUMMARY

PROJECT CONTROL is a dual-mode code analysis system with two distinct graph building mechanisms operating in parallel:

1. **Legacy Ghost Graph** (`--deep`): Python/JS import graph engines built directly from snapshot content
2. **New Graph Builder** (`graph build`): Extractor-based graph system with edge attributes and metrics

These systems share the same snapshot foundation but produce incompatible graph structures, creating architectural redundancy.

---

## PHASE 1 — ENTRY POINT INVENTORY

### CLI Commands (10 total)

| Command | Description | Internal Functions | Snapshot Rebuild? | Graph Rebuild? | Uses Graph? | Heavy FS? | Ripgrep? |
|---------|-------------|---------------------|-------------------|----------------|------------|-----------|----------|
| **init** | Creates .project-control dir, patterns.yaml, status.yaml | ensure_control_dirs(), yaml.dump() | No | No | No | Light (dir creation) | No |
| **scan** | Walks project, hashes files, stores blobs in .project-control/content/ | scan_project() → os.walk() + sha256 + write bytes | Yes (creates new) | No | No | Heavy (full FS walk + read all files) | No |
| **checklist** | Generates markdown checklist from snapshot files | _load_existing_snapshot(), write text | No | No | No | Light (read snapshot) | No |
| **find [symbol]** | Searches project using ripgrep, saves results | run_rg() → subprocess rg | No | No | No | Light (subprocess) | Yes |
| **ghost** | Runs all detectors (orphan, legacy, session, duplicate, semantic); optionally deep import graph analysis | run_ghost() → GhostWorkflow → GhostUseCase → analyze_ghost() → detectors + detect_graph_orphans() | No | Yes (if --deep) | No (if --deep) | Medium (read files via ContentStore) | Yes (orphan detector) |
| **writers** | Analyzes code for writer patterns (scale, emissive, opacity, position) | run_writers_analysis() | No | No | No | Medium | No |
| **graph build** | Builds extractor-based graph with edge attributes | GraphBuilder.build() → extractor_registry → extractors → SpecifierResolver → compute_metrics() | No | Yes | No | Medium (read files via ContentStore) | No |
| **graph report** | Regenerates artifacts (same as build) | graph_build() | No | Yes | No | Medium (read files via ContentStore) | No |
| **graph trace [target]** | Traces paths to/from a node; uses ripgrep for symbol resolution | _load_or_build_graph() → trace_paths() → _find_symbol_definitions() → run_rg() | No | Yes (if cache invalid) | Yes | Medium | Yes (for symbol resolution) |
| **ui** | Launches web UI | launch_ui() | No | No | No | No | No |

### Ghost Subcommands (via flags)

| Flag | Triggers | Effect |
|------|----------|--------|
| `--deep` | detect_graph_orphans() | Runs PythonImportGraphEngine + JSImportGraphEngine, builds import graph, computes metrics, anomalies, drift (if --compare-snapshot), trend |
| `--stats` | None | Prints counts only, skips markdown generation |
| `--tree-only` | None | Skips flat list in import_graph_orphans.md, writes only tree view |
| `--export-graph` | graph_exporter | Exports DOT and Mermaid formats (only with --deep) |
| `--mode strict/pragmatic` | detect_graph_orphans() | Controls apply_ignore parameter (pragmatic = ignore patterns applied) |
| `--validate-architecture` | validate_architecture() | Runs layer boundary validation before ghost; exits on violation |
| `--compare-snapshot [path]` | detect_graph_orphans() | Loads previous snapshot, compares graphs, computes drift, requires --deep |
| `--debug` | Various | Enables debug output in deep analysis and validation |
| `--max-*` | None | Threshold checks for severity counts (high, medium, low, info); causes exit on violation |

---

## PHASE 2 — SNAPSHOT & GRAPH CONTRACT

### Snapshot Lifecycle

```
┌─────────────────────────────────────────────────────────────────┐
│                        SNAPSHOT LIFECYCLE                       │
└─────────────────────────────────────────────────────────────────┘

CREATION:
  pc scan → scan_project() → os.walk() all files
    ↓
    For each file:
      - Read bytes
      - Compute sha256 hash
      - Write blob to .project-control/content/{sha256}.blob
      - Store metadata (path, size, modified, sha256) in files list
    ↓
    Compute snapshot_id = sha256(concatenated path+sha256 strings)
    ↓
    Write .project-control/snapshot.json with metadata + files list

READERS:
  1. load_snapshot() - All commands requiring snapshot
  2. ContentStore - Wraps snapshot for filesystem-independent content access
  3. GraphBuilder - Uses snapshot to collect nodes
  4. All detectors - Receive snapshot as parameter

INVALIDATION:
  - Manual: Run `pc scan` again
  - No automatic invalidation mechanism
  - snapshot.json not checked against actual files on subsequent runs

STORAGE:
  - .project-control/snapshot.json (metadata)
  - .project-control/content/{sha256}.blob (deduplicated file contents)
```

### Graph Lifecycle (Dual System)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GRAPH SYSTEM 1: LEGACY GHOST (--deep)       │
└─────────────────────────────────────────────────────────────────┘

CREATION:
  ghost --deep → GhostWorkflow → GhostUseCase → analyze_ghost()
    ↓
    detect_graph_orphans()
      ↓
      PythonImportGraphEngine.build_graph() OR
      JSImportGraphEngine.build_graph()
        ↓
        For each .py or .js file:
          - ContentStore.get_text(path)
          - Parse imports (AST for Python, regex for JS)
          - Build adjacency dict: {module: set(neighbors)}
        ↓
        DFS from entrypoints → find unreachable modules
        ↓
        Return orphans + graph + metrics + anomalies

OUTPUT:
  - analysis_result["graph"] = {module: set(neighbors)} (dict of sets)
  - analysis_result["metrics"] = {node_count, edge_count, density, is_dag, ...}
  - analysis_result["anomalies"] = {cycle_groups, god_modules, dead_clusters, isolated_nodes, smell_score}
  - Written to: import_graph_orphans.md (markdown report)

CACHING:
  - NO CACHING
  - Rebuilds entire graph every time --deep is used
  - Does NOT check snapshot.json for changes

---

┌─────────────────────────────────────────────────────────────────┐
│                    GRAPH SYSTEM 2: NEW BUILDER                   │
└─────────────────────────────────────────────────────────────────┘

CREATION:
  graph build → GraphBuilder.build()
    ↓
    _collect_nodes() from snapshot
      - Apply include/exclude globs
      - Filter by extensions
      - Assign IDs (1..N)
    ↓
    _collect_edges()
      - For each node:
        - ContentStore.get_text(path)
        - Extractor.extract() (AST for Python, regex for JS)
        - SpecifierResolver.resolve() or PythonResolver.resolve()
        - Create edge with attributes (fromId, toId, specifier, kind, line, lineText, isExternal, isDynamic, resolvedPath)
    ↓
    _resolve_entrypoints() (zero fan-in if none configured)
    ↓
    compute_metrics(graph) → Tarjan SCC, component DAG, depth map
    ↓
    write_artifacts()

OUTPUT:
  - .project-control/out/graph.snapshot.json = {meta, nodes, edges, entrypoints}
  - .project-control/out/graph.metrics.json = {totals, externals, fanIn, fanOut, depth, cycles, orphanCandidates}
  - .project-control/out/graph.report.md = Human-readable report

CACHING:
  YES - In graph_trace():
    - Reads existing graph.snapshot.json
    - Compares meta.snapshotHash with compute_snapshot_hash(current snapshot)
    - Compares meta.configHash with hash_config(current config)
    - Rebuilds only if either hash mismatched

CACHE INVALIDATION:
  - snapshot.json changes (files added/removed/modified)
  - graph config changes
  - Manual deletion of .project-control/out/graph.snapshot.json

---

KEY DIFFERENCES:

GHOST GRAPH (--deep):
  - Simple adjacency dict: {module: set(neighbors)}
  - Module-based (not file paths for Python)
  - No edge attributes
  - No caching
  - Separate engines (PythonImportGraphEngine, JSImportGraphEngine)
  - Computes anomalies via GraphAnomalyAnalyzer
  - Computes drift via compare_snapshots()
  - Computes trend via GraphTrendAnalyzer

NEW BUILDER GRAPH:
  - Rich edge objects with attributes
  - File path-based (nodes = files)
  - Edge attributes: specifier, kind, line, lineText, isExternal, isDynamic, resolvedPath
  - Hash-based caching
  - Extractor registry pattern
  - Computes metrics via compute_metrics() (Tarjan SCC, component DAG)
  - No anomalies/drift/trend built-in
```

### Snapshot Hash Comparison

```
compute_snapshot_hash(snapshot):
  Concatenates: for each file in sorted order:
    f"{path}{sha256}"
  Returns: sha256(concatenated string)

Used in:
  1. GraphBuilder.build() → meta.snapshotHash (written to graph.snapshot.json)
  2. graph_trace._load_or_build_graph() → checks if cached graph valid

Comparison:
  if cached_graph.meta.snapshotHash == compute_snapshot_hash(current_snapshot):
    → Use cached graph
  else:
    → Rebuild graph
```

---

## PHASE 3 — PERFORMANCE HOTSPOT DETECTION

### Hotspot 1: File Reading During Scan

**File:** `project_control/core/scanner.py`  
**Function:** `scan_project()`  
**Why expensive:** Walks entire project tree, reads EVERY file, computes SHA256, writes blobs to disk  
**Triggered:** 1 time per `pc scan`  
**Estimate:** O(N) where N = total files; dominated by disk I/O

**File:** `project_control/core/content_store.py`  
**Function:** `ContentStore.get_text()`  
**Why expensive:** Called repeatedly during graph build for each node; reads from blob files  
**Triggered:** 1 time per node per graph build  
**Estimate:** O(N) per graph build

### Hotspot 2: Ghost Orphan Detector

**File:** `project_control/analysis/orphan_detector.py`  
**Function:** `detect_orphans()` / `analyze()`  
**Why expensive:** For each code file, generates 3 regex patterns, calls run_rg() 3 times  
**Triggered:** 1 time per `pc ghost` (always runs, even without --deep)  
**Estimate:** O(N) ripgrep calls where N = number of code files

```python
# For EACH file:
patterns_to_check = _reference_patterns(name_without_ext)  # 3 patterns
if any(run_rg(p).strip() for p in patterns_to_check):  # 3 ripgrep calls
    continue
```

### Hotspot 3: Deep Import Graph Build (Ghost --deep)

**File:** `project_control/analysis/import_graph_detector.py`  
**Function:** `detect_graph_orphans()`  
**Why expensive:** Builds entire import graph from scratch for BOTH Python AND JS engines, NO CACHING  
**Triggered:** 1 time per `pc ghost --deep`  
**Estimate:** O(N + E) where N = files, E = edges

**File:** `project_control/analysis/python_import_graph_engine.py`  
**Function:** `PythonImportGraphEngine.build_graph()`  
**Why expensive:** AST parsing of every .py file, DFS traversal of entire graph  
**Triggered:** 1 time per `pc ghost --deep`  
**Estimate:** O(N * avg_file_size + E)

**File:** `project_control/analysis/js_import_graph_engine.py`  
**Function:** `JSImportGraphEngine.build_graph()`  
**Why expensive:** Regex parsing of every .js/.ts file, DFS traversal of entire graph  
**Triggered:** 1 time per `pc ghost --deep`  
**Estimate:** O(N * avg_file_size + E)

### Hotspot 4: New Graph Builder

**File:** `project_control/graph/builder.py`  
**Function:** `GraphBuilder._collect_edges()`  
**Why expensive:** For each node, reads file content, extracts imports, resolves specifiers  
**Triggered:** 1 time per graph build (unless cached)  
**Estimate:** O(N * avg_file_size + E)

**File:** `project_control/graph/metrics.py`  
**Function:** `compute_metrics()`  
**Why expensive:** Tarjan SCC algorithm O(N + E), component DAG construction, longest path  
**Triggered:** 1 time per graph build  
**Estimate:** O(N + E)

### Hotspot 5: Graph Trace Symbol Resolution

**File:** `project_control/cli/graph_cmd.py`  
**Function:** `_find_symbol_definitions()`  
**Why expensive:** Calls run_rg() and parses output for symbol resolution  
**Triggered:** 1 time per `pc graph trace` when target is a symbol (not a path)  
**Estimate:** O(1) ripgrep call (limited to 3 results)

### Hotspot 6: Nested Rebuild Cycles

**CRITICAL ISSUE:**

`graph report` → calls `graph_build()` unconditionally:
```python
def graph_report(project_root: Path, config_path: Optional[Path]) -> int:
    # Report regenerates artifacts to remain deterministic
    return graph_build(project_root, config_path)  # ALWAYS REBUILDS
```

This means `pc graph report` ALWAYS rebuilds the graph, ignoring the cache that `graph trace` uses.

**Estimate:** Full graph rebuild O(N * avg_file_size + E) every time report is run.

### Hotspot 7: Repeated Ripgrep Calls

**File:** `project_control/analysis/orphan_detector.py`  
**Function:** `detect_orphans()`  
**Why expensive:** 3 ripgrep subprocess calls per code file  
**Triggered:** Every `pc ghost` (even without --deep)  
**Estimate:** 3 * N calls where N = number of code files

**Optimization opportunity:** Single ripgrep call with multiple patterns, or build index.

---

## PHASE 4 — FEATURE CLASSIFICATION

### BUILD

**Snapshot Build:**
- `pc scan` → scan_project() → snapshot.json + content blobs

**Graph Build (New System):**
- `pc graph build` → GraphBuilder.build() → graph.snapshot.json + graph.metrics.json + graph.report.md
- `pc graph report` → graph_build() (rebuilds, ignores cache)
- `pc graph trace` → _load_or_build_graph() (checks cache, may rebuild)

**Graph Build (Legacy System):**
- `pc ghost --deep` → detect_graph_orphans() → PythonImportGraphEngine.build_graph() + JSImportGraphEngine.build_graph() → in-memory graph (no persistence)

### ANALYZE

**Ghost Detectors (always run):**
- `pc ghost` → analyze_ghost() runs all detectors:
  - orphan_detector: Find unused code via ripgrep
  - legacy_detector: Find legacy files by pattern
  - session_detector: Find files with "session" in name
  - duplicate_detector: Find files with same basename
  - semantic_detector: (implementation not reviewed)

**Import Graph Analysis (deep):**
- `pc ghost --deep` → detect_graph_orphans():
  - Python import graph via AST
  - JS/TS import graph via regex
  - Compute metrics (node_count, edge_count, density, is_dag, largest_component)
  - Compute anomalies (cycle_groups, god_modules, dead_clusters, isolated_nodes, smell_score, smell_level)
  - Compute drift (if --compare-snapshot provided)
  - Compute trend (if history >= 2 entries)

**Layer Boundary Validation:**
- `pc ghost --validate-architecture` → validate_boundaries() → layer boundary checks
- `pc ghost --deep` → validate_boundaries() called before deep analysis

**Architecture Validation:**
- `pc ghost --validate-architecture` → validate_architecture() → self-architecture validation (different from boundary validation)

### EXPLORE

**Graph Report:**
- `pc graph report` → Generates markdown report from metrics (top fan-in/out, deepest files, cycles, orphans)

**Graph Trace:**
- `pc graph trace [target]` → trace_paths():
  - Inbound paths (roots → target)
  - Outbound paths (target → leaves)
  - Supports limits (max-depth, max-paths)
  - Line-level context (--line flag)

**Symbol Search:**
- `pc find [symbol]` → run_rg() → saves results to markdown

**Checklist:**
- `pc checklist` → Generates checklist from snapshot files

### MAINTENANCE

**Snapshot Comparison:**
- `pc ghost --deep --compare-snapshot [path]` → compare_snapshots() → node/edge/entrypoint drift, metric deltas, severity classification

**Graph Export:**
- `pc ghost --deep --export-graph` → graph_exporter.export_dot() + export_mermaid()

**Configuration:**
- `pc init` → Creates patterns.yaml with defaults
- Load patterns from .project-control/patterns.yaml
- Load graph config from .project-control/graph_config.yaml

**Drift History:**
- DriftHistoryRepository persists drift data to .project-control/drift_history.json
- GraphTrendAnalyzer computes stability trends from history

### INTERNAL / LEGACY

**Unused/Duplicate Logic:**
- `project_control/core/tmp_unused_test.py` - File name indicates unused
- Duplicate graph building systems (Ghost vs New Builder)
- `validate_architecture()` and `validate_boundaries()` appear to do similar layer validation

**Embedded Services (Not Used by CLI):**
- `project_control/core/embedding_service.py` - No CLI command references this
- `project_control/usecases/ghost_usecase.py` - Used internally but not exposed
- `project_control/persistence/` - Drift history storage, only used internally

**Potential Dead Code:**
- `project_control/analysis/semantic_detector.py` - Exists but not reviewed
- `project_control/analysis/entrypoint_policy.py` - Used by import graph detector
- `project_control/analysis/tree_renderer.py` - Used for tree view in deep report

---

## PHASE 5 — REDUNDANCY & DRIFT

### Duplicate Logic

**1. Dual Graph Building Systems**

**Ghost Import Graph (--deep):**
- Location: `project_control/analysis/python_import_graph_engine.py`, `js_import_graph_engine.py`
- Structure: `{module: set(neighbors)}` (dict of sets)
- Output: In-memory only, not persisted
- Entry detection: EntrypointPolicy class
- No caching
- No edge attributes
- Module-based (Python) vs file-based (JS)

**New Graph Builder:**
- Location: `project_control/graph/builder.py`
- Structure: Rich objects with `meta`, `nodes`, `edges`, `entrypoints`
- Output: Persisted to `graph.snapshot.json`
- Entry detection: Zero fan-in or configured entrypoints
- Hash-based caching
- Rich edge attributes (specifier, kind, line, lineText, isExternal, isDynamic, resolvedPath)
- File-based for both Python and JS

**Redundancy:** Both systems parse Python/JS files and build import graphs, but produce incompatible structures.

**2. Metrics Computation**

**Ghost System:**
- Location: `project_control/analysis/graph_metrics.py` (GraphMetrics class)
- Metrics: node_count, edge_count, reachable_count, unreachable_count, density, is_dag, largest_component_size

**New Builder System:**
- Location: `project_control/graph/metrics.py` (compute_metrics function)
- Metrics: totals (nodeCount, edgeCount, externalEdgeCount), externals, fanIn, fanOut, depth, cycles, orphanCandidates

**Redundancy:** Both compute graph metrics, but different metric sets and formats.

**3. Cycle Detection**

**Ghost System:**
- Location: `project_control/analysis/graph_anomaly.py` (GraphAnomalyAnalyzer)
- Output: cycle_groups in anomalies dict

**New Builder System:**
- Location: `project_control/graph/metrics.py` (Tarjan SCC in compute_metrics)
- Output: cycles in metrics dict

**Redundancy:** Both detect cycles, but Ghost aggregates into anomaly metrics while New Builder returns raw cycles.

### Outdated Flags

**1. `--tree-only` flag**

Purpose: Write only tree view to import_graph_orphans.md, skip flat list

Status: Still functional, but the tree view is appended to the file AFTER the flat list header, making the flag's behavior unclear:

```python
if args.deep:
    graph_report_path = exports_dir / "import_graph_orphans.md"
    # ... writes flat list if not tree_only ...
    if not args.tree_only:
        for path in graph_orphans:
            graph_lines.append(f"- {path}")
    graph_report_path.write_text("\n".join(graph_lines).rstrip() + "\n", encoding="utf-8")
    
    if graph_orphans:
        tree_output = render_tree(graph_orphans)
        with graph_report_path.open("a", encoding="utf-8") as f:
            f.write("\n## Tree View\n\n")
            # ... appends tree view ...
```

Issue: If `--tree-only` is set, the file starts with header and no flat list, then tree view is appended. The behavior works but is confusing.

**2. `pc graph report` unconditional rebuild**

Comment says "to remain deterministic" but no explanation of what determinism is being preserved vs cache.

```python
def graph_report(project_root: Path, config_path: Optional[Path]) -> int:
    # Report regenerates artifacts to remain deterministic
    return graph_build(project_root, config_path)
```

### Contract Mismatches

**1. Metrics Key Mismatch**

Ghost system expects:
```python
metrics.get("node_count", 0)
metrics.get("edge_count", 0)
metrics.get("density", 0)
metrics.get("smell_score", 0)
```

New Builder system provides:
```python
metrics["totals"]["nodeCount"]  # NOT node_count
metrics["totals"]["edgeCount"]  # NOT edge_count
metrics["totals"]["externalEdgeCount"]
# NO density key
# NO smell_score key
```

**Impact:** Graph drift comparison (`compare_snapshots()`) expects Ghost metrics format. If New Builder metrics are used, keys won't match, causing errors or incorrect comparisons.

**2. Graph Structure Mismatch**

Ghost system expects:
```python
{
    "node_count": int,
    "edge_count": int,
    "density": float,
    "is_dag": bool,
    "largest_component_size": int
}
```

New Builder provides:
```python
{
    "totals": {
        "nodeCount": int,
        "edgeCount": int,
        "externalEdgeCount": int
    },
    "externals": {...},
    "fanIn": {...},
    "fanOut": {...},
    "depth": {...},
    "cycles": [...],
    "orphanCandidates": [...]
}
```

**Impact:** Incompatible structures cannot be exchanged between systems.

**3. Anomaly Contract Mismatch**

Ghost system returns:
```python
{
    "cycle_groups": [[path1, path2, ...], ...],
    "god_modules": [path1, path2, ...],
    "dead_clusters": [path1, path2, ...],
    "isolated_nodes": [path1, path2, ...],
    "smell_score": float,
    "smell_level": "HIGH" | "MEDIUM" | "LOW"
}
```

New Builder provides (in metrics):
```python
{
    "cycles": [[path1, path2, ...], ...]  # Different key name
    # NO god_modules
    # NO dead_clusters
    # NO isolated_nodes
    # NO smell_score
    # NO smell_level
}
```

**Impact:** Ghost system's anomaly analysis cannot use New Builder's metrics.

### Dependencies on Outdated Formats

**1. Graph Drift Comparison**

`project_control/analysis/graph_drift.py` function `compare_snapshots()` expects Ghost metrics format:

```python
metric_deltas["nodes"] = new_metrics.get("node_count", 0) - old_metrics.get("node_count", 0)
metric_deltas["edges"] = new_metrics.get("edge_count", 0) - old_metrics.get("edge_count", 0)
metric_deltas["density"] = new_metrics.get("density", 0) - old_metrics.get("density", 0)
metric_deltas["cycle_groups"] = len(new_cycle_groups) - len(old_cycle_groups)
metric_deltas["smell_score"] = round(new_smell - old_smell, 2)
```

This ONLY works with Ghost system metrics. New Builder metrics would cause these to be 0 or missing keys.

**2. Graph Trend Analysis**

`project_control/analysis/graph_trend.py` expects drift format from Ghost system. If drift is computed from New Builder graph, the structure won't match.

**3. UI Result DTO**

`project_control/core/result_dto.py` function `build_ui_result_dto()` expects specific payloads:

```python
graph_payload if deep else None,  # from Ghost system
metrics_payload if deep else None,  # from Ghost system
anomalies_payload if deep else None,  # from Ghost system
drift_payload if deep else None,  # from Ghost system
trend_payload if deep else None,  # from Ghost system
```

This is tightly coupled to Ghost system structure.

---

## PROJECT CONTROL CURRENT STATE SUMMARY

### Architecture Overview

PROJECT CONTROL is a **dual-track code analysis system** with significant architectural redundancy:

1. **Legacy Track (Ghost --deep):** Python/JS import graph engines built directly from snapshot, module-based graphs, in-memory only, no caching, separate anomaly/drift/trend analysis.

2. **Modern Track (Graph Build):** Extractor-based graph system with rich edge attributes, file-based graphs, hash-based caching, metrics computation, no anomaly/drift/trend.

Both tracks share the same snapshot foundation (`.project-control/snapshot.json` + `.project-control/content/*.blob`) but are otherwise completely incompatible.

### Critical Findings

**1. Redundant Graph Systems**
- Two separate import graph builders with incompatible structures
- Both parse Python/JS files
- Both compute metrics (different formats)
- Both detect cycles (different outputs)
- No mechanism to unify or migrate between systems

**2. Performance Issues**
- Ghost --deep builds graph from scratch every time (NO caching)
- Orphan detector calls ripgrep 3 times per code file (3N subprocess calls)
- Graph report unconditionally rebuilds, ignoring cache
- No incremental build capability in either system

**3. Contract Mismatches**
- Ghost metrics use snake_case (node_count, edge_count, density)
- Builder metrics use nested camelCase (totals.nodeCount, totals.edgeCount)
- Graph drift comparison expects Ghost metrics format
- Anomaly analysis expects Ghost anomalies (god_modules, dead_clusters, isolated_nodes, smell_score) which Builder doesn't provide

**4. Inconsistent Caching**
- Ghost --deep: NO caching
- Graph build: Hash-based caching (snapshotHash + configHash)
- Graph trace: Checks cache, may reuse
- Graph report: Ignores cache, always rebuilds

**5. Confusing CLI Semantics**
- `graph report` rebuilds despite comment about "deterministic"
- `--tree-only` behavior unclear (header + no flat list + appended tree)
- `--validate-architecture` vs layer boundary validation (two different validators)

### Feature Completeness

**Implemented:**
- ✅ Snapshot creation and content-addressable storage
- ✅ Ghost detectors (orphan, legacy, session, duplicate, semantic)
- ✅ Python import graph analysis (AST-based)
- ✅ JS/TS import graph analysis (regex-based)
- ✅ Graph building with edge attributes
- ✅ Graph metrics (fan-in/out, depth, cycles)
- ✅ Graph tracing (inbound/outbound paths)
- ✅ Graph drift comparison (Ghost system only)
- ✅ Graph trend analysis (Ghost system only)
- ✅ Layer boundary validation
- ✅ Graph export (DOT, Mermaid)
- ✅ Symbol search via ripgrep
- ✅ Checklist generation

**Missing / Incomplete:**
- ❌ Unified graph system
- ❌ Metrics format standardization
- ❌ Incremental builds
- ❌ Ripgrep optimization (batch patterns)
- ❌ Clear separation between analysis and persistence
- ❌ Migration path from Ghost to Builder

### Technical Debt

**High Priority:**
1. Choose ONE graph system (recommend Builder with anomaly/drift/trend features)
2. Standardize metrics format
3. Implement caching for Ghost --deep
4. Fix graph report to respect cache
5. Consolidate duplicate cycle detection

**Medium Priority:**
1. Optimize orphan detector (batch ripgrep calls)
2. Clarify or remove `--tree-only` flag
3. Consolidate layer validation logic
4. Document determinism requirement for graph report

**Low Priority:**
1. Remove tmp_unused_test.py
2. Review semantic_detector usage
3. Review embedding_service usage

### Data Flow

```
User runs CLI
    ↓
Router.dispatch()
    ↓
┌─────────────────┐     ┌─────────────────┐
│   Command       │     │   Subcommand    │
└────────┬────────┘     └────────┬────────┘
         │                       │
         ↓                       ↓
┌─────────────────────────────────────────┐
│  Commands REQUIRING snapshot          │
│  (all except init, ui)                 │
└────────┬────────────────────────────────┘
         ↓
    load_snapshot()
         ↓
┌─────────────────────────────────────────┐
│  Commands REQUIRING graph             │
│  (ghost --deep, graph build/report)    │
└────────┬────────────────────────────────┘
         ↓
    ┌────┴────┐
    ↓         ↓
GHOST      BUILDER
--deep     build
    ↓         ↓
Python/JS   Extractor
Engines     Registry
    ↓         ↓
In-memory   Persisted
graph       graph
    ↓         ↓
Anomalies   Metrics
Drift       Cycles
Trend       (no drift/
            anomalies)
```

### Filesystem Touch Points

**Reads:**
- `.project-control/snapshot.json` - All commands except init, ui
- `.project-control/content/*.blob` - ContentStore.get_text() for graph builds
- `.project-control/patterns.yaml` - All ghost/analysis commands
- `.project-control/graph_config.yaml` - Graph build/report/trace
- `.project-control/out/graph.snapshot.json` - Graph trace (cache check)
- `.project-control/drift_history.json` - Ghost drift/trend

**Writes:**
- `.project-control/snapshot.json` - `pc scan`
- `.project-control/content/*.blob` - `pc scan`
- `.project-control/exports/*.md` - Ghost reports, checklist, find results
- `.project-control/out/graph.snapshot.json` - `pc graph build`
- `.project-control/out/graph.metrics.json` - `pc graph build`
- `.project-control/out/graph.report.md` - `pc graph build`
- `.project-control/out/graph.trace.txt` - `pc graph trace`

**Heavy Operations:**
1. `pc scan` - Full FS walk + read all files + hash + write blobs
2. `pc ghost --deep` - Read all .py/.js files + parse + build graph (no cache)
3. `pc graph build` - Read all matching files + extract + build graph (cached)
4. `pc ghost` (without --deep) - 3N ripgrep calls for orphan detection

---

## RECOMMENDATIONS FOR UX REFACTOR

### DO NOT Change
- Snapshot creation mechanism (works well, content-addressable is good)
- ContentStore abstraction (clean separation of concerns)
- Graph builder's hash-based caching (excellent design)

### MUST Address Before UX
1. **Choose graph system** - Cannot build UX on top of two incompatible graphs
2. **Standardize metrics format** - UI needs consistent data structure
3. **Fix performance** - Ripgrep N^3 calls and uncached Ghost --deep
4. **Clarify cache semantics** - Graph report ignoring cache is confusing

### UX Implications
- UX should likely be built on top of Graph Builder (more complete features)
- Ghost detectors are independent of graph and can run separately
- Consider progressive loading: show detectors first, then deep graph analysis
- Cache visualization: show when graph is cached vs rebuilt

---

**AUDIT COMPLETE**

This audit identifies the dual-track architecture as the primary structural issue. The Ghost system and Graph Builder are competing implementations of the same concept (import graph analysis) with incompatible contracts. Any UX refactor must first resolve this architectural ambiguity by choosing one system and migrating/standardizing accordingly.