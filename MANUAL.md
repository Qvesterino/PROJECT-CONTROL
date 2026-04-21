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

## Experimental Features

Some advanced analysis features (deep graph analysis, anomaly detection, drift tracking)
are currently isolated and not part of the core CLI.

These live in:
project_control/experimental/

They are:

* not executed during normal CLI usage
* not guaranteed to be stable
* reserved for future versions

Core philosophy:

* CLI remains stable, fast, deterministic
* experimental features evolve separately

### Ghost Contract

Ghost analysis uses a stable core contract:

{
"orphans": list,
"legacy": list,
"duplicates": list,
"sessions": list,
"semantic": list
}

This contract is the single source of truth for all ghost results.

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

Notes:

* Embedding system is optional
* Requires external Ollama server
* If unavailable, semantic analysis is skipped gracefully



## Interactive UI
- pc ui --> Launches interactive text-based menu with scan, ghost, graph report, and trace options

### Keyboard Shortcuts

In the interactive menu (`pc ui`), you can use these keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| `0` | Return to previous menu / Exit |
| `1-7` | Select menu option by number |
| `Q` | Open Quick Actions menu |
| `Enter` | Confirm selection / Continue |

### Color Terminal Output

PROJECT_CONTROL uses color-coded output for better readability:

| Color | Usage |
|-------|-------|
| **Green** | Success messages, completed operations, healthy status |
| **Yellow** | Warnings, cautions, issues that need attention |
| **Red** | Errors, failed operations, critical issues |
| **Cyan** | Information messages, neutral status |

Color support is automatically detected and gracefully falls back to plain text on terminals that don't support ANSI escape codes (including some Windows console configurations).

**Status Indicators:**
- `[OK]` - Operation completed successfully
- `[WARN]` - Warning or caution
- `[FAIL]` / `[ERROR]` - Operation failed or error occurred
- `[INFO]` - Informational message

**Example Output:**
```
[OK] Snapshot created successfully!
[WARN] Graph is 3 days old. Rebuild recommended.
[ERROR] Snapshot not found. Run 'pc scan' first.
[INFO] Processing 247 files...
```

### Quick Actions Menu (Q)

Access frequently used operations:

| Option | Action |
|--------|--------|
| `1` | Full Analysis — scan → ghost → graph → report |
| `2` | Health Check — validate everything |
| `3` | Find Orphans — quick orphan scan |
| `4` | Find Cycles — quick cycle detection |
| `5` | Dependency Audit — analyze dependency graph |
| `6` | Favorites — manage favorite trace targets |
| `7` | History — view recent actions |

### Tools Menu (7)

Access utility functions:

| Option | Action |
|--------|--------|
| `1` | List Backups — show all available backups |
| `2` | Create Manual Backup — create a named backup |
| `3` | Restore Backup — restore from a backup |
| `4` | Delete Backup — delete a specific backup |
| `5` | Cleanup Old Backups — remove old backups (keep latest 5) |
| `6` | Clear Graph Cache — remove .project-control/out/ |
| `7` | Show Diagnostics — display system information |

### Favorites & History

- **Favorites**: Save frequently traced targets for quick access
  - In Explore menu, press `f` to add current target to favorites
  - In Quick Actions → Favorites, press `[1-N]` to trace a favorite
  - Favorites persist across sessions

- **History**: Automatically tracks your last 10 actions
  - View history in Quick Actions → History
  - Most recent action shown in header notifications


____


## Experimental Features

Some advanced analysis features (deep graph analysis, anomaly detection, drift tracking)
are currently isolated and not part of the core CLI.

These live in:
project_control/experimental/

They are:

* not executed during normal CLI usage
* not guaranteed to be stable
* reserved for future versions

Core philosophy:

* CLI remains stable, fast, deterministic
* experimental features evolve separately

## Philosophy

PROJECT CONTROL is a deterministic developer tool.

It prioritizes:

* correctness over guesswork
* simplicity over feature complexity
* stability over experimentation

Advanced analysis (AI, deep graph reasoning) is intentionally separated
from the core engine.
