# PROJECT CONTROL

**Find dead code. Understand your architecture. Stop guessing.**

[![CI](https://github.com/danielhlavac/project-control/actions/workflows/ci.yml/badge.svg)](https://github.com/danielhlavac/project-control/actions/workflows/ci.yml)
[![PyPI version](https://badge.fury.io/py/project-control.svg)](https://badge.fury.io/py/project-control)
[![Python Versions](https://img.shields.io/pypi/pyversions/project-control.svg)](https://pypi.org/project/project-control/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

Project Control is a deterministic analysis tool that tells you what is really happening inside your codebase.

---

## Install / Update / Upgrade

### Use from any repository

Install it once:

```bash
pipx install .
```

Then go to any project and use:

```bash
pc init
pc scan
pc tui
pc gui
pc artifacts
pc audits retention
```

### Use directly from this repository

From the PROJECT_CONTROL repository root on Windows:

```bash
.\pc.ps1 tui
.\pc.cmd gui
python .\pc.py tui
python .\pc.py gui
```

PowerShell does not run local scripts from the current folder unless you prefix them with `.\`.

### Update / Upgrade

If you installed PROJECT CONTROL in editable mode for development:

```bash
git pull
python -m pip install -e .
```

You usually only need the second command when dependencies, packaging metadata, or launcher entrypoints changed.

If you installed it with `pipx`, update it with:

```bash
pipx upgrade project-control
```

Do not uninstall first unless you are intentionally cleaning up a broken install.

---

## 30-Second Demo

```bash
pc init
pc scan
pc ghost
pc graph report
```

If `pc` is not recognized on your machine, use one of these local launchers from the repository root instead:

```bash
.\pc.ps1 gui           # PowerShell repo-local launcher
.\pc.cmd tui           # CMD repo-local launcher
python .\pc.py gui     # Python fallback
python .\pc.py tui     # Python fallback
```

Or use the new diagnostic commands:

```bash
pc dead        # Find dead code
pc unused      # Find unused systems
pc patterns    # Detect suspicious patterns
pc search TODO # Smart search
pc artifacts   # Find temporary screenshots and debug assets
pc audits retention # Find stale generated audits and reports
```

That's it. You now understand your codebase.

---

## What is Ghost Analysis?

Ghost analysis finds parts of your codebase that no longer matter:

- **Orphans** — files that are never referenced by anything
- **Legacy** — outdated code matching known legacy patterns
- **Sessions** — temporary or session artifacts left behind
- **Duplicates** — files with identical names in different paths
- **Semantic** — files that don't belong (embedding-powered, optional)

It is fast, heuristic, and designed to highlight architectural drift before it becomes technical debt.

### Example Output

```
$ pc ghost

Ghost Results
-------------
Orphans:    31
Legacy:      0
Sessions:    0
Duplicates:  0
Semantic:   61
```

A detailed markdown report is generated at `.project-control/exports/ghost_candidates.md`.

---

## Features

| Feature | Description |
|---------|-------------|
| **Snapshot Scan** | Recursively indexes files with SHA256 hashing and content deduplication |
| **Ghost Analysis** | Detects orphan files, legacy snippets, session files, duplicates, and semantic outliers |
| **Dead Code Radar** | Finds files with zero or minimal usage (ripgrep-based) |
| **Unused System Scan** | Identifies unused systems (Manager, Controller, Service, etc.) |
| **Suspicious Patterns** | Detects forbidden or problematic code patterns (debug code, hardcoded values, etc.) |
| **Smart Search** | Power-user code search with advanced filters (invert, files-only) |
| **Dependency Graph** | Builds a deterministic import graph for Python and JS/TS projects |
| **Graph Trace** | Traces dependency paths to/from any symbol or file |
| **Artifact Hygiene** | Finds suspicious screenshots, debug assets, and other temporary visual artifacts without deleting them |
| **Audit Retention** | Finds stale generated audits, reports, checklists, and export files that are likely safe to remove |
| **TUI** | Text-based menu with quick actions, favorites, and smart notifications |
| **Color Terminal Output** | Cross-platform color support with graceful fallback for terminals without ANSI support |
| **Quick Actions** | One-click full analysis, health checks, and common tasks |
| **Backup & Rollback** | Automatic backups before destructive operations with restore capability |
| **Favorites & History** | Save frequently traced targets and view recent actions |
| **Embedding Search** | Semantic code search powered by local Ollama (optional) |

---

## Requirements

- **Python 3.10+**
- **ripgrep** (`rg`) — required for symbol search and orphan detection

### Optional (for semantic analysis)

Embedding is **optional and not required for core functionality**. You can safely ignore this section if you only want structural analysis.

If you want semantic code search and semantic ghost detection:

- **[Ollama](https://ollama.ai)** — local LLM server (runs on your machine, no cloud)
- **FAISS** + **NumPy** — installed automatically with `pip install -e ".[embedding]"`

---

## Installation

### Install matrix

**End users**

```bash
pipx install project-control
```

If you are running from a source checkout instead of PyPI:

```bash
pipx install .
```

**Contributors**

```bash
pip install -e .
```

### Option 1: Install from PyPI

```bash
pip install project-control
```

Or with embedding support for semantic analysis:

```bash
pip install project-control[embedding]
```

### Option 2: Install from source

```bash
git clone https://github.com/danielhlavac/project-control.git
cd project-control
pip install -e .
```

This installs the `pc` command and core dependencies (`pyyaml`).

### Embedding support (optional)

If you installed with embedding support, you'll need Ollama:

```bash
ollama serve
ollama pull qwen3-embedding:8b
```

### Verify installation

```bash
pc --version
pc --help
```

If `pc` says "not recognized", that means the package is not installed into your shell PATH yet. You can either:

```bash
pipx install .
```

or run it locally from the repository root without installing:

```bash
.\pc.ps1 gui
.\pc.cmd tui
python .\pc.py gui
python .\pc.py tui
```

---

## Quick Start

### Step 1: Initialize

```bash
cd /path/to/your/project
pc init
```

Creates `.project-control/` directory with default configuration.

### Step 2: Scan

```bash
pc scan
```

Indexes all files matching configured extensions (`.py`, `.js`, `.ts`, `.md`, `.txt`). Saves snapshot to `.project-control/snapshot.json`.

### Step 3: Analyze

```bash
# Ghost analysis — finds dead code
pc ghost

# Build dependency graph
pc graph build

# Generate graph report
pc graph report

# Trace a symbol or file
pc graph trace src/utils.py

# NEW: Diagnostic commands
pc dead                # Dead Code Radar
pc unused              # Unused System Scan
pc patterns            # Suspicious Patterns
pc search "TODO"       # Smart Search
pc artifacts           # Artifact Hygiene
pc audits retention    # Audit Retention
```

### Or use the TUI / GUI

```bash
pc tui
pc gui
```

`pc gui` exposes both hygiene workflows in the `Audits` surface. `pc tui` exposes both as direct menu actions.

Windows note:
- PowerShell does not run scripts from the current directory unless you prefix them with `.\`
- That is why repo-local launchers are `.\pc.ps1 ...` and `.\pc.cmd ...`

Migration note:
- `pc ui` was removed in this release.
- Use `pc tui`, `pc tui menu`, and `pc tui verify` instead.

### Simplest launch from a cloned repository

Installed mode:

```bash
pc gui
pc tui
```

Repo-local mode from the repository root:

```bash
.\pc.ps1 gui
.\pc.cmd tui
python .\pc.py gui
python .\pc.py tui
```

On Windows you can also double-click:

```text
OPEN_PROJECT_CONTROL.bat
start_gui.bat
start_menu.bat
```

---

## Commands Reference

### Project Setup

| Command | Description |
|---------|-------------|
| `pc init` | Initialize `.project-control/` with default config |
| `pc scan` | Scan project files and create snapshot |
| `pc checklist` | Generate markdown checklist from snapshot |

### Analysis

| Command | Description |
|---------|-------------|
| `pc ghost` | Run ghost analysis (orphans, legacy, sessions, duplicates, semantic) |
| `pc ghost --mode strict` | Strict mode — no ignore patterns applied |
| `pc ghost --max-high 10` | Fail if more than 10 HIGH severity issues found |
| `pc ghost --tree` | Export results as ASCII tree files (easier to read than JSON) |
| `pc find <symbol>` | Search for symbol usage across project |
| `pc writers` | Analyze writer patterns in codebase |

### Diagnostic Commands

| Command | Description |
|---------|-------------|
| `pc dead` | Dead Code Radar — finds files with zero or minimal usage |
| `pc dead --threshold 2` | Set max usage count for low-usage detection |
| `pc unused` | Unused System Scan — finds systems (Manager, Controller, etc.) that aren't used |
| `pc patterns` | Suspicious Patterns — detects forbidden or problematic code patterns |
| `pc patterns --file <path>` | Use custom patterns YAML file |
| `pc search <pattern>` | Smart Search — power-user code search |
| `pc search <pattern> --files-only` | Return only file paths (no line details) |
| `pc search <pattern> --not` | Find files that DO NOT match the pattern |
| `pc artifacts` | Artifact Hygiene — find temporary screenshots and debug assets |
| `pc artifacts --delete-list` | Print strict safe-to-delete artifact paths |
| `pc audits retention` | Audit Retention — find stale generated audits and reports |
| `pc audits retention --delete-list` | Print strict safe-to-delete audit/report paths |

### Dependency Graph

| Command | Description |
|---------|-------------|
| `pc graph build` | Build import dependency graph |
| `pc graph report` | Generate graph report (uses cache if valid) |
| `pc graph trace <target>` | Trace dependency paths to/from target |
| `pc graph trace <target> --direction inbound` | Trace only incoming dependencies |
| `pc graph trace <target> --line` | Include line-level context |

### Embedding (optional)

| Command | Description |
|---------|-------------|
| `pc embed build` | Build FAISS embedding index |
| `pc embed rebuild` | Rebuild index from scratch |
| `pc embed search "query"` | Semantic code search |

### TUI / GUI

| Command | Description |
|---------|-------------|
| `pc tui` | Launch the TUI text-based menu |
| `pc gui` | Launch desktop Tkinter GUI |

## Hygiene Workflows

Two cleanup-oriented workflows are available for generated outputs and temporary artifacts:

- `Artifact Hygiene` targets screenshots, Playwright outputs, and other temporary visual assets.
- `Audit Retention` targets stale generated audits, reports, checklists, and export files.

Both workflows are analyze-only. They never delete files automatically.

```bash
pc artifacts
pc artifacts --json
pc audits retention
pc audits retention --delete-list
```

Generated exports:

- `.project-control/exports/artifact_candidates.md`
- `.project-control/exports/artifact_candidates.json`
- `.project-control/exports/delete_candidates.txt`
- `.project-control/exports/audit_retention_candidates.md`
- `.project-control/exports/audit_retention_candidates.json`
- `.project-control/exports/audit_delete_candidates.txt`

---

## Configuration

Configuration is stored in `.project-control/patterns.yaml`:

```yaml
writers:
  - scale
  - emissive
  - opacity
  - position
entrypoints:
  - main.js
  - index.ts
ignore_dirs:
  - .git
  - .project-control
  - node_modules
  - __pycache__
extensions:
  - .py
  - .js
  - .ts
  - .md
  - .txt
artifacts:
  older_than_days: 30
  min_score: 8
audit_retention:
  older_than_days: 45
  keep_latest_per_family: 3
```

Graph configuration is in `.project-control/graph_config.yaml` (auto-created on first `pc graph build`).

---

## Output Files

All outputs are stored in `.project-control/`:

```
.project-control/
├── snapshot.json              # File metadata (from pc scan)
├── patterns.yaml              # Configuration (includes diagnostic patterns)
├── content/                   # Deduplicated file blobs
├── exports/
│   ├── ghost_candidates.md    # Ghost analysis report
│   ├── artifact_candidates.md # Artifact hygiene report
│   ├── artifact_candidates.json # Artifact hygiene data
│   ├── delete_candidates.txt  # Artifact safe-delete list
│   ├── audit_retention_candidates.md # Audit retention report
│   ├── audit_retention_candidates.json # Audit retention data
│   ├── audit_delete_candidates.txt # Audit retention safe-delete list
│   ├── ghost_orphans_tree.txt # ASCII tree of orphan files
│   ├── ghost_legacy_tree.txt  # ASCII tree of legacy files
│   ├── ghost_sessions_tree.txt # ASCII tree of session files
│   ├── ghost_duplicates_tree.txt # ASCII tree of duplicate files
│   ├── ghost_semantic_tree.txt # ASCII tree of semantic findings
│   ├── checklist.md           # File checklist
│   ├── find_<symbol>.md       # Symbol search results
│   └── writers_report.md      # Writers analysis
├── out/
│   ├── graph.snapshot.json    # Graph structure
│   ├── graph.metrics.json     # Graph metrics
│   ├── graph.report.md        # Graph report
│   └── graph.trace.txt        # Trace output
└── embeddings/                # Embedding cache (optional)
```

**Note:** Some diagnostic commands (`pc dead`, `pc unused`, `pc patterns`, `pc search`) output directly to terminal and don't create export files. Hygiene workflows do create markdown, JSON, and delete-list exports.

### ASCII Tree Export

When you run `pc ghost --tree`, the tool generates ASCII tree files that are much easier to read than JSON. For example:

```bash
$ pc ghost --tree

Ghost Results
-------------
Orphans:   31
Legacy:    0
Sessions:  0
Duplicates: 0
Semantic:  61

📄 Tree reports saved to:
   - ghost_orphans_tree.txt
   - ghost_semantic_tree.txt
```

The tree files look like this:

```
Orphans
+--- src
|   +--- old_utils.py
|   \--- deprecated_feature.js
\--- tests
    \--- test_old_feature.py
```

This format is perfect for quickly understanding the structure of dead code in your project.

---

## How It Works

### Snapshot System

`pc scan` creates a deterministic snapshot of your project:
- Recursively walks the directory tree
- Computes SHA256 hash for each file
- Stores deduplicated content blobs in `.project-control/content/`
- Saves metadata to `snapshot.json`

### Ghost Analysis

`pc ghost` runs five detectors on your codebase:

1. **Orphan Detector** — finds files not referenced by any other file (via ripgrep)
2. **Legacy Detector** — identifies files matching legacy patterns
3. **Session Detector** — finds temporary/session files
4. **Duplicate Detector** — detects files with identical names in different paths
5. **Semantic Detector** — uses embeddings to find semantically similar or orphan files (optional, requires Ollama)

### Graph Engine

`pc graph build` constructs a deterministic import dependency graph:
- Extracts imports using AST for Python and regex for JS/TS
- Resolves relative imports to actual file paths
- Computes metrics: node count, edge count, fan-in/out, cycles (Tarjan SCC), orphan candidates
- Caches results based on snapshot hash — rebuilds only when files change

---

## Running Tests

```bash
python -m unittest discover tests/ -v
```

---

## Project Structure

```
project_control/
├── pc.py                      # CLI entrypoint
├── cli/
│   ├── router.py              # Command dispatch
│   ├── graph_cmd.py           # Graph commands
│   └── menu.py                # Interactive menu
├── core/
│   ├── ghost.py               # Canonical ghost core (pure function)
│   ├── ghost_service.py       # Ghost execution service
│   ├── scanner.py             # File scanner
│   ├── snapshot_service.py    # Snapshot I/O
│   ├── content_store.py       # Content deduplication
│   ├── embedding_service.py   # Embedding computation
│   └── markdown_renderer.py   # Report rendering
├── analysis/
│   ├── orphan_detector.py     # Orphan detection
│   ├── legacy_detector.py     # Legacy detection
│   ├── session_detector.py    # Session detection
│   ├── duplicate_detector.py  # Duplicate detection
│   ├── semantic_detector.py   # Semantic detection
│   ├── dead_analyzer.py       # Dead code analyzer
│   ├── unused_analyzer.py     # Unused systems analyzer
│   ├── patterns_analyzer.py   # Suspicious patterns analyzer
│   └── search_analyzer.py     # Smart search analyzer
├── graph/
│   ├── builder.py             # Graph builder
│   ├── metrics.py             # Metrics computation
│   ├── trace.py               # Path tracing
│   ├── artifacts.py           # Output writing
│   └── extractors/            # Language-specific import extractors
├── utils/
│   ├── fs_helpers.py          # Filesystem helpers
│   ├── rg_helper.py           # Ripgrep wrapper with JSON output
│   └── renderers.py           # CLI output rendering
├── embedding/                 # Embedding system (optional)
└── experimental/
    └── ghost_deep/            # Preserved deep ghost code (not active)
```

---

## License

MIT
