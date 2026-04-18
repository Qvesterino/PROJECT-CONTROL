# COMMAND REFERENCE

## Project Management
- pc init --> Initializes PROJECT CONTROL structure in current directory, creates .project-control directory with exports subdirectory, generates default patterns.yaml configuration file, and creates empty status.yaml with tags dictionary
- pc scan --> Scans project directory recursively, indexes files matching configured extensions (default: .py, .js, .ts, .md, .txt), ignores directories specified in patterns.yaml (default: .git, .project-control, node_modules, __pycache__), saves snapshot to .project-control/snapshot.json with file count and file metadata
- pc checklist --> Loads existing snapshot from .project-control/snapshot.json, generates markdown checklist with all indexed files as unchecked items, saves checklist to .project-control/exports/checklist.md for manual tracking

## Analysis & Search
- pc find [symbol] --> Searches project files for specified symbol using ripgrep, saves search results to .project-control/exports/find_[symbol].md with usage documentation, returns validation error if no symbol is provided

## Ghost Analysis
- pc ghost --> Runs shallow ghost code analysis detecting orphans, legacy snippets, session files, duplicates, and semantic findings. Generates smart ghost report at .project-control/exports/ghost_candidates.md with severity levels (HIGH, MEDIUM, LOW, INFO)
- pc ghost --mode [strict|pragmatic] --> Sets ghost detection mode to strict (no ignore patterns applied) or pragmatic (default, applies ignore patterns from patterns.yaml), affects which files are flagged as candidates
- pc ghost --max-high [value] --> Sets maximum allowed count for HIGH severity issues (orphans), command exits with validation error if threshold is exceeded
- pc ghost --max-medium [value] --> Sets maximum allowed count for MEDIUM severity issues (legacy snippets), command exits with validation error if threshold is exceeded
- pc ghost --max-low [value] --> Sets maximum allowed count for LOW severity issues (session files), command exits with validation error if threshold is exceeded
- pc ghost --max-info [value] --> Sets maximum allowed count for INFO severity issues (duplicates), command exits with validation error if threshold is exceeded

## Code Quality
- pc writers --> Analyzes codebase for writer patterns (scale, emissive, opacity, position by default), generates writers report with usage statistics and recommendations, saves report to .project-control/exports/writers_report.md in markdown format

## Dependency Graph Engine
- pc graph build [project_root] --> Builds deterministic JS/TS dependency graph using existing .project-control/snapshot.json (run pc scan first), writes graph.snapshot.json, graph.metrics.json, and graph.report.md to .project-control/out/
- pc graph report [project_root] --> Regenerates dependency graph report from cache if valid, otherwise rebuilds. Outputs graph.report.md into .project-control/out/
- pc graph trace [target] --> Traces dependency paths to/from a target symbol or file. Options: --direction (inbound/outbound/both), --max-depth, --max-paths, --no-limits, --line (include line context)

## Embedding System (requires Ollama)
- pc embed build [path] --> Builds FAISS embedding index from code files using Ollama qwen3-embedding model
- pc embed rebuild [path] --> Rebuilds embedding index from scratch
- pc embed search [query] [path] --> Searches codebase using semantic similarity, returns top-k results

## Interactive UI
- pc ui --> Launches interactive text-based menu with scan, ghost, graph report, and trace options
