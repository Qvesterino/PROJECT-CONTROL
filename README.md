# PROJECT CONTROL

**Deterministic architectural analysis engine** for codebases.

Project Control scans your project, detects dead code, builds dependency graphs, and helps you keep your architecture clean.

---

## Features

| Feature | Description |
|---------|-------------|
| **Snapshot Scan** | Recursively indexes files with SHA256 hashing and content deduplication |
| **Ghost Analysis** | Detects orphan files, legacy snippets, session files, duplicates, and semantic outliers |
| **Dependency Graph** | Builds a deterministic import graph for Python and JS/TS projects |
| **Graph Trace** | Traces dependency paths to/from any symbol or file |
| **Interactive UI** | Text-based menu for guided analysis |
| **Embedding Search** | Semantic code search powered by Ollama (optional) |

---

## Requirements

- **Python 3.10+**
- **ripgrep** (`rg`) — required for symbol search and orphan detection
- **Git** — recommended for version control integration

### Optional (for semantic analysis)

- **[Ollama](https://ollama.ai)** — local LLM server for embedding computation
- **FAISS** + **NumPy** — for vector similarity search

---

## Installation

### 1. Clone and install

```bash
git clone <your-repo-url>
cd PROJECT_CONTROL
pip install -e .
```

This installs the `pc` command and core dependencies (`pyyaml`).

### 2. Install with embedding support (optional)

```bash
pip install -e ".[embedding]"
```

Then start Ollama and pull the embedding model:

```bash
ollama serve
ollama pull qwen3-embedding:8b
```

### 3. Verify installation

```bash
pc --help
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
```

### Or use the interactive UI

```bash
pc ui
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
| `pc find <symbol>` | Search for symbol usage across project |
| `pc writers` | Analyze writer patterns in codebase |

### Dependency Graph

| Command | Description |
|---------|-------------|
| `pc graph build` | Build import dependency graph |
| `pc graph report` | Generate graph report (uses cache if valid) |
| `pc graph trace <target>` | Trace dependency paths to/from target |
| `pc graph trace <target> --direction inbound` | Trace only incoming dependencies |
| `pc graph trace <target> --line` | Include line-level context |

### Embedding (requires Ollama)

| Command | Description |
|---------|-------------|
| `pc embed build` | Build FAISS embedding index |
| `pc embed rebuild` | Rebuild index from scratch |
| `pc embed search "query"` | Semantic code search |

### Interactive

| Command | Description |
|---------|-------------|
| `pc ui` | Launch interactive text-based menu |

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
```

Graph configuration is in `.project-control/graph_config.yaml` (auto-created on first `pc graph build`).

---

## Output Files

All outputs are stored in `.project-control/`:

```
.project-control/
├── snapshot.json              # File metadata (from pc scan)
├── patterns.yaml              # Configuration
├── content/                   # Deduplicated file blobs
├── exports/
│   ├── ghost_candidates.md    # Ghost analysis report
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
5. **Semantic Detector** — uses embeddings to find semantically similar or orphan files (requires Ollama)

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
│   └── semantic_detector.py   # Semantic detection
├── graph/
│   ├── builder.py             # Graph builder
│   ├── metrics.py             # Metrics computation
│   ├── trace.py               # Path tracing
│   ├── artifacts.py           # Output writing
│   └── extractors/            # Language-specific import extractors
├── embedding/                 # Embedding system (optional)
└── experimental/
    └── ghost_deep/            # Preserved deep ghost code (not active)
```

---

## License

This project is provided as-is for internal use.
