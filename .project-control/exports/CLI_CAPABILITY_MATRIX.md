# PROJECT CONTROL - CLI Capability Matrix

## Static Audit Report

**Date:** 2026-02-17  
**Scope:** `project_control/pc.py`, `project_control/cli/*`, `project_control/core/ghost.py`, `project_control/core/ghost_service.py`

---

## Executive Summary

PROJECT_CONTROL provides **6 CLI commands** with **10 flags** across the system. The analysis pipeline includes **6 layers** (Import Graph, Metrics, Anomaly, Drift, Trend, Export). Three commands (`diff`, `duplicate`, `graph`) have stub implementations in the CLI directory but are not registered in the main CLI.

---

## CLI Command Inventory

| Command | Description | Implementation Location |
|---------|-------------|------------------------|
| `init` | Initialize project control directories and config | `pc.py::cmd_init()` |
| `scan` | Scan project files and create snapshot | `pc.py::cmd_scan()` |
| `checklist` | Generate project file checklist | `pc.py::cmd_checklist()` |
| `find <symbol>` | Search for symbol usage across project | `pc.py::cmd_find()` |
| `ghost` | Main ghost detection and analysis | `pc.py::cmd_ghost()` |
| `writers` | Analyze Three.js writer usage | `pc.py::cmd_writers()` |
| `diff` *(STUB)* | Not implemented | `cli/diff_cmd.py` (empty) |
| `duplicate` *(STUB)* | Not implemented | `cli/duplicate_cmd.py` (empty) |
| `graph` *(STUB)* | Not implemented | `cli/graph_cmd.py` (empty) |

---

## Detailed Command Analysis

### 1. `pc init`

**Purpose:** Initialize PROJECT_CONTROL directory structure and configuration files

**Flags:** None

**Layers Triggered:** None (filesystem operations only)

**Output Files:**
- `.project-control/patterns.yaml` (created if not exists)
- `.project-control/status.yaml` (created if not exists)

**Deep Mode Required:** No

---

### 2. `pc scan`

**Purpose:** Scan project directory and create file snapshot

**Flags:** None

**Layers Triggered:** None (filesystem scanning only)

**Output Files:**
- `.project-control/snapshot.json`

**Deep Mode Required:** No

---

### 3. `pc checklist`

**Purpose:** Generate markdown checklist of all project files

**Flags:** None

**Layers Triggered:** None (snapshot-based reporting only)

**Output Files:**
- `.project-control/exports/checklist.md`

**Deep Mode Required:** No

---

### 4. `pc find <symbol>`

**Purpose:** Search for symbol usage using ripgrep

**Arguments:**
- `symbol` (required) - Symbol to search for

**Flags:** None

**Layers Triggered:** None (external grep tool only)

**Output Files:**
- `.project-control/exports/find_<symbol>.md`

**Deep Mode Required:** No

---

### 5. `pc ghost`

**Purpose:** Execute comprehensive ghost detection and architectural analysis

**Flags:**

| Flag | Type | Default | Description | Dependencies |
|------|------|---------|-------------|--------------|
| `--deep` | boolean | False | Run deep import graph analysis (slow) | Triggers all graph-related layers |
| `--stats` | boolean | False | Print statistics without generating report | Overrides report generation |
| `--tree-only` | boolean | False | Write only tree view to graph report | Requires `--deep` |
| `--export-graph` | boolean | False | Export graph in DOT and Mermaid formats | Requires `--deep` |
| `--mode` | enum | pragmatic | Detection mode (strict/pragmatic) | Affects import graph ignore patterns |
| `--max-high` | integer | -1 | Fail if HIGH severity count exceeds this | -1 = disabled |
| `--max-medium` | integer | -1 | Fail if MEDIUM severity count exceeds this | -1 = disabled |
| `--max-low` | integer | -1 | Fail if LOW severity count exceeds this | -1 = disabled |
| `--max-info` | integer | -1 | Fail if INFO severity count exceeds this | -1 = disabled |
| `--compare-snapshot` | path | None | Path to previous snapshot for drift comparison | Requires `--deep` |

**Layers Triggered:**

| Layer | Always? | Trigger Condition | Module |
|-------|---------|-------------------|--------|
| Orphan Detector | ✅ Yes | Always | `orphan_detector` |
| Legacy Detector | ✅ Yes | Always | `legacy_detector` |
| Session Detector | ✅ Yes | Always | `session_detector` |
| Duplicate Detector | ✅ Yes | Always | `duplicate_detector` |
| Semantic Detector | ✅ Yes | Always | `semantic_detector` |
| Import Graph | ❌ No | `--deep` flag | `import_graph_detector` |
| Metrics | ❌ No | `--deep` flag | `graph_metrics` |
| Anomaly | ❌ No | `--deep` flag | `graph_anomaly` |
| Drift | ❌ No | `--deep` + `--compare-snapshot` | `graph_drift` |
| Trend | ❌ No | `--deep` + `--compare-snapshot` + history ≥ 2 | `graph_trend` |
| Export (DOT/Mermaid) | ❌ No | `--deep` + `--export-graph` | `graph_exporter` |

**Output Files:**

| File | Created When | Content |
|------|--------------|---------|
| `.project-control/exports/ghost_candidates.md` | Always (unless `--stats`) | Main ghost detection report |
| `.project-control/exports/import_graph_orphans.md` | `--deep` flag | Import graph orphans report |
| `.project-control/exports/import_graph.dot` | `--deep` + `--export-graph` | Graphviz DOT format |
| `.project-control/exports/import_graph.mmd` | `--deep` + `--export-graph` | Mermaid diagram format |
| `.project-control/drift_history.json` | `--deep` + `--compare-snapshot` | Historical drift records |

**Deep Mode Required:** 
- Required for: Import Graph, Metrics, Anomaly, Export, Drift, Trend
- Not required for: Basic ghost detectors (Orphans, Legacy, Session, Duplicates, Semantic)

**Exit Codes:**
- `0` - Success
- `2` - Severity limit violation (when `--max-*` flags are set)

---

### 6. `pc writers`

**Purpose:** Analyze Three.js writer property usage

**Flags:** None

**Layers Triggered:** None (custom analysis only)

**Output Files:**
- `.project-control/exports/writers_report.md`

**Deep Mode Required:** No

---

## Analysis Layers Reference

### Layer 1: Import Graph
**Module:** `project_control/analysis/import_graph_detector.py`  
**Function:** `detect_graph_orphans()`  
**Purpose:** Build dependency graphs for Python and JavaScript projects  
**Engines Used:**
- `PythonImportGraphEngine`
- `JSImportGraphEngine`

**Outputs:**
- Graph structure (dict of node → set of neighbors)
- Graph orphans (unreachable nodes)
- Entrypoints (resolved via `EntryPointPolicy`)

---

### Layer 2: Metrics
**Module:** `project_control/analysis/graph_metrics.py`  
**Class:** `GraphMetrics`  
**Method:** `compute()`  
**Purpose:** Calculate structural metrics for import graph

**Metrics Computed:**
- `node_count` - Total nodes in graph
- `edge_count` - Total edges in graph
- `density` - Graph density (edges / possible edges)
- `reachable_count` - Reachable nodes from entrypoints
- `unreachable_count` - Unreachable nodes (orphans)
- `is_dag` - Whether graph is a DAG (no cycles)
- `largest_component_size` - Size of largest connected component
- `avg_degree` - Average node degree
- `max_degree` - Maximum node degree

---

### Layer 3: Anomaly
**Module:** `project_control/analysis/graph_anomaly.py`  
**Class:** `GraphAnomalyAnalyzer`  
**Method:** `analyze()`  
**Purpose:** Detect architectural anti-patterns and code smells

**Anomalies Detected:**
- `cycle_groups` - Lists of nodes in each cycle (SCCs)
- `god_modules` - Nodes with extremely high fan-in/out
- `dead_clusters` - Isolated subgraphs
- `isolated_nodes` - Nodes with no connections
- `smell_score` - Aggregate architectural smell score (0.0-1.0)
- `smell_level` - Severity classification (LOW/MEDIUM/HIGH)

---

### Layer 4: Drift
**Module:** `project_control/analysis/graph_drift.py`  
**Functions:** `compare_snapshots()`, `classify_drift()`  
**Purpose:** Compare two graph snapshots and detect structural changes

**Drift Components:**
- **Node Drift:** Added/removed nodes
- **Edge Drift:** Added/removed edges (as sorted tuples)
- **Entrypoint Drift:** Added/removed entrypoints
- **Metric Deltas:** Changes in nodes, edges, density, cycle_groups, smell_score

**Severity Classification:**
- `HIGH` - >10% node change OR smell_score delta > 0.1
- `MEDIUM` - Structural changes not meeting HIGH criteria
- `LOW` - Minor edge-only changes
- `NONE` - No changes detected

---

### Layer 5: Trend
**Module:** `project_control/analysis/graph_trend.py`  
**Class:** `GraphTrendAnalyzer`  
**Method:** `compute()`  
**Purpose:** Compute stability trends from historical drift records

**Trend Metrics:**
- `intensity` - List of intensity scores for each drift record
- `avg_intensity` - Average change intensity
- `volatility` - Standard deviation of intensity
- `stability_index` - 1 / (1 + avg_intensity)
- `classification` - STABLE/MODERATE/UNSTABLE

**Trigger Condition:** Requires ≥ 2 drift records in history

---

### Layer 6: Export
**Module:** `project_control/analysis/graph_exporter.py`  
**Functions:** `export_dot()`, `export_mermaid()`  
**Purpose:** Export graph structure to external visualization formats

**Formats:**
- DOT (Graphviz format) - `.dot` file
- Mermaid - `.mmd` file

---

## Flag Usage Analysis

### Documented Flags (in CLI help)
✅ All 10 flags are properly documented in `argparse` help text:
- `--deep`
- `--stats`
- `--tree-only`
- `--export-graph`
- `--mode`
- `--max-high`
- `--max-medium`
- `--max-low`
- `--max-info`
- `--compare-snapshot`

### Unused Flags
❌ None detected. All defined flags are used in the codebase.

### Undocumented Flags
❌ None detected. All flags have help text defined.

### Flag Dependencies

| Flag | Requires | Implicit Dependency |
|------|----------|---------------------|
| `--tree-only` | `--deep` | Must run import graph analysis |
| `--export-graph` | `--deep` | Must generate graph first |
| `--compare-snapshot` | `--deep` | Must compute current graph for comparison |
| `--stats` | None | Disables report generation |
| `--mode` | `--deep` | Only affects import graph analysis |

---

## Ghost Detectors Summary

| Detector | Severity | Output Key | Always Runs? |
|----------|----------|------------|--------------|
| Orphan Detector | HIGH | `orphans` | ✅ Yes |
| Legacy Detector | MEDIUM | `legacy` | ✅ Yes |
| Session Detector | LOW | `session` | ✅ Yes |
| Duplicate Detector | INFO | `duplicates` | ✅ Yes |
| Semantic Detector | INFO | `semantic_findings` | ✅ Yes |
| Import Graph | CRITICAL | `graph_orphans` | ❌ No (`--deep`) |

---

## Output Files Reference

| File | Command | Condition | Format |
|------|---------|-----------|--------|
| `.project-control/patterns.yaml` | `init` | Always | YAML |
| `.project-control/status.yaml` | `init` | Always | YAML |
| `.project-control/snapshot.json` | `scan` | Always | JSON |
| `.project-control/exports/checklist.md` | `checklist` | Always | Markdown |
| `.project-control/exports/find_<symbol>.md` | `find` | Always | Markdown |
| `.project-control/exports/ghost_candidates.md` | `ghost` | Unless `--stats` | Markdown |
| `.project-control/exports/import_graph_orphans.md` | `ghost --deep` | `--deep` flag | Markdown |
| `.project-control/exports/import_graph.dot` | `ghost --deep --export-graph` | Both flags | DOT |
| `.project-control/exports/import_graph.mmd` | `ghost --deep --export-graph` | Both flags | Mermaid |
| `.project-control/exports/writers_report.md` | `writers` | Always | Markdown |
| `.project-control/drift_history.json` | `ghost --deep --compare-snapshot` | Both flags | JSON |

---

## Stub Commands (Not Implemented)

### Command: `diff`
**Location:** `project_control/cli/diff_cmd.py`  
**Status:** Empty file (no implementation)  
**CLI Registration:** Not registered in `pc.py`  
**Notes:** Appears to be planned for snapshot comparison functionality

### Command: `duplicate`
**Location:** `project_control/cli/duplicate_cmd.py`  
**Status:** Empty file (no implementation)  
**CLI Registration:** Not registered in `pc.py`  
**Notes:** Duplicate detection is integrated into `ghost` command already

### Command: `graph`
**Location:** `project_control/cli/graph_cmd.py`  
**Status:** Empty file (no implementation)  
**CLI Registration:** Not registered in `pc.py`  
**Notes:** Graph analysis is integrated into `ghost --deep` command

---

## Recommendations

### 1. Remove or Implement Stub Commands
- Either implement `diff`, `duplicate`, and `graph` commands
- Or remove empty files from `project_control/cli/` directory to avoid confusion

### 2. Improve Flag Validation
- Add validation to ensure `--tree-only` requires `--deep`
- Add validation to ensure `--export-graph` requires `--deep`
- Add validation to ensure `--compare-snapshot` requires `--deep`

### 3. Documentation Updates
- Document the new `--compare-snapshot` flag in user documentation
- Document the drift and trend analysis features
- Document the new `drift_history.json` file format

### 4. CLI Reorganization Consideration
- Consider moving ghost command logic from `pc.py` to `project_control/cli/ghost_cmd.py`
- This would align with the existing CLI directory structure

---

## Summary Statistics

- **Total Commands:** 6 active + 3 stubs
- **Total Flags:** 10 (all in `ghost` command)
- **Analysis Layers:** 6 (Import Graph, Metrics, Anomaly, Drift, Trend, Export)
- **Ghost Detectors:** 6 (5 always + 1 conditional)
- **Output Files:** 10 distinct file types
- **Deep Mode Required For:** 4 layers (Import Graph, Metrics, Anomaly, Export)
- **Exit Codes:** 0 (success), 2 (limit violation)

---

**End of CLI Capability Audit Report**