# MEMORY.md

This document is your memory cheat sheet for PROJECT_CONTROL. Quick reference for finding things, understanding data flow, and remembering key patterns.

## Quick File Location Reference

### Core Analysis
| What You Need | File |
|---------------|------|
| **Ghost analysis (pure function)** | `core/ghost.py` |
| **Ghost execution service** | `core/ghost_service.py` |
| **All detectors** | `analysis/*.py` (orphan, legacy, session, duplicate, semantic) |
| **Snapshot scanner** | `core/scanner.py` |
| **Snapshot I/O** | `core/snapshot_service.py` |
| **Content store (CRITICAL)** | `core/content_store.py` |

### Graph Engine
| What You Need | File |
|---------------|------|
| **Graph builder** | `graph/builder.py` |
| **Graph metrics** | `graph/metrics.py` |
| **Path tracing** | `graph/trace.py` |
| **Import extractors** | `graph/extractors/*.py` (python_ast.py, js_ts.py, base.py) |
| **Extractor registry** | `graph/extractors/registry.py` |
| **Specifier resolution** | `graph/resolver.py` |

### CLI Layer
| What You Need | File |
|---------------|------|
| **CLI entry point** | `pc.py` |
| **Command dispatch** | `cli/router.py` |
| **Graph CLI commands** | `cli/graph_cmd.py` |
| **Interactive menu** | `cli/menu.py` |

### Configuration
| What You Need | File |
|---------------|------|
| **Pattern config loader** | `config/patterns_loader.py` |
| **Graph config loader** | `config/graph_config.py` |
| **User patterns file** | `.project-control/patterns.yaml` (in project root) |
| **Graph config file** | `.project-control/graph.config.yaml` (in project root) |

### Services Layer
| What You Need | File |
|---------------|------|
| **Graph service** | `services/graph_service.py` |
| **Analysis service** | `services/analyze_service.py` |
| **Scan service** | `services/scan_service.py` |

## Key Functions & Their Locations

### Ghost Analysis
```python
# core/ghost.py - THE CANONICAL PURE FUNCTION
def ghost(snapshot, patterns, content_store) -> Dict[str, List[Any]]:
    """Returns exactly 5 keys: orphans, legacy, duplicates, sessions, semantic"""

# Each detector in analysis/*.py
def analyze(snapshot, patterns, content_store) -> List[Any]:
    """Detector interface - returns list of findings"""
```

### Snapshot System
```python
# core/scanner.py
def scan_project(project_root, ignore_dirs, extensions) -> Snapshot:
    """Walks tree, computes SHA256, stores blobs, returns snapshot"""

# core/content_store.py
class ContentStore:
    def get_text(path) -> str:
        """Get file content via snapshot + blob storage"""
    def get_blob(sha256) -> str:
        """Get content directly by SHA256"""
```

### Graph Engine
```python
# graph/builder.py
class GraphBuilder:
    def build(self) -> Dict:
        """Returns graph with meta, nodes, edges, entrypoints"""

# graph/extractors/python_ast.py (AST-based, accurate)
class PythonExtractor:
    def extract(path, content_text) -> List[ImportOccurrence]:
        """Extracts imports using Python AST"""

# graph/extractors/js_ts.py (regex-based, fast)
class JsTsExtractor:
    def extract(path, content_text) -> List[ImportOccurrence]:
        """Extracts imports using regex patterns"""
```

### Configuration
```python
# config/patterns_loader.py
def load_patterns(project_root) -> Dict[str, Any]:
    """Returns defaults merged with .project-control/patterns.yaml"""

# config/graph_config.py
class GraphConfig:
    """Loads and validates .project-control/graph.config.yaml"""
```

## Configuration Files & Defaults

### User Patterns (`.project-control/patterns.yaml`)
```yaml
# Defaults defined in:
# - cli/router.py:DEFAULT_PATTERNS
# - config/patterns_loader.py:_DEFAULT_PATTERNS

writers: [scale, emissive, opacity, position]
entrypoints: [main.js, index.ts]
ignore_dirs: [.git, .project-control, node_modules, __pycache__]
extensions: [.py, .js, .ts, .md, .txt]
```

### Graph Config (`.project-control/graph.config.yaml`)
```yaml
# Defaults defined in config/graph_config.py

include_globs: ["**/*.js", "**/*.ts", "**/*.jsx", "**/*.tsx"]
exclude_globs: ["**/node_modules/**", "**/.project-control/**"]
entrypoints: ["main.js", "index.ts"]
alias: {"@/": "src/"}
orphan_allow_patterns: ["**/*.test.*", "**/*.spec.*"]
treat_dynamic_imports_as_edges: true
languages:
  js_ts:
    enabled: true
    include_exts: [".js", ".ts", ".jsx", ".tsx"]
  python:
    enabled: false
    include_exts: [".py"]
```

### Exit Codes
```python
# core/exit_codes.py
EXIT_OK = 0
EXIT_VALIDATION_ERROR = 2
```

## Data Flow & Workflows

### Full Analysis Workflow
```
1. pc init
   → Creates .project-control/
   → Creates .project-control/patterns.yaml
   → Adds .project-control/ to .gitignore

2. pc scan
   → scanner.py:scan_project()
   → Walks directory tree
   → Computes SHA256 for each file
   → Stores blobs in .project-control/content/<sha256>.blob
   → Saves snapshot.json with metadata

3. pc ghost
   → ghost.py:ghost() (PURE FUNCTION)
   → Calls each detector's analyze()
   → ContentStore provides file access
   → Returns 5 lists: orphans, legacy, duplicates, sessions, semantic
   → Writes .project-control/exports/ghost_candidates.md

4. pc graph build
   → graph/builder.py:GraphBuilder.build()
   → Collects nodes from snapshot (filtered by config)
   → Extracts imports (AST for Python, regex for JS/TS)
   → Resolves specifiers to file paths
   → Computes edges, metrics, entrypoints
   → Caches results in .project-control/out/

5. pc graph report
   → Uses cached graph if valid (snapshot + config hash match)
   → Generates markdown report
```

### Content Access Pattern
```python
# NEVER do this:
content = Path(path).read_text()  # ❌ Wrong

# ALWAYS do this:
from project_control.core.content_store import ContentStore

snapshot = load_snapshot(project_root)
content_store = ContentStore(snapshot, snapshot_path)
content = content_store.get_text(file_path)  # ✅ Correct
```

### Path Handling Pattern
```python
# ALWAYS use posix paths for storage/comparison
from pathlib import Path

path_str = Path(path).as_posix()  # ✅ Forward slashes

# NEVER store Windows backslashes
wrong = "src\\utils\\helpers.py"  # ❌
right = "src/utils/helpers.py"    # ✅
```

## Directory Structure Quick Reference

```
project_control/
├── pc.py                      # CLI entry point
├── __init__.py                # Package init (version defined here)
│
├── cli/                       # Command-line interface
│   ├── router.py              # Command dispatch
│   ├── graph_cmd.py           # Graph CLI commands
│   └── menu.py                # Interactive TUI
│
├── core/                      # CORE ANALYSIS LAYER
│   ├── ghost.py               # ★ CANONICAL PURE FUNCTION
│   ├── ghost_service.py       # Ghost execution service
│   ├── scanner.py             # Snapshot creation
│   ├── snapshot_service.py    # Snapshot I/O
│   ├── content_store.py       # ★ File content access layer
│   ├── exit_codes.py          # EXIT_OK=0, EXIT_VALIDATION_ERROR=2
│   ├── embedding_service.py   # Embedding computation
│   └── markdown_renderer.py   # Report rendering
│
├── analysis/                  # DETECTORS (all expose analyze())
│   ├── orphan_detector.py     # Files never referenced
│   ├── legacy_detector.py     # Outdated patterns
│   ├── session_detector.py    # Temp/session files
│   ├── duplicate_detector.py  # Identical names in different paths
│   └── semantic_detector.py   # Embedding-based outliers
│
├── graph/                     # GRAPH ENGINE
│   ├── builder.py             # Graph construction
│   ├── metrics.py             # Fan-in/out, cycles, depth
│   ├── trace.py               # Path tracing
│   ├── artifacts.py           # Output writing
│   ├── resolver.py            # Import resolution strategies
│   └── extractors/            # Language-specific import extraction
│       ├── base.py            # BaseExtractor protocol
│       ├── python_ast.py      # AST-based Python (accurate)
│       ├── js_ts.py           # Regex-based JS/TS (fast)
│       └── registry.py        # Extractor registration
│
├── config/                    # CONFIGURATION
│   ├── patterns_loader.py     # Loads .project-control/patterns.yaml
│   └── graph_config.py        # Loads .project-control/graph.config.yaml
│
├── services/                  # BUSINESS LOGIC
│   ├── graph_service.py       # Graph operations
│   ├── analyze_service.py     # Analysis orchestration
│   └── scan_service.py        # Scan orchestration
│
├── embedding/                 # EMBEDDING (optional, requires Ollama)
│   ├── chunker.py             # Code chunking
│   ├── embed_provider.py      # Ollama client
│   ├── index_builder.py       # FAISS index construction
│   └── search_engine.py       # Vector similarity search
│
├── experimental/              # NOT INTEGRATED (preserved code)
│   └── ghost_deep/            # Deep ghost analysis (NOT ACTIVE)
│
├── ui/                        # User interface state
├── utils/                     # Utilities
│   └── fs_helpers.py          # ripgrep wrapper
├── persistence/               # Data persistence
└── usecases/                  # Use case implementations (empty)
```

### Project Root Structure (after running)
```
your-project/
├── .project-control/          # All PROJECT_CONTROL data lives here
│   ├── snapshot.json          # File metadata (from pc scan)
│   ├── patterns.yaml          # User configuration
│   ├── graph.config.yaml      # Graph configuration (auto-created)
│   ├── status.yaml            # Tags and state
│   ├── content/               # Deduplicated file blobs
│   │   └── <sha256>.blob      # Content-addressable storage
│   ├── exports/               # Generated reports
│   │   ├── ghost_candidates.md
│   │   ├── checklist.md
│   │   ├── find_<symbol>.md
│   │   └── writers_report.md
│   ├── out/                   # Graph artifacts
│   │   ├── graph.snapshot.json
│   │   ├── graph.metrics.json
│   │   ├── graph.report.md
│   │   └── graph.trace.txt
│   └── embeddings/            # Embedding cache (optional)
│       └── <sha256>.json      # Cached embeddings
│
├── .gitignore                 # Auto-updated with .project-control/
└── ... (your code)
```

## Common Gotchas & Tips

### ❌ DON'T DO THIS
```python
# 1. Reading files directly after scan
content = Path(path).read_text()  # ❌ Use ContentStore

# 2. Using Windows paths
path = "src\\utils\\helpers.py"  # ❌ Use posix: "src/utils/helpers.py"

# 3. Forgetting to sort before JSON
data = {"files": files}  # ❌ May be non-deterministic
# Use: sorted(files, key=lambda f: f["path"])

# 4. Assuming ripgrep is installed
rg_output = run_rg(query)  # ❌ May return empty string if missing
# Check: if not rg_output: handle gracefully

# 5. Using experimental code
from project_control.experimental.ghost_deep import ...  # ❌ NOT INTEGRATED
```

### ✅ DO THIS INSTEAD
```python
# 1. Use ContentStore for file access
content_store = ContentStore(snapshot, snapshot_path)
content = content_store.get_text(path)  # ✅

# 2. Always convert to posix paths
path_str = Path(path).as_posix()  # ✅

# 3. Sort before serialization
files_sorted = sorted(files, key=lambda f: f["path"])  # ✅

# 4. Handle missing ripgrep gracefully
rg_output = run_rg(query)
if not rg_output:
    logger.warning("ripgrep not available, skipping...")  # ✅

# 5. Use core/ghost.py for ghost analysis
from project_control.core.ghost import ghost
result = ghost(snapshot, patterns, content_store)  # ✅
```

### Quick Tests
```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_ghost_graph_core.py

# Run specific test
pytest tests/test_ghost_graph_core.py::test_specific_function

# Run with coverage
pytest tests/ --cov=project_control --cov-report=term-missing

# Lint
flake8 project_control/

# Type check (non-blocking)
mypy project_control/ --ignore-missing-imports
```

### Version Syncing
Two places must stay in sync:
```python
# project_control/__init__.py
__version__ = "0.1.0"

# pyproject.toml
version = "0.1.0"  # Keep in sync with __init__.py
```

### Graph Caching
- Graph results cached in `.project-control/out/`
- Cache valid if: `snapshot_hash` AND `config_hash` match
- To force rebuild: delete `.project-control/out/` directory
- Changing `graph.config.yaml` triggers rebuild (config hash changes)

### Python vs JS Resolution
- `PythonResolver`: module paths → file paths (e.g., `utils.helpers` → `utils/helpers.py`)
- `SpecifierResolver`: specifier strings → file paths with extension/index resolution (e.g., `./utils` → `utils/index.ts`)
- These are DIFFERENT classes with DIFFERENT logic

## Quick Reference: Key Patterns

### Detector Pattern (for adding new detectors)
```python
# analysis/new_detector.py
from typing import Any, Dict, List
from project_control.core.content_store import ContentStore

def analyze(snapshot: Dict[str, Any], patterns: Dict[str, Any], content_store: ContentStore) -> List[Any]:
    """Return list of findings."""
    findings = []
    for file_entry in snapshot.get("files", []):
        # Use content_store for file access
        content = content_store.get_text(file_entry["path"])
        # Your detection logic here
        if condition:
            findings.append({"path": file_entry["path"], ...})
    return findings

# Then add to core/ghost.py
from project_control.analysis import new_detector

def ghost(...):
    return {
        # ... existing detectors
        "new_category": _run_detector(new_detector, snapshot, patterns, content_store),
    }
```

### Extractor Pattern (for adding new languages)
```python
# graph/extractors/new_lang.py
from typing import List
from graph.extractors.base import BaseExtractor, ImportOccurrence

class NewLangExtractor(BaseExtractor):
    def extract(self, path: str, content_text: str) -> List[ImportOccurrence]:
        """Extract imports from code."""
        # Your extraction logic here
        return [
            ImportOccurrence(specifier="...", kind="import", line=1, lineText="..."),
        ]

# Register in graph/extractors/registry.py
from .new_lang import NewLangExtractor
# Add to build_registry() return dict
```

## Remember This

1. **Always use ContentStore** after scan - never read files directly
2. **Always use posix paths** (forward slashes) for storage/comparison
3. **core/ghost.py is THE SOURCE OF TRUTH** for ghost analysis
4. **experimental/ is NOT INTEGRATED** - don't use it
5. **Sort before serializing** to ensure determinism
6. **Version in two places** - keep `__init__.py` and `pyproject.toml` in sync
7. **Ripgrep is optional** - handle gracefully if missing
8. **Graph caches on hash** - delete `.project-control/out/` to force rebuild
9. **Exit codes: OK=0, VALIDATION_ERROR=2**
10. **Python uses AST, JS/TS uses regex** for import extraction
