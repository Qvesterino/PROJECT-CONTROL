# AGENTS.md

This document provides essential context for AI agents working on the PROJECT_CONTROL codebase.

## Project Overview

PROJECT_CONTROL is a deterministic architectural analysis engine for codebases. It performs static analysis to find dead code, build dependency graphs, and understand code structure through:
- **Snapshot System**: Content-addressable file storage with SHA256 hashing
- **Ghost Analysis**: Detects orphans, legacy code, sessions, duplicates, and semantic outliers
- **Graph Engine**: Builds import dependency graphs for Python and JS/TS projects

The tool is built with Python 3.10+ and follows strict principles of determinism and purity.

## Essential Commands

### Development
```bash
# Install in development mode
pip install -e .

# Install with embedding support (optional)
pip install -e ".[embedding]"

# Install development dependencies
pip install pytest pytest-cov flake8 mypy
```

### Testing
```bash
# Run all tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=project_control --cov-report=term-missing

# Run specific test file
pytest tests/test_ghost_graph_core.py

# Run specific test
pytest tests/test_ghost_graph_core.py::test_specific_function
```

### Linting & Type Checking
```bash
# Lint with flake8
flake8 project_control/

# Type check with mypy (non-blocking)
mypy project_control/ --ignore-missing-imports

# Run all quality checks
flake8 project_control/ && mypy project_control/ --ignore-missing-imports && pytest tests/
```

### Project-Specific Commands
```bash
# Test the CLI tool locally
python -m project_control.pc --help

# Run the tool on itself (for testing)
cd D:/PROJECT_CONTROL
pc scan
pc ghost
pc graph build
```

## Architecture Overview

### Core Data Flow
```
CLI (pc.py)
  → Router (cli/router.py)
    → Services (services/*)
      → Core Layer (core/*)
        → Analysis Detectors (analysis/*)
        → Graph Engine (graph/*)
```

### Key Components

**Snapshot System** (`core/scanner.py`, `core/snapshot_service.py`, `core/content_store.py`)
- Walks directory tree, computes SHA256 hashes, stores deduplicated content blobs
- Snapshot metadata in `.project-control/snapshot.json`
- Content blobs in `.project-control/content/<sha256>.blob`
- **Critical**: ContentStore provides filesystem-independent content access - all file reads should go through it, not direct filesystem access

**Ghost Analysis** (`core/ghost.py`, `core/ghost_service.py`)
- `core/ghost.py` is the **canonical pure function** - takes `(snapshot, patterns, content_store)`, returns dict with exactly 5 keys: `orphans`, `legacy`, `duplicates`, `sessions`, `semantic`
- This module is the only source of truth for ghost analysis
- Does NOT contain deep/anomaly/drift logic - those belong in `experimental/`
- Detectors in `analysis/` are called via `_run_detector()` which looks for an `analyze()` function

**Graph Engine** (`graph/builder.py`, `graph/metrics.py`, `graph/trace.py`)
- Builds import dependency graphs from snapshot
- Uses extractor pattern for language-specific import parsing:
  - `graph/extractors/python_ast.py`: AST-based Python import extraction
  - `graph/extractors/js_ts.py`: Regex-based JS/TS import extraction
  - `graph/extractors/base.py`: Protocol interface `BaseExtractor`
- Resolves specifiers using strategy pattern (`graph/resolver.py`)
- Computes metrics: fan-in/out, depth, cycles (Tarjan SCC), orphan candidates
- Caches results based on snapshot hash - rebuilds only when files change

**CLI Layer** (`cli/router.py`, `cli/graph_cmd.py`, `pc.py`)
- `pc.py`: Entry point, builds argparse parser, calls `dispatch()`
- `router.py`: Command dispatch to service functions
- Commands: `init`, `scan`, `ghost`, `graph build/report/trace`, `find`, `writers`, `embed build/rebuild/search`, `ui`

### Directory Structure
```
project_control/
├── pc.py                      # CLI entrypoint
├── cli/                       # Command-line interface
├── core/                      # Core services (ghost, scanner, snapshot, content_store)
├── analysis/                  # Analysis detectors (orphan, legacy, session, duplicate, semantic)
├── graph/                     # Import graph engine
│   └── extractors/            # Language-specific import extractors
├── embedding/                 # Semantic embedding system (optional, requires Ollama)
├── experimental/              # Experimental features (preserved but not integrated)
├── config/                    # Configuration loading
├── services/                  # Business logic services
├── persistence/               # Data persistence layer
├── ui/                        # User interface components
├── utils/                     # Utility functions (e.g., fs_helpers.py with ripgrep wrapper)
└── usecases/                  # Use case implementations (currently empty)
```

## Configuration Management

### User Configuration (`.project-control/patterns.yaml`)
Loaded by `config/patterns_loader.py` with defaults:
```yaml
writers: [scale, emissive, opacity, position]
entrypoints: [main.js, index.ts]
ignore_dirs: [.git, .project-control, node_modules, __pycache__]
extensions: [.py, .js, .ts, .md, .txt]
```

### Graph Configuration (`.project-control/graph.config.yaml`)
Loaded by `config/graph_config.py`:
```yaml
include_globs: ["**/*.js", "**/*.ts", ...]
exclude_globs: ["**/node_modules/**", ...]
entrypoints: ["main.js", "index.ts"]
alias: {"@/": "src/"}
orphan_allow_patterns: ["**/*.test.*", ...]
treat_dynamic_imports_as_edges: true
languages:
  js_ts:
    enabled: true
    include_exts: [".js", ".ts", ...]
  python:
    enabled: false
    include_exts: [".py"]
```

## Code Patterns & Conventions

### Pure Functions
- `core/ghost.py` is intentionally a pure function with no side effects
- All analysis detectors (`analysis/*.py`) expose an `analyze()` function
- Prefer pure functions over classes where possible

### Path Handling
- **Always use posix paths** (forward slashes) for all path storage and comparison
- Use `Path.as_posix()` when converting paths to strings
- Use `Path(path).as_posix()` for normalization
- The project uses `Path` objects internally but stores strings in JSON

### Content Access
- **Never read files directly** after scanning - always use `ContentStore.get_text(path)`
- ContentStore looks up SHA256 from snapshot and reads from blob storage
- This makes the codebase filesystem-independent after the scan

### Language-Specific Logic
- Import extraction uses the Extractor pattern: implement `BaseExtractor.extract(path, content_text)`
- Register extractors in `graph/extractors/registry.py`
- Return `ImportOccurrence` dataclass with: `specifier`, `kind`, `line`, `lineText`

### Error Handling
- Most functions log warnings but continue (e.g., scanner ignores unreadable files)
- Return empty lists/dicts rather than raising exceptions when possible
- Use `try/except` around file operations with `OSError`, `IOError`
- Check `exit_codes.py` for standard exit codes: `EXIT_OK=0`, `EXIT_VALIDATION_ERROR=2`

### Testing Patterns
- Tests use both `unittest.TestCase` and `pytest`
- Use `tempfile.TemporaryDirectory()` for filesystem tests
- Tests often create minimal snapshots and content stores for isolation
- See `tests/test_graph_core.py` for graph testing patterns
- See `tests/test_ghost_graph_core.py` for ghost core testing patterns

### Type Hints
- Use `from __future__ import annotations` at the top of all files
- Use `TypedDict` for structured data (e.g., `FileEntry`, `Snapshot`)
- Use `dataclass(frozen=True)` for immutable data structures
- Use `Protocol` for interfaces (e.g., `BaseExtractor`)

## Important Gotchas

### Ripgrep Dependency
- The `utils/fs_helpers.py` module wraps `ripgrep (rg)` for symbol search
- `run_rg()` function gracefully handles missing `rg` (returns empty string, logs warning)
- Tests that use ripgrep may fail if `rg` is not installed on the system

### Content Store Initialization
- ContentStore requires both the snapshot dict AND the path to `snapshot.json`
- It derives the content directory path from the snapshot path: `snapshot_path.parent / "content"`
- Always pass the correct snapshot path or content lookups will fail

### Graph Caching
- Graph results are cached based on snapshot hash and config hash
- To force rebuild, delete `.project-control/out/` directory
- Changes to graph config alone will trigger rebuild if config hash changes

### Python vs JS Resolution
- `PythonResolver` and `SpecifierResolver` are different classes with different resolution logic
- Python: module paths → file paths (e.g., `utils.helpers` → `utils/helpers.py`)
- JS/TS: specifier strings → file paths with extension/index resolution (e.g., `./utils` → `utils/index.ts`)

### Experimental Code
- The `experimental/` directory contains preserved deep ghost code that is **not integrated** into the main codebase
- Do not import or use experimental code in core features
- This is legacy/preserved code that may be removed in the future

### Version Syncing
- Version is defined in two places that must stay in sync:
  - `project_control/__init__.py`: `__version__ = "0.1.0"`
  - `pyproject.toml`: `version = "0.1.0"` (comment: "Keep in sync with project_control/__init__.py")

### Determinism Requirements
- The project emphasizes deterministic output
- Always sort lists/dicts before serialization (use `sorted()` with consistent keys)
- Use SHA256 hashing for content deduplication
- Graph nodes are assigned sequential IDs starting from 1
- All graph operations should produce the same output given the same input

### Language Support
- Python import extraction uses `ast` module (accurate but slower)
- JS/TS import extraction uses regex (fast but less accurate)
- New language support requires:
  1. Extractor implementation in `graph/extractors/`
  2. Registration in `graph/extractors/registry.py`
  3. Resolver strategy in `graph/resolver.py`
  4. Configuration in `graph_config.py` defaults

## Entry Points for Common Tasks

### Adding a New Ghost Detector
1. Create file in `analysis/` (e.g., `analysis/new_detector.py`)
2. Implement `analyze(snapshot, patterns, content_store)` function that returns a list
3. Import in `core/ghost.py` and add to the return dict
4. Add tests in `tests/test_*_detector.py`

### Adding a New CLI Command
1. Add subparser in `pc.py:build_parser()`
2. Add handler function in `cli/router.py`
3. Add dispatch case in `cli/router.py:dispatch()`
4. Update documentation in `README.md`

### Adding a New Language to Graph Engine
1. Create extractor in `graph/extractors/new_lang.py` implementing `BaseExtractor`
2. Register in `graph/extractors/registry.py:build_registry()`
3. Add resolver strategy in `graph/resolver.py` if needed
4. Add to defaults in `config/graph_config.py:DEFAULT_LANGUAGES`
5. Add tests in `tests/`

### Modifying Graph Metrics
1. Edit `graph/metrics.py:compute_metrics()`
2. Ensure result dict is serializable to JSON
3. Add tests in `tests/test_graph_core.py`
4. Update report rendering in `graph/artifacts.py` if needed

## CI/CD Notes

- GitHub Actions runs on Python 3.10, 3.11, 3.12
- CI runs: `pytest --cov`, `flake8`, `mypy`
- mypy failures do NOT block CI (runs with `|| true`)
- Coverage is uploaded to Codecov but does not block CI
- See `.github/workflows/ci.yml` for full pipeline

## External Dependencies

### Required
- `pyyaml>=6.0`: Configuration file parsing
- `requests>=2.31.0`: HTTP client (likely for future API features)
- `ripgrep (rg)`: Symbol search and orphan detection (system binary, not pip package)

### Optional (embedding support)
- `ollama>=0.1.0`: Local LLM server for embeddings
- `faiss-cpu>=1.7.0`: Vector similarity search
- `numpy>=1.24.0`: Numerical operations
- Requires running Ollama server: `ollama serve` and `ollama pull qwen3-embedding:8b`

## File Naming Conventions

- Test files: `test_<module_name>.py` in `tests/` directory
- Detectors: `<detector_type>_detector.py` in `analysis/` directory
- Extractors: `<language>.py` in `graph/extractors/` directory
- Services: `<feature>_service.py` in `core/` or `services/` directory
- CLI commands: `<feature>_cmd.py` in `cli/` directory

## Common Pitfalls

1. **Reading files directly after scan**: Always use ContentStore
2. **Using Windows paths**: Always convert to posix with `Path.as_posix()`
3. **Modifying experimental code**: Don't - it's not integrated
4. **Forgetting to sort lists before JSON serialization**: Causes non-deterministic output
5. **Not handling missing ripgrep**: `run_rg()` returns empty string, not error
6. **Confusing Python and JS resolvers**: They're separate classes with different logic
7. **Modifying ghost.py signature**: Must keep it as pure function with exactly 3 params
8. **Forgetting to update version**: Sync `__init__.py` and `pyproject.toml`
