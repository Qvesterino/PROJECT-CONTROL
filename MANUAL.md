# COMMAND REFERENCE

## Project Management
- `pc init` --> Initializes PROJECT CONTROL in the current directory, creates `.project-control/`, writes default `patterns.yaml`, and creates `status.yaml`
- `pc scan` --> Scans the project recursively, indexes matching files, and saves the snapshot to `.project-control/snapshot.json`
- `pc checklist` --> Loads the current snapshot and generates `.project-control/exports/checklist.md`

## Analysis & Search
- `pc ghost` --> Runs shallow ghost analysis and writes `.project-control/exports/ghost_candidates.md`
- `pc ghost --mode [strict|pragmatic]` --> Chooses strict or pragmatic ghost analysis mode
- `pc ghost --max-high [value]` --> Fails if orphan count exceeds the threshold
- `pc ghost --max-medium [value]` --> Fails if legacy count exceeds the threshold
- `pc ghost --max-low [value]` --> Fails if session count exceeds the threshold
- `pc ghost --max-info [value]` --> Fails if duplicate count exceeds the threshold
- `pc find [symbol]` --> Searches project files for a symbol and writes `.project-control/exports/find_[symbol].md`
- `pc dead` --> Finds unused or low-usage files from the current snapshot
- `pc unused` --> Finds unused systems and modules
- `pc patterns` --> Detects suspicious or forbidden code patterns
- `pc search [pattern]` --> Runs power-user text search across the project
- `pc writers` --> Analyzes writer patterns and writes `.project-control/exports/writers_report.md`

## Hygiene Workflows
- `pc artifacts` --> Runs Artifact Hygiene and reports temporary screenshots, debug assets, and similar visual artifacts
- `pc artifacts --json` --> Prints the structured artifact payload
- `pc artifacts --delete-list` --> Prints the strict safe-to-delete artifact list
- `pc audits retention` --> Runs Audit Retention and reports stale generated audits, reports, checklists, and exports
- `pc audits retention --json` --> Prints the structured audit-retention payload
- `pc audits retention --delete-list` --> Prints the strict safe-to-delete audit/report list

Standard hygiene exports:
- `.project-control/exports/artifact_candidates.md`
- `.project-control/exports/artifact_candidates.json`
- `.project-control/exports/delete_candidates.txt`
- `.project-control/exports/audit_retention_candidates.md`
- `.project-control/exports/audit_retention_candidates.json`
- `.project-control/exports/audit_delete_candidates.txt`

## Dependency Graph
- `pc graph build [project_root]` --> Builds the deterministic dependency graph from the current snapshot
- `pc graph report [project_root]` --> Regenerates graph artifacts from cache or rebuilds when needed
- `pc graph trace [target]` --> Traces dependency paths to and from a target symbol or file

## Embedding System (optional)
- `pc embed build [path]` --> Builds the FAISS embedding index
- `pc embed rebuild [path]` --> Rebuilds the embedding index from scratch
- `pc embed search [query] [path]` --> Runs semantic search

Notes:
- Embedding is optional
- Requires Ollama
- If unavailable, semantic analysis degrades gracefully

## TUI
- `pc tui` --> Launches the TUI text-based menu
- `pc tui menu` --> Explicitly launches the TUI text-based menu
- `pc tui verify` --> Runs browser-based UI verification
- `pc gui` --> Launches the desktop GUI

### Launch Modes
- **Installed mode** --> `pc gui`, `pc tui`, `pc scan`
- **Repo-local mode (Windows)** --> `.\pc.ps1 gui`, `.\pc.cmd tui`
- **Python fallback** --> `python .\pc.py gui`, `python .\pc.py tui`

### Install Matrix
- **End users** --> `pipx install project-control`
- **Source checkout users** --> `pipx install .`
- **Contributors** --> `pip install -e .`

### Windows Note
- PowerShell does not run scripts from the current directory unless you prefix them with `.\`
- That is why the repo-local launcher is `.\pc.ps1 ...` instead of bare `pc ...`

### Removal Note
- `pc ui`, `pc ui menu`, and `pc ui verify` were removed in this release
- Migration path:
  - `pc ui` → `pc tui`
  - `pc ui menu` → `pc tui menu`
  - `pc ui verify` → `pc tui verify`

### Keyboard Shortcuts

In the TUI (`pc tui`), you can use these keyboard shortcuts:

| Shortcut | Action |
|----------|--------|
| `0` | Return to previous menu / Exit |
| `1-6` | Select main menu option by number |
| `Q` | Open Quick Actions |
| `Enter` | Confirm selection / Continue |

### Color Terminal Output

PROJECT CONTROL uses color-coded output for readability:

| Color | Usage |
|-------|-------|
| **Green** | Success messages, completed operations, healthy status |
| **Yellow** | Warnings, cautions, issues that need attention |
| **Red** | Errors, failed operations, critical issues |
| **Cyan** | Information messages, neutral status |

### Quick Actions

The TUI Quick Actions panel includes:

| Option | Action |
|--------|--------|
| `1` | Full Analysis — scan → ghost → graph → report |
| `2` | Health Check — validate everything |
| `3` | Find Orphans — quick orphan scan |
| `4` | Find Cycles — quick cycle detection |
| `5` | Dependency Audit — analyze dependency graph |
| `6` | VFX Audit — audit FX contract compliance |
| `7` | UI Verify — run browser-based UI verification |
| `8` | Artifact Hygiene — find temporary screenshots and debug assets |
| `9` | Audit Retention — find stale generated audits and reports |
| `10` | Favorites — manage favorite trace targets |
| `11` | History — view recent actions |

### Tools Menu

| Option | Action |
|--------|--------|
| `1` | List Backups |
| `2` | Create Manual Backup |
| `3` | Restore Backup |
| `4` | Delete Backup |
| `5` | Cleanup Old Backups |
| `6` | Clear Graph Cache |
| `7` | Show Diagnostics |

### Favorites & History

- **Favorites**: Save frequently traced targets for fast reuse
- **History**: Review recent actions from the TUI session state

## Experimental Features

Some advanced analysis features (deep graph analysis, anomaly detection, drift tracking) are isolated and not part of the core CLI.

They live in:
- `project_control/experimental/`

They are:
- not executed during normal CLI usage
- not guaranteed to be stable
- reserved for future versions

## Philosophy

PROJECT CONTROL is a deterministic developer tool.

It prioritizes:
- correctness over guesswork
- simplicity over feature complexity
- stability over experimentation
