# COMMAND REFERENCE

## Project Management
- pc init --> Initializes PROJECT CONTROL structure in current directory, creates .project-control directory with exports subdirectory, generates default patterns.yaml configuration file, and creates empty status.yaml with tags dictionary
- pc scan --> Scans project directory recursively, indexes files matching configured extensions (default: .py, .js, .ts, .md, .txt), ignores directories specified in patterns.yaml (default: .git, .project-control, node_modules, __pycache__), saves snapshot to .project-control/snapshot.json with file count and file metadata
- pc checklist --> Loads existing snapshot from .project-control/snapshot.json, generates markdown checklist with all indexed files as unchecked items, saves checklist to .project-control/exports/checklist.md for manual tracking

## Analysis & Search
- pc find [symbol] --> Searches project files for specified symbol using ripgrep, saves search results to .project-control/exports/find_[symbol].md with usage documentation, returns validation error if no symbol is provided

- pc ghost --> Runs ghost code analysis detecting orphans, legacy snippets, session files, and duplicates, generates smart ghost report at .project-control/exports/ghost_candidates.md with severity levels (HIGH, MEDIUM, LOW, INFO), validates against severity limits if specified via --max-* flags

## Ghost Analysis Options
- pc ghost --deep --> Performs deep import graph analysis in addition to standard ghost analysis, builds static import dependency graph, identifies unreachable files from entrypoints, detects architectural anomalies (cycles, god modules, dead clusters), exports detailed import graph orphans report to .project-control/exports/import_graph_orphans.md
- pc ghost --stats --> Displays only analysis statistics without generating markdown reports, shows counts for import graph orphans (CRITICAL), orphans (HIGH), legacy snippets (MEDIUM), session files (LOW), and duplicates (INFO)
- pc ghost --tree-only --> Writes only tree view section to import_graph_orphans.md report when used with --deep, omits flat list of orphans, generates hierarchical directory structure based on import graph reachability
- pc ghost --export-graph --> Exports combined import graph in DOT format to .project-control/exports/import_graph.dot and Mermaid format to .project-control/exports/import_graph.mmd for visualization tools, requires --deep flag to function
- pc ghost --mode [strict|pragmatic] --> Sets ghost detection mode to strict (no ignore patterns applied) or pragmatic (default, applies ignore patterns from patterns.yaml), affects which files are flagged as candidates
- pc ghost --max-high [value] --> Sets maximum allowed count for HIGH severity issues (orphans), command exits with validation error if threshold is exceeded, returns exit code corresponding to validation error
- pc ghost --max-medium [value] --> Sets maximum allowed count for MEDIUM severity issues (legacy snippets), command exits with validation error if threshold is exceeded
- pc ghost --max-low [value] --> Sets maximum allowed count for LOW severity issues (session files), command exits with validation error if threshold is exceeded
- pc ghost --max-info [value] --> Sets maximum allowed count for INFO severity issues (duplicates), command exits with validation error if threshold is exceeded
- pc ghost --compare-snapshot [path] --> Compares current analysis against previous snapshot JSON file for architectural drift detection, requires --deep flag, reports node/edge drift, entrypoint changes, and metric deltas, appends drift entry to .project-control/drift_history.yaml
- pc ghost --validate-architecture --> Validates architecture layer boundaries before running ghost analysis, checks for layer violations in import statements, prints violations with file:line and import path information, exits with layer violation code if issues found, skips ghost analysis if validation fails
- pc ghost --debug --> Enables verbose debug output for deep analysis and validation operations, prints additional diagnostic information including drift history entry counts, version information, and internal processing details

## Code Quality
- pc writers --> Analyzes codebase for writer patterns (scale, emissive, opacity, position by default), generates writers report with usage statistics and recommendations, saves report to .project-control/exports/writers_report.md in markdown format

## Architecture Validation
- pc ghost --validate-architecture [standalone] --> Runs standalone architecture validation without ghost analysis, validates layer boundary rules defined in patterns.yaml, reports all violations with file paths, line numbers, and violated rules, returns exit code 0 if no violations detected

## Dependency Graph Engine
- pc graph build [project_root] --> Builds deterministic JS/TS dependency graph using existing .project-control/snapshot.json (run pc scan first), writes graph.snapshot.json, graph.metrics.json, and graph.report.md to .project-control/out/
- pc graph report [project_root] --> Regenerates dependency graph and markdown report from snapshot (same outputs as graph build) into .project-control/out/

## Graph Metrics (Available with --deep)
- pc ghost --deep [metrics output] --> Displays graph summary metrics after deep analysis including total node count, edge count, reachable/unreachable node counts, graph density, DAG status, and largest component size
- pc ghost --deep [anomaly output] --> Reports architectural anomalies including cycle groups, god modules, dead clusters, isolated nodes, and overall smell score with severity level classification
- pc ghost --deep --compare-snapshot [drift output] --> Generates architectural drift report comparing current and previous snapshots, reports nodes/edges/entrypoints added and removed, shows metric deltas with directional indicators (+/-), calculates and displays drift severity level
- pc ghost --deep --compare-snapshot [trend output] --> Computes stability trends when sufficient history exists (2+ drift entries), displays average intensity, volatility, stability index, and trend classification (STABLE/UNSTABLE/UNKNOWN), requires --compare-snapshot and historical drift data
