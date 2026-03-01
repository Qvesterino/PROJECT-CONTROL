# PROJECT CONTROL - Architectural Capability Audit Report

**Version:** 1.3  
**Date:** 2026-02-14  
**Scope:** Full architectural analysis of PROJECT CONTROL codebase

---

## Executive Summary

PROJECT CONTROL is a static code analysis tool for detecting unused code, duplicates, and structural issues in JavaScript, TypeScript, and Python projects. It uses a snapshot-based approach combined with multiple detectors to identify "ghost" files that may be dead code.

The architecture is well-structured with clear separation between CLI, services, core logic, and analysis modules. It is deterministic, modular, and production-ready for its current scope, though it has limitations in areas like incremental analysis, semantic understanding, and extensibility.

---

## 1️⃣ CLI Surface (pc.py)

### Available Commands

| Command | Purpose | Required Snapshot |
|---------|---------|-------------------|
| `init` | Initialize .project-control directory with default config | No |
| `scan` | Create file inventory snapshot with hashes | No |
| `checklist` | Generate markdown checklist of all indexed files | Yes |
| `find <symbol>` | Search for symbol usage via ripgrep | No |
| `ghost` | Run ghost detection analysis | Yes |
| `writers` | Search for writer pattern usage | No |

### Command Flags

#### `ghost` Command Flags
- `--deep` - Enable import graph analysis (slow, requires parsing JS/TS files)
- `--stats` - Print statistics only, skip markdown report generation
- `--tree-only` - Write only tree view to import_graph_orphans.md (requires --deep)
- `--mode` - Detection mode: `strict` (no ignore patterns) or `pragmatic` (default, apply ignore patterns)
- `--max-high <int>` - Fail if HIGH severity count exceeds value (default: -1 = no limit)
- `--max-medium <int>` - Fail if MEDIUM severity count exceeds value (default: -1 = no limit)
- `--max-low <int>` - Fail if LOW severity count exceeds value (default: -1 = no limit)
- `--max-info <int>` - Fail if INFO severity count exceeds value (default: -1 = no limit)

### Command Behavior

**init**
- Creates `.project-control/` directory
- Creates `patterns.yaml` with default configuration
- Creates `status.yaml` with empty tags structure
- Idempotent - safe to run multiple times

**scan**
- Walks project directory tree
- Computes SHA256 hash for each file
- Applies ignore_dirs and extensions filters from patterns.yaml
- Writes snapshot to `.project-control/snapshot.json`
- Outputs file count to stdout

**checklist**
- Requires existing snapshot
- Generates `.project-control/exports/checklist.md`
- Lists all indexed files as markdown checkboxes
- Simple file inventory report

**find**
- Executes ripgrep (rg) search for symbol
- Writes results to `.project-control/exports/find_<symbol>.md`
- Includes line numbers via ripgrep
- No dependency on snapshot

**ghost**
- Requires existing snapshot
- Runs all detectors: orphans, legacy, session, duplicates
- Optionally runs import graph detector with --deep flag
- Generates reports in `.project-control/exports/`
- Can fail with exit code 2 if limits exceeded
- --stats mode: prints counts to stdout, no file output

**writers**
- Searches for writer patterns defined in patterns.yaml
- Uses ripgrep for each pattern
- Generates `.project-control/exports/writers_report.md`

### Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 2 | Ghost limits exceeded (max-high/medium/low/info) |
| Other | Unhandled exception (Python default) |

### Error Handling Strategy

- **Snapshot missing**: `FileNotFoundError` with message "Run 'pc scan' first."
- **Limit violation**: Explicit exit with code 2 and descriptive message
- **Ripgrep not found**: Logged warning, returns empty string (graceful degradation)
- **Invalid YAML**: Falls back to default patterns with debug logging
- **File read errors**: Silently skipped during import graph parsing

### Orchestration vs Business Logic

**CLI Layer (pc.py)**
- Argument parsing and validation
- Directory management (.project-control creation)
- Command routing
- User-facing output/messages

**Service Layer (ghost_service.py, snapshot_service.py)**
- Business logic orchestration
- Report generation coordination
- Persistence management
- Threshold validation

**Analysis Layer (analysis/*)**
- Pure detection logic
- No I/O operations
- Testable in isolation

**Separation Score: 4/5** - Clean separation, though some CLI concerns (directory creation) leak into command handlers.

---

## 2️⃣ Snapshot Layer

### Architecture

The snapshot layer consists of two modules:

- `core/scanner.py` - File scanning and hashing logic
- `core/snapshot_service.py` - Persistence and metadata management

### Snapshot Schema

```json
{
  "snapshot_version": 1,
  "snapshot_id": "2026-02-14T20-00-00__a1b2c3",
  "generated_at": "2026-02-14T20:00:00+00:00",
  "file_count": 150,
  "files": [
    {
      "path": "src/main.py",
      "size": 1024,
      "modified": "2026-02-14T19:30:00+00:00",
      "sha256": "abc123def456..."
    }
  ]
}
```

### FileEntry Structure

| Field | Type | Description |
|-------|------|-------------|
| path | string | Relative path from project root |
| size | int | File size in bytes |
| modified | string | ISO 8601 timestamp (UTC) |
| sha256 | string | SHA256 hex digest of file contents |

### Snapshot Version Usage

- **Current version:** 1
- **Purpose:** Schema versioning for future compatibility
- **Usage:** Currently informational only, no migration logic
- **Future:** Could be used for schema evolution

### Snapshot ID Generation

**Format:** `{timestamp}__{hash_short}`

**Example:** `2026-02-14T20-00-00__a1b2c3`

**Components:**
- Timestamp: `YYYY-MM-DDTHH-MM-SS` format (UTC)
- Hash: First 6 characters of SHA256(timestamp + timezone)

**Purpose:** Unique identifier for each snapshot run, useful for tracking history if expanded.

### SHA256 Handling

**Algorithm:** SHA-256 cryptographic hash

**Implementation:**
```python
def file_sha256(path: Path) -> str:
    hasher = sha256()
    with path.open("rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()
```

**Chunk size:** 8192 bytes (8KB) - balances memory and I/O

**Purpose:** Content integrity verification, duplicate detection (not currently used), potential diffing

### File Hashing Logic

- **Streaming approach:** Reads in 8KB chunks
- **Binary mode:** Opens files as binary for consistency
- **Error handling:** No explicit error handling (propagates exceptions)

### Timestamp Format

**Format:** ISO 8601 with timezone

**Example:** `2026-02-14T19:30:00+00:00`

**Components:**
- `datetime.fromtimestamp(stat.st_mtime, timezone.utc)` - converts filesystem timestamp to UTC
- `.isoformat()` - converts to ISO 8601 string

### snapshot.json Location

**Path:** `<project_root>/.project-control/snapshot.json`

**Required for:** checklist, ghost commands

### When snapshot.json is Required

| Command | Required | Behavior if Missing |
|---------|----------|---------------------|
| init | No | N/A |
| scan | No | Overwrites existing |
| checklist | Yes | Error "Run 'pc scan' first." |
| find | No | N/A |
| ghost | Yes | Error "Run 'pc scan' first." |
| writers | No | N/A |

### Failure Behavior

**Scan failures:**
- Permission denied: Propagates as Python exception
- File locked: Propagates as Python exception
- Disk full: Propagates as Python exception

**Load failures:**
- Missing snapshot.json: Raises `FileNotFoundError`
- Invalid JSON: Propagates `json.JSONDecodeError`
- Missing fields: Returns empty list via `get("files", [])`

### Idempotency

**Scanning:**
- **Not idempotent:** Each scan generates new snapshot_id and generated_at
- **File content:** Deterministic - same content produces same file entries
- **File order:** OS-dependent (os.walk yields directory entries in arbitrary order)

**Snapshot state:**
- **Overwrites:** Each scan overwrites snapshot.json completely
- **No append:** No history or incremental updates

### Determinism Assessment

**Deterministic aspects:**
- File content hash: Always produces same SHA256 for same content
- File metadata: Deterministic for same filesystem state
- Timestamp format: Consistent ISO 8601 format

**Non-deterministic aspects:**
- File order: os.walk order is OS-dependent
- snapshot_id: Contains timestamp, different for each run
- generated_at: Always current time

### Stability Across Runs

**Same project state:**
- File entries: Identical (except order)
- Hashes: Identical
- Counts: Identical

**Changed project state:**
- Added files: Detected and added
- Modified files: Hash changes, timestamp updates
- Deleted files: Not detected until re-scan

### Diffing Suitability

**For snapshot comparison:**
- ✅ SHA256 hashes enable content change detection
- ✅ File paths enable structural comparison
- ❌ No incremental diff mode implemented
- ❌ No change tracking between runs

**For import graph diffing:**
- ❌ No snapshot history storage
- ❌ No diff capability

### Embedding Readiness

**Snapshot schema suitability for vector indexing:**
- ✅ SHA256 provides natural cache keys
- ✅ File paths enable context association
- ✅ File metadata (size, type) useful for filtering
- ❌ No semantic content stored (only hashes)
- ❌ No file content stored (would need extension)

**Recommendation:** Schema is suitable for embedding integration with minimal changes:
1. Add embedding vectors to FileEntry (optional)
2. Use SHA256 as cache key to avoid re-embedding
3. Store embeddings separately or in document store

---

## 3️⃣ Ghost Layer

### Architecture

The ghost layer consists of two modules:

- `core/ghost.py` - Detector orchestration and protocol definition
- `core/ghost_service.py` - Execution flow and report writing

### Command Flow

**Standard mode (no --deep):**
```
pc ghost
  └─> run_ghost()
      └─> analyze_ghost()
          ├─> orphan_detector.analyze()
          ├─> legacy_detector.analyze()
          ├─> session_detector.analyze()
          └─> duplicate_detector.analyze()
      └─> write_ghost_reports()
          └─> render_ghost_report()
              └─> markdown_renderer.render_ghost_report()
```

**Deep mode (--deep):**
```
pc ghost --deep
  └─> run_ghost()
      └─> analyze_ghost() with deep=True
          └─> import_graph_detector.detect_graph_orphans()
              ├─> import_parser.extract_imports() for each file
              ├─> Build adjacency graph
              └─> DFS from entrypoints
      └─> write_ghost_reports()
          ├─> Generate import_graph_orphans.md
          │   ├─> Flat list (unless --tree-only)
          │   └─> Tree view (tree_renderer.render_tree())
          └─> Generate ghost_candidates.md
              └─> render_ghost_report()
```

### Deep Mode Behavior

**Triggers:** `--deep` flag

**Actions:**
1. Builds static import graph from JS/TS files
2. Parses all JS/TS files with import_parser
3. Creates adjacency map of file dependencies
4. Performs DFS from configured entrypoints
5. Identifies files unreachable from entrypoints

**Time complexity:** O(F × I) where F = number of files, I = average imports per file

**Slow for:** Large codebases (1000+ files)

**Use cases:**
- Production dead code detection
- Refactoring planning
- Codebase health assessment

### Tree-Only Mode Behavior

**Triggers:** `--deep --tree-only`

**Actions:**
1. Runs deep import graph analysis
2. Generates only tree view in import_graph_orphans.md
3. Skips flat list section

**Output format:** ASCII tree using tree_renderer

**Use cases:** Visual dependency inspection, code review

### Writing Logic

#### ghost_candidates.md

**Generated by:** `markdown_renderer.render_ghost_report()`

**Always generated:** Yes (unless --stats mode)

**Structure:**
```markdown
# Smart Ghost Report

## Summary
- Import graph orphans (CRITICAL): N
- Orphans (HIGH): N
- Legacy snippets (MEDIUM): N
- Session files (LOW): N
- Duplicates (INFO): N

### Orphans [HIGH]
- path/to/file1.py
- path/to/file2.py

### Legacy snippets [MEDIUM]
- ...

### Session files [LOW]
- ...

### Duplicates [INFO]
- ('path/to/file1.js', 'other/path/to/file1.js')
```

#### import_graph_orphans.md

**Generated by:** `ghost_service.write_ghost_reports()`

**Generated only when:** `--deep` flag present

**Structure (full mode):**
```markdown
# Import Graph Orphans

## Legend
(Directory tree based on import graph reachability)

# NOTE
This report is static-import based.
Dynamic runtime wiring (FrameScheduler, registries, side-effects) is not detected.

- src/orphan1.js
- src/orphan2.js

## Tree View

Total import graph orphans: N

src/
├── orphan1.js
└── subdir/
    └── orphan2.js
```

**Structure (tree-only mode):**
```markdown
# Import Graph Orphans

## Legend
(Directory tree based on import graph reachability)

# NOTE
This report is static-import based.
Dynamic runtime wiring (FrameScheduler, registries, side-effects) is not detected.

## Tree View

Total import graph orphans: N

src/
├── orphan1.js
└── subdir/
    └── orphan2.js
```

### render_tree Implementation

**Module:** `analysis/tree_renderer.py`

**Algorithm:**
1. Builds nested dict from slash-delimited paths
2. Walks tree depth-first
3. Generates ASCII art connectors

**Connectors:**
- `└── ` for last child
- `├── ` for non-last child
- `│   ` for continuation
- `    ` for no continuation

**Features:**
- Handles both forward and backslashes
- Sorts alphabetically
- Appends `/` to directories

**Example:**
```
src/
├── main.js
├── utils/
│   ├── helper.js
│   └── other.js
└── orphan.js
```

### Stats Computation

**Calculated in:** `ghost_service.run_ghost()`

**Metrics:**
- `orphans`: Count of orphan_detector results
- `legacy`: Count of legacy_detector results
- `session`: Count of session_detector results
- `duplicates`: Count of duplicate_detector pairs
- `graph_orphans`: Count of import_graph_detector results (if deep mode)

**Usage:**
- --stats mode: Printed to stdout
- Summary section in ghost_candidates.md
- Limit validation against max-* flags

### Separation Between Analysis vs Rendering

**Analysis (core/ghost.py):**
- Pure data transformation
- No I/O
- Returns dict of results

**Rendering (core/markdown_renderer.py, analysis/tree_renderer.py):**
- Converts analysis data to text/markdown
- Writes to files
- Handles presentation

**Separation Score: 5/5** - Excellent separation. Analysis produces data, rendering consumes it.

### Separation Between Detection vs Reporting

**Detection (analysis/*_detector.py):**
- Domain-specific logic
- No awareness of output format
- Returns simple data structures

**Reporting (core/markdown_renderer.py):**
- Format-specific logic
- No detection logic
- Consumes detection results

**Separation Score: 5/5** - Clean separation. Each detector is independent of reporting.

### Coupling with Snapshot

**Direct coupling:**
- All detectors require snapshot as input
- Snapshot provides file metadata for filtering
- Snapshot provides file list for analysis

**Coupling points:**
- File list iteration: `snapshot.get("files", [])`
- Path extraction: `file.get("path")`
- Extension filtering: `Path(path).suffix`

**Coupling Score: 3/5** - Moderate. Detectors depend on snapshot structure, but no circular dependencies. Could benefit from abstracted file interface.

### Extension Potential

**Adding new detectors:**
1. Create module in `analysis/`
2. Implement `analyze(snapshot, patterns) -> List[Any]` function
3. Register in `core/ghost.py` (add to result dict)
4. Add severity mapping in `core/markdown_renderer.py`

**Example:**
```python
# analysis/my_detector.py
def analyze(snapshot, patterns):
    results = []
    for file in snapshot.get("files", []):
        if some_condition(file):
            results.append(file["path"])
    return results

# core/ghost.py
result["my_detector"] = _run_detector(my_detector, snapshot, patterns)

# core/markdown_renderer.py
SEVERITY_MAP["my_detector"] = "MEDIUM"
```

**Extension points:**
- ✅ Detector protocol defined via typing
- ✅ Consistent interface across detectors
- ✅ No detector-to-detector dependencies
- ❌ No plugin system (requires code changes)
- ❌ No configuration-based detector registration

---

## 4️⃣ Detector Modules

### Overview

| Detector | File | Purpose | Output Type |
|----------|------|---------|-------------|
| orphan_detector | orphan_detector.py | Files not referenced via imports | List[str] |
| duplicate_detector | duplicate_detector.py | Files with same basename | List[Tuple[str, str]] |
| legacy_detector | legacy_detector.py | Files matching legacy patterns | List[str] |
| session_detector | session_detector.py | Files containing "session" | List[str] |
| import_graph_detector | import_graph_detector.py | Files unreachable from entrypoints | List[str] |

---

### Orphan Detector

**File:** `analysis/orphan_detector.py`

**Purpose:** Identify code files that do not appear to be referenced elsewhere via import statements.

**Input:**
- `snapshot`: Dict with "files" list containing FileEntry objects
- `patterns`: Dict with "entrypoints" list (files to exclude)

**Output:** `List[str]` - Relative file paths

**Algorithm:**
1. Filter files by extension (`.js`, `.ts`, `.py`)
2. Exclude configured entrypoints
3. For each file:
   - Extract filename without extension
   - Generate reference patterns (import, from, require)
   - Search codebase via ripgrep for each pattern
   - If no matches, mark as orphan

**Reference patterns:**
```python
fr"import .*{escaped_name}"
fr"from .*{escaped_name}"
fr"require\(.*{escaped_name}"
```

**Example:**
```
File: src/helper.py
Name: helper
Patterns searched:
- import .*helper
- from .*helper
- require\(.*helper\)
```

**False positives:**
- Files loaded dynamically
- Files referenced by string paths
- Files in configuration files
- Files in HTML/template references

**Integration into ghost flow:**
- Always runs in standard mode
- Results sorted alphabetically
- Severity: HIGH

**Dependency on snapshot:**
- Requires file list for iteration
- Requires file paths for filtering

**Extensibility:**
- ✅ Easy to add new reference patterns
- ✅ Language-agnostic approach
- ❌ Hardcoded extension list
- ❌ No configuration for reference patterns

---

### Duplicate Detector

**File:** `analysis/duplicate_detector.py`

**Purpose:** Detect files sharing the same base name but located in different directories.

**Input:**
- `snapshot`: Dict with "files" list containing FileEntry objects
- `patterns`: Dict (unused)

**Output:** `List[Tuple[str, str]]` - Pairs of duplicate file paths

**Algorithm:**
1. Extract filename (basename) from each path
2. Group files by basename (case-insensitive)
3. For groups with ≥2 files, generate all pairs

**Example:**
```
Files:
- src/v1/helper.js
- src/v2/helper.js
- src/main.js

Buckets:
- helper.js: [src/v1/helper.js, src/v2/helper.js]
- main.js: [src/main.js]

Pairs:
- (src/v1/helper.js, src/v2/helper.js)
```

**Complexity:** O(n²) for duplicates, O(n) for bucketing

**Integration into ghost flow:**
- Always runs in standard mode
- Severity: INFO

**Dependency on snapshot:**
- Requires file list for iteration
- Requires file paths for basename extraction

**Extensibility:**
- ✅ Simple algorithm
- ❌ No content comparison (only names)
- ❌ No threshold for similarity
- ❌ No fuzzy matching

---

### Legacy Detector

**File:** `analysis/legacy_detector.py`

**Purpose:** Identify legacy files by filename patterns configured in patterns.yaml.

**Input:**
- `snapshot`: Dict with "files" list containing FileEntry objects
- `patterns`: Dict with "legacy_patterns" list

**Output:** `List[str]` - Relative file paths

**Algorithm:**
1. Normalize legacy patterns (lowercase, trim)
2. For each file:
   - Lowercase path
   - Check if any pattern is in path
   - If match, add to results

**Pattern matching:**
- Substring matching (case-insensitive)
- Matches anywhere in path (directory or filename)

**Example:**
```
Patterns: ["old", "deprecated", "v1"]
Files:
- src/old_helper.py ✅
- src/deprecated/feature.js ✅
- src/new_feature.py ❌
- src/v2/api.py ✅ (contains "v1" as substring of "v2") ⚠️
```

**False positives:**
- Patterns that are substrings of other words
- Non-legacy files with pattern in directory name

**Integration into ghost flow:**
- Always runs in standard mode
- Severity: MEDIUM

**Dependency on snapshot:**
- Requires file list for iteration
- Requires file paths for pattern matching

**Extensibility:**
- ✅ Configuration-driven patterns
- ✅ Easy to add/remove patterns
- ❌ No regex support
- ❌ No pattern validation
- ❌ Substring matching can be imprecise

---

### Session Detector

**File:** `analysis/session_detector.py`

**Purpose:** Return any files whose names include 'session' (case-insensitive).

**Input:**
- `snapshot`: Dict with "files" list containing FileEntry objects
- `patterns`: Dict (unused)

**Output:** `List[str]` - Relative file paths

**Algorithm:**
1. For each file:
   - Lowercase path
   - Check if "session" is in path
   - If yes, add to results

**Example:**
```
Files:
- src/session_manager.py ✅
- src/user_session.js ✅
- src/main.py ❌
- src/SessionHandler.ts ✅
```

**Integration into ghost flow:**
- Always runs in standard mode
- Severity: LOW

**Dependency on snapshot:**
- Requires file list for iteration
- Requires file paths for string matching

**Extensibility:**
- ❌ Hardcoded "session" keyword
- ❌ No configuration
- ❌ Not generalizable

---

### Import Graph Detector

**File:** `analysis/import_graph_detector.py`

**Purpose:** Build a static import graph starting from entrypoints and return JS/TS files not reachable from entrypoints.

**Input:**
- `snapshot`: Dict with "files" list containing FileEntry objects
- `patterns`: Dict with "entrypoints" and "graph_ignore_patterns" lists
- `apply_ignore`: Bool (apply ignore patterns if True)

**Output:** `List[str]` - Relative file paths of unreachable files

**Algorithm:**
1. Filter JS/TS files (`.js`, `.ts`)
2. Apply ignore patterns if `apply_ignore=True`
3. Build adjacency graph:
   - Parse each file with `import_parser.extract_imports()`
   - Resolve relative imports to absolute paths
   - Add edges to graph
4. Perform DFS from each entrypoint
5. Identify files not in reachable set

**Import resolution:**
- Only resolves relative imports (starting with `.`)
- Handles implicit `.js`/`.ts` extensions
- Resolves parent directory references (`..`)

**Example:**
```
Entrypoints: ["src/main.js"]
Files:
- src/main.js
- src/helper.js
- src/utils/string.js
- src/unused.js

Graph:
main.js -> helper.js
helper.js -> utils/string.js

Reachable from main.js:
- main.js
- helper.js
- utils/string.js

Orphans:
- src/unused.js
```

**Pragmatic mode (apply_ignore=True):**
- Applies `graph_ignore_patterns` from patterns.yaml
- Useful for ignoring test files, examples, etc.

**Strict mode (apply_ignore=False):**
- No ignore patterns applied
- More thorough analysis

**Limitations:**
- ❌ No dynamic import detection (`import()`)
- ❌ No require.resolve detection
- ❌ No runtime wiring detection (FrameScheduler, registries)
- ❌ No module federation detection
- ❌ No re-export analysis (import { x } from './re-export')

**Integration into ghost flow:**
- Only runs when `--deep` flag is present
- Severity: CRITICAL

**Dependency on snapshot:**
- Requires file list for iteration
- Requires file paths for parsing

**Extensibility:**
- ✅ Pluggable import parser
- ✅ Configurable entrypoints
- ✅ Configurable ignore patterns
- ❌ No dynamic import support
- ❌ No module system abstraction (JS vs TS vs Python)

---

### Pattern Loader

**File:** `config/patterns_loader.py`

**Purpose:** Load configuration from patterns.yaml with fallback to defaults.

**Default patterns:**
```yaml
writers: ["scale", "emissive", "opacity", "position"]
entrypoints: ["main.js", "index.ts"]
ignore_dirs: [".git", ".project-control", "node_modules", "__pycache__"]
extensions: [".py", ".js", ".ts", ".md", ".txt"]
```

**Configuration file:** `.project-control/patterns.yaml`

**Available patterns:**
- `writers`: List of strings for writer search patterns
- `entrypoints`: List of entrypoint file paths
- `ignore_dirs`: List of directory names to ignore during scan
- `extensions`: List of file extensions to include
- `legacy_patterns`: List of legacy filename patterns (optional)
- `graph_ignore_patterns`: List of patterns for import graph ignore (optional)

**Error handling:**
- Missing file: Returns defaults
- Invalid YAML: Returns defaults with debug log
- Invalid structure: Merges with defaults

**Integration:** Used by all commands that need configuration

---

## 5️⃣ Rendering & Reporting Layer

### Architecture

**Modules:**
- `core/markdown_renderer.py` - Report generation
- `analysis/tree_renderer.py` - ASCII tree rendering

### Markdown Generation Strategy

**Function:** `markdown_renderer.render_ghost_report()`

**Process:**
1. Create report header ("# Smart Ghost Report")
2. Generate summary section with counts
3. For each section (orphans, legacy, session, duplicates):
   - Check severity mapping
   - Generate markdown list
   - Handle empty case with "_No entries found._"
4. Join with newlines
5. Write to file with UTF-8 encoding

**Section ordering:**
1. Import graph orphans (if include_graph=True)
2. Orphans
3. Legacy snippets
4. Session files
5. Duplicates

**Severity display:**
```
### Orphans [HIGH]

- path/to/file1.py
- path/to/file2.py
```

### Tree Rendering Strategy

**Function:** `tree_renderer.render_tree()`

**Algorithm:**
1. Build nested dict from paths:
   - Split path by `/` or `\`
   - Insert into tree hierarchy
2. Walk tree recursively:
   - For each node:
     - Determine if last child
     - Choose connector (└── or ├──)
     - Add to output
     - Recurse for children
3. Return joined lines

**Connector logic:**
- Last child: `└── ` followed by `    ` for children
- Non-last child: `├── ` followed by `│   ` for children

**Directory marking:**
- Append `/` if node has children
- No suffix for leaf nodes

**Example input:**
```
["src/main.js", "src/utils/helper.js", "src/utils/other.js", "readme.md"]
```

**Example output:**
```
readme.md
src/
├── main.js
└── utils/
    ├── helper.js
    └── other.js
```

### File Writing Strategy

**Functions:**
- `markdown_renderer.render_ghost_report()` - Uses `Path.write_text()`
- `markdown_renderer.render_writer_report()` - Uses `Path.write_text()`
- `ghost_service.write_ghost_reports()` - Uses `Path.write_text()`

**Strategy:**
1. Generate complete report string in memory
2. Use `Path.write_text()` with UTF-8 encoding
3. Overwrite existing file (no append)
4. Ensure trailing newline

**Advantages:**
- Atomic operation (single write)
- No partial writes
- Easy to test

**Disadvantages:**
- Large reports held in memory
- No streaming for very large reports

### Duplication Between Writers

**Ghost reports:**
- `ghost_candidates.md` - Standard ghost detection
- `import_graph_orphans.md` - Import graph analysis (deep mode only)

**Writer reports:**
- `writers_report.md` - Writer pattern usage
- `find_<symbol>.md` - Symbol search results
- `checklist.md` - File inventory checklist

**Duplication:**
- ❌ No shared code between report generation
- ❌ Similar structure but different implementations
- ⚠️ `render_ghost_report()` and `render_writer_report()` have similar patterns

**Refactoring opportunity:**
- Extract common report structure (header, sections, footer)
- Abstract section rendering
- Reduce code duplication

### Stats Mode

**Triggered by:** `--stats` flag on `ghost` command

**Behavior:**
1. Run all detectors as usual
2. Compute counts per section
3. Print counts to stdout
4. Skip file generation

**Output format:**
```
Ghost Stats
-----------
Import graph orphans (CRITICAL): 5
Orphans (HIGH): 12
Legacy snippets (MEDIUM): 3
Session files (LOW): 7
Duplicates (INFO): 2
```

**Use cases:**
- CI/CD pipelines (text output only)
- Quick health checks
- Integration with monitoring systems

### How --deep Alters Output

**Standard mode (no --deep):**
```
ghost_candidates.md
- Orphans (HIGH)
- Legacy snippets (MEDIUM)
- Session files (LOW)
- Duplicates (INFO)
```

**Deep mode (--deep):**
```
import_graph_orphans.md (NEW)
- Flat list of unreachable files
- ASCII tree view

ghost_candidates.md
- Import graph orphans (CRITICAL) (NEW in summary)
- Orphans (HIGH)
- Legacy snippets (MEDIUM)
- Session files (LOW)
- Duplicates (INFO)
```

**Deep + tree-only mode (--deep --tree-only):**
```
import_graph_orphans.md
- ASCII tree view only (no flat list)

ghost_candidates.md
- (Not generated)
```

---

## 6️⃣ Architecture Map

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                        CLI Layer                            │
│                      (pc.py)                                │
│  - Argument parsing                                          │
│  - Command routing                                           │
│  - Directory management                                      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Service Layer                          │
│  - ghost_service.py                                         │
│  - snapshot_service.py                                      │
│  - Writers analysis coordination                            │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┴────────────┐
        ▼                         ▼
┌──────────────────┐    ┌──────────────────┐
│   Core Layer     │    │   Core Layer     │
│ - ghost.py       │    │ - scanner.py     │
│ - import_parser  │    │ - snapshot.py    │
│ - writers.py     │    │ - markdown_*     │
└────────┬─────────┘    └──────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────┐
│                   Analysis Layer                           │
│  - orphan_detector.py                                       │
│  - duplicate_detector.py                                    │
│  - legacy_detector.py                                       │
│  - session_detector.py                                      │
│  - import_graph_detector.py                                 │
│  - tree_renderer.py                                         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      Utils Layer                            │
│  - fs_helpers.py (ripgrep wrapper)                          │
│  - patterns_loader.py                                       │
└─────────────────────────────────────────────────────────────┘
```

### Dependency Flow

**Scan flow:**
```
pc.py scan
  └─> snapshot_service.create_snapshot()
      └─> scanner.scan_project()
          └─> os.walk() + file hashing
  └─> snapshot_service.save_snapshot()
      └─> JSON write to .project-control/snapshot.json
```

**Ghost flow (standard):**
```
pc.py ghost
  └─> ghost_service.run_ghost()
      ├─> ghost_service.load_snapshot()
      ├─> ghost.analyze_ghost()
      │   ├─> orphan_detector.analyze()
      │   │   └─> fs_helpers.run_rg() [via orphan_detector]
      │   ├─> legacy_detector.analyze()
      │   ├─> session_detector.analyze()
      │   └─> duplicate_detector.analyze()
      └─> ghost_service.write_ghost_reports()
          └─> markdown_renderer.render_ghost_report()
              └─> Path.write_text()
```

**Ghost flow (deep):**
```
pc.py ghost --deep
  └─> ghost_service.run_ghost()
      ├─> ghost_service.load_snapshot()
      ├─> ghost.analyze_ghost(deep=True)
      │   └─> import_graph_detector.detect_graph_orphans()
      │       ├─> import_parser.extract_imports()
      │       │   └─> regex matching
      │       └─> Graph traversal (DFS)
      └─> ghost_service.write_ghost_reports()
          ├─> Write import_graph_orphans.md
          │   └─> tree_renderer.render_tree()
          └─> Write ghost_candidates.md
              └─> markdown_renderer.render_ghost_report()
```

### Separation of Concerns

| Layer | Responsibility | Dependencies |
|-------|---------------|--------------|
| CLI (pc.py) | User interface, argument parsing | Services |
| Services (ghost_service, snapshot_service) | Orchestration, persistence | Core, Analysis |
| Core (ghost, scanner, markdown) | Business logic interfaces | Analysis |
| Analysis (*_detector) | Domain-specific detection | Utils |
| Utils (fs_helpers, patterns_loader) | Low-level utilities | External tools |

**Separation Score: 4/5**
- Clear layer boundaries
- Minimal cross-layer coupling
- Service layer properly abstracts complexity
- Some tight coupling in CLI (directory creation mixed with command logic)

### Single Responsibility Violations

**Minor violations:**

1. **pc.py - Directory creation mixed with command logic**
   - `ensure_control_dirs()` called in multiple command functions
   - Could be extracted to initialization hook

2. **ghost_service.py - Report writing mixed with validation**
   - `write_ghost_reports()` handles both deep and standard modes
   - Could be split into separate functions

3. **orphan_detector.py - File filtering mixed with detection**
   - Extension filtering and entrypoint exclusion in detection logic
   - Could be pre-filtered before detection

**No major violations detected.**

### Circular Dependency Risks

**Potential circular dependencies:**

1. **ghost.py ↔ detectors**
   - ghost imports detector modules
   - Detectors do not import ghost
   - ✅ No circular dependency

2. **ghost_service.py ↔ markdown_renderer.py**
   - ghost_service imports markdown_renderer
   - markdown_renderer does not import ghost_service
   - ✅ No circular dependency

3. **import_graph_detector.py ↔ import_parser.py**
   - import_graph_detector imports import_parser
   - import_parser does not import import_graph_detector
   - ✅ No circular dependency

**Conclusion:** No circular dependencies detected. Dependency graph is acyclic.

---

## 7️⃣ Current Capabilities Summary

### Current System Capabilities

#### File Inventory
- **Full project scanning** with configurable ignore directories
- **File metadata collection**: path, size, modification timestamp
- **SHA256 hashing** for content integrity verification
- **Extension filtering** to include/exclude file types
- **Snapshot persistence** in `.project-control/snapshot.json`

#### Static Snapshot System
- **Deterministic file indexing** for consistent results
- **Timestamped snapshots** with unique IDs
- **JSON format** for easy parsing and version control
- **Incremental scan capability** (re-scan overwrites previous)
- **Schema versioning** (currently version 1)

#### Hash-Based File Tracking
- **SHA256 content hashing** for each file
- **Streaming hash computation** (8KB chunks) for memory efficiency
- **Hash-based duplicate detection** infrastructure (not fully utilized)
- **Content change detection** via hash comparison

#### Import Graph Orphan Detection (CRITICAL)
- **Static import graph construction** from JS/TS files
- **Entrypoint-based reachability analysis** (DFS traversal)
- **Relative import resolution** (`.`, `..` handling)
- **Extension implicit resolution** (`.js`, `.ts` auto-detection)
- **Strict vs Pragmatic modes** for ignore patterns
- **Tree visualization** of orphan files
- **ASCII tree rendering** with proper indentation

#### Orphan Detection (HIGH)
- **Import statement analysis** for JavaScript, TypeScript, Python
- **Multiple import patterns**: `import`, `from`, `require`
- **Ripgrep-powered searching** for code references
- **Entrypoint exclusion** to prevent false positives
- **Alphabetical sorting** of results

#### Duplicate Detection (INFO)
- **Basename-based duplicate identification**
- **Cross-directory duplicate detection**
- **Pair generation** for all duplicate combinations
- **Case-insensitive matching**

#### Pattern Detection (MEDIUM)
- **Configurable legacy patterns** in patterns.yaml
- **Substring matching** for filename patterns
- **Case-insensitive filtering**
- **Multiple pattern support**

#### Session File Detection (LOW)
- **Substring-based detection** for "session" keyword
- **Case-insensitive matching**
- **Path-wide matching** (filename and directory)

#### Tree Visualization
- **ASCII tree rendering** for path hierarchies
- **Proper connector formatting** (├──, └──, │)
- **Directory marking** with `/` suffix
- **Alphabetical sorting** at each level

#### CLI Filtering
- **Extension filtering** during scan
- **Directory ignore patterns** (`.git`, `node_modules`, etc.)
- **Entrypoint configuration** for exclusion
- **Graph ignore patterns** for deep analysis

#### Markdown Reporting
- **Structured report generation** with sections
- **Severity classification** (CRITICAL, HIGH, MEDIUM, LOW, INFO)
- **Summary statistics** with counts
- **Empty state handling** with "_No entries found._"
- **UTF-8 encoding** for international characters

#### Writer Pattern Analysis
- **Configurable writer patterns** for specific code patterns
- **Ripgrep-powered search** for each pattern
- **Markdown report generation** per pattern
- **Usage tracking** for codebase-wide patterns

#### Limit Enforcement
- **Configurable severity thresholds** (max-high, max-medium, max-low, max-info)
- **Exit code 2** on limit violation
- **Descriptive error messages** for CI/CD integration

#### Stats Mode
- **Statistics-only output** for CI/CD pipelines
- **Console output** without file generation
- **Per-section counts** with severity labels

#### Configuration Management
- **YAML-based configuration** in `.project-control/patterns.yaml`
- **Default configuration** with override capability
- **Graceful fallback** to defaults on load failure
- **Merged configuration** (defaults + user config)

---

## 8️⃣ Current Limitations

### No Semantic Embedding Layer

**Impact:** Limited understanding of code semantics

**Details:**
- No semantic analysis of code meaning
- No natural language understanding of comments/docs
- No code similarity detection beyond filenames
- No concept extraction or classification
- No semantic search capabilities

**Workarounds:** None currently available

---

### No Incremental Snapshot Diff Mode

**Impact:** Cannot track changes between snapshots

**Details:**
- Each scan overwrites previous snapshot
- No history of file changes
- No diff capability between snapshots
- Cannot identify added/modified/deleted files
- No change rate analysis

**Workarounds:** Manual comparison of snapshot.json files

---

### No Persistent History

**Impact:** Cannot analyze codebase evolution

**Details:**
- Only one snapshot stored at a time
- No historical trend analysis
- No audit trail of ghost evolution
- Cannot correlate ghost emergence with commits

**Workarounds:** External version control of snapshot.json

---

### No Plugin System

**Impact:** Cannot extend functionality without code changes

**Details:**
- No dynamic detector loading
- No third-party detector support
- Requires code modifications for new detectors
- No detector marketplace or ecosystem

**Workarounds:** Fork project and modify code

---

### No Configuration File (Full)

**Impact:** Limited configurability

**Details:**
- Configuration exists (patterns.yaml) but limited scope
- No per-project configuration beyond patterns
- No global configuration file
- No environment variable support
- No configuration validation

**Workarounds:** Edit patterns.yaml manually

---

### No Performance Profiling

**Impact:** Cannot identify bottlenecks

**Details:**
- No timing metrics
- No performance tracking
- Cannot measure detector execution time
- No profiling output

**Workarounds:** Manual timing with external tools

---

### No Concurrency

**Impact:** Slower execution on large codebases

**Details:**
- All operations are sequential
- No parallel file processing
- No concurrent detector execution
- Deep mode especially slow (1000+ files)

**Workarounds:** None currently available

---

### No Caching

**Impact:** Redundant computation on repeated runs

**Details:**
- No ripgrep result caching
- No import parse caching
- No hash caching across runs
- Re-computes everything on each run

**Workarounds:** None currently available

---

### Limited Language Support

**Impact:** Cannot analyze all codebases

**Details:**
- Primary focus: JavaScript, TypeScript, Python
- No support for other languages (Java, C#, Go, etc.)
- No language-agnostic analysis
- Hardcoded extension lists

**Workarounds:** Manual analysis of other languages

---

### Static Import Analysis Only

**Impact:** Misses dynamic imports

**Details:**
- No `import()` detection
- No `require.resolve()` detection
- No dynamic module loading
- No runtime wiring detection
- Misses FrameScheduler, registry-based loading

**Workarounds:** Manual code review

---

### No Re-export Analysis

**Impact:** May miss indirect imports

**Details:**
- Does not analyze re-export modules
- Cannot track transitive re-exports
- May mark used files as orphans (false positives)

**Workarounds:** Manual investigation of re-exports

---

### Substring Pattern Matching

**Impact:** Imprecise pattern matching

**Details:**
- Legacy detector uses substring matching
- Can match unintended words (e.g., "v1" matches "v2")
- No regex support
- No word boundary checking

**Workarounds:** Careful pattern selection

---

### Ripgrep Dependency

**Impact:** External dependency required

**Details:**
- Requires ripgrep (rg) installed in PATH
- Graceful degradation if missing (returns empty)
- Some features become unavailable without ripgrep

**Workarounds:** Install ripgrep

---

### No Module Federation Detection

**Impact:** Cannot analyze micro-frontend architectures

**Details:**
- No awareness of module federation
- Cannot detect shared modules
- Cannot analyze cross-app dependencies

**Workarounds:** Manual analysis

---

### No CI/CD Integration Examples

**Impact:** Harder to integrate into pipelines

**Details:**
- No GitHub Actions examples
- No GitLab CI examples
- No Jenkins examples
- No pre-commit hooks

**Workarounds:** Manual integration

---

### No Automated Testing Infrastructure

**Impact:** Harder to verify correctness

**Details:**
- No test suite visible in codebase
- No integration tests
- No unit tests for detectors

**Workarounds:** Manual testing

---

### No Documentation Generator

**Impact:** Limited API documentation

**Details:**
- No automated documentation
- No API reference
- No type hints in some modules

**Workarounds:** Manual documentation

---

### Large Report Memory Usage

**Impact:** Potential OOM on very large codebases

**Details:**
- Full report built in memory
- No streaming output
- For 10,000+ files, may consume significant RAM

**Workarounds:** Analyze smaller subsets

---

### No Diff-Based Ghost Tracking

**Impact:** Cannot identify new ghosts

**Details:**
- Cannot compare ghost lists between runs
- Cannot track ghost emergence/removal
- No trend analysis

**Workarounds:** Manual comparison of reports

---

## 9️⃣ Production Readiness Evaluation

### Architecture Clarity: 5/5

**Justification:**
- Clear layering: CLI → Services → Core → Analysis → Utils
- Well-defined module boundaries
- Intuitive file organization
- Easy to understand data flow
- Minimal cross-cutting concerns

**Strengths:**
- Consistent naming conventions
- Clear separation of concerns
- Logical directory structure
- Self-documenting code

**Areas for improvement:**
- None significant

---

### Modularity: 4/5

**Justification:**
- Each detector is independent
- Detectors follow consistent interface
- Services abstract complexity well
- Minimal coupling between modules

**Strengths:**
- Detector protocol via typing
- Pluggable architecture (requires code changes)
- Clear extension points
- No circular dependencies

**Areas for improvement:**
- No plugin system (requires code modifications)
- Some tight coupling in CLI layer
- Configuration loading could be more modular

---

### Determinism: 4/5

**Justification:**
- Same project state produces identical results (mostly)
- SHA256 hashing ensures content consistency
- No randomness in algorithms
- Sorted output for consistent ordering

**Strengths:**
- Hash-based file tracking
- Timestamped snapshots
- Consistent file metadata
- Sorted ghost lists

**Areas for improvement:**
- File order from os.walk is OS-dependent
- Snapshot ID contains timestamp (not deterministic)
- No incremental diff mode

---

### CLI Design: 5/5

**Justification:**
- Intuitive command structure
- Clear flag naming
- Good help messages (via argparse)
- Appropriate exit codes
- Useful stats mode for CI/CD

**Strengths:**
- Consistent command verbs (init, scan, ghost)
- Descriptive flag names (--deep, --stats, --tree-only)
- Good default values
- Clear error messages
- Exit code 2 for limit violations

**Areas for improvement:**
- None significant

---

### Extensibility: 3/5

**Justification:**
- Adding new detectors is straightforward
- Consistent interface across detectors
- Clear extension points in code

**Strengths:**
- Detector protocol is simple
- No detector-to-detector dependencies
- Configuration-driven where appropriate

**Areas for improvement:**
- No plugin system
- No dynamic detector loading
- Adding detectors requires code changes
- No hook system for custom reports
- No custom severity levels

---

### Maintainability: 5/5

**Justification:**
- Clean, readable code
- Type hints in most modules
- Good documentation (docstrings)
- Small, focused functions
- Minimal code duplication

**Strengths:**
- Clear function responsibilities
- Descriptive variable names
- Good error handling
- Consistent code style
- Well-organized imports

**Areas for improvement:**
- Some minor code duplication in rendering
- Could benefit from more unit tests

---

### Overall Production Readiness: 4.3/5

**Summary:** PROJECT CONTROL is well-architected, maintainable, and production-ready for its current scope. The main limitations are in extensibility (no plugin system) and scalability (no concurrency/caching). For static analysis of small to medium codebases, it is highly reliable and effective.

**Recommendation:** Production-ready for teams with:
- Small to medium codebases (<10,000 files)
- Primarily JavaScript/TypeScript/Python projects
- Need for static dead code detection
- Ability to modify code for custom detectors

**Not recommended for:**
- Enterprise-scale monorepos (100,000+ files)
- Multi-language polyglot projects
- Teams requiring zero-code extensibility
- Real-time analysis needs

---

## 🔟 Embedding Integration Readiness

### Is Snapshot Schema Suitable for Vector Indexing?

**Yes, with minimal extensions.**

**Current suitability:**
- ✅ File paths provide context
- ✅ File metadata (size, extension) useful for filtering
- ✅ SHA256 provides natural cache keys
- ❌ No semantic content stored
- ❌ No embeddings stored

**Required minimal changes:**

1. **Add embeddings to FileEntry** (optional):
```json
{
  "path": "src/main.py",
  "size": 1024,
  "modified": "2026-02-14T19:30:00+00:00",
  "sha256": "abc123...",
  "embedding": [0.1, 0.2, ...],  // Optional
  "embedding_model": "text-embedding-3-small"  // Optional
}
```

2. **Alternative: Separate embedding store**
```json
{
  "sha256": "abc123...",
  "embedding": [0.1, 0.2, ...],
  "model": "text-embedding-3-small",
  "dimension": 1536
}
```

**Recommendation:** Store embeddings separately from snapshot to keep snapshot file small and fast. Use SHA256 as foreign key.

---

### Are File Hashes Usable as Embedding Cache Keys?

**Yes, excellent.**

**Rationale:**
- SHA256 is cryptographically unique per file content
- Same content → same hash → same embedding (deterministic)
- Can skip re-embedding unchanged files
- Enables incremental embedding updates

**Caching strategy:**
```
For each file in snapshot:
  1. Compute SHA256
  2. Check cache for existing embedding
  3. If found and hash matches, use cached embedding
  4. If not found or hash mismatch, compute new embedding
  5. Store embedding with SHA256 as key
```

**Cache storage options:**
1. Local JSON file (simple)
2. SQLite database (scalable)
3. Redis (distributed)
4. Document store (Elasticsearch, MongoDB)

---

### Is Modularization Sufficient for Embedding Layer Injection?

**Yes, very good.**

**Current architecture supports:**

1. **Add new detector:**
```python
# analysis/semantic_similarity_detector.py
def analyze(snapshot, patterns):
    files = snapshot.get("files", [])
    # Compute semantic clusters
    # Return clusters/similarities
```

2. **Add new service:**
```python
# core/embedding_service.py
def compute_embeddings(project_root):
    # Load files, compute embeddings
    # Return embeddings
```

3. **Integrate into ghost flow:**
```python
# core/ghost.py
result["semantic_clusters"] = _run_detector(
    semantic_similarity_detector,
    snapshot,
    patterns
)
```

**Extension points:**
- ✅ Detector protocol
- ✅ Service layer abstraction
- ✅ Configuration loading
- ✅ Report rendering
- ❌ No plugin system (but not blocking)

---

### What Minimal Interface Would Be Required?

**Option 1: Embedding as Detector (Recommended)**

**Interface:**
```python
# analysis/semantic_detector.py
from typing import Any, Dict, List

def analyze(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Perform semantic analysis of codebase.
    
    Returns:
        List of semantic clusters:
        [
            {
                "cluster_id": 1,
                "files": ["src/helper1.py", "src/helper2.py"],
                "similarity": 0.95,
                "description": "Utility functions"
            },
            ...
        ]
    """
    # 1. Compute embeddings
    # 2. Cluster embeddings
    # 3. Return clusters
```

**Integration:**
```python
# core/ghost.py
from analysis import semantic_detector

def analyze_ghost(...):
    result = {
        "orphans": _run_detector(orphan_detector, snapshot, patterns),
        # ... existing detectors ...
        "semantic_clusters": _run_detector(semantic_detector, snapshot, patterns),
    }
    return result
```

**Configuration:**
```yaml
# patterns.yaml
embedding:
  model: "text-embedding-3-small"
  cache_dir: ".project-control/embeddings"
  similarity_threshold: 0.85
  max_clusters: 20
```

---

**Option 2: Embedding as Service**

**Interface:**
```python
# core/embedding_service.py
from typing import Dict, List
from pathlib import Path

class EmbeddingService:
    def __init__(self, project_root: Path, config: Dict):
        self.project_root = project_root
        self.config = config
        self.cache_dir = project_root / ".project-control" / "embeddings"
    
    def compute_embeddings(self, files: List[Dict]) -> Dict[str, List[float]]:
        """
        Compute embeddings for all files.
        
        Args:
            files: List of file entries from snapshot
            
        Returns:
            Mapping of file path to embedding vector
        """
        pass
    
    def load_embeddings(self) -> Dict[str, List[float]]:
        """Load cached embeddings from disk."""
        pass
    
    def save_embeddings(self, embeddings: Dict[str, List[float]]) -> None:
        """Save embeddings to disk."""
        pass
    
    def cluster_embeddings(self, embeddings: Dict[str, List[float]]) -> List[Dict]:
        """Cluster embeddings and return groups."""
        pass

def run_embedding_analysis(project_root: Path, patterns: Dict) -> Dict:
    """Orchestrate embedding analysis."""
    service = EmbeddingService(project_root, patterns.get("embedding", {}))
    # Compute, cluster, return results
```

**Integration:**
```python
# pc.py
def cmd_embedding(args: argparse.Namespace) -> None:
    snapshot = _load_existing_snapshot()
    if snapshot is None:
        return
    
    patterns = load_patterns(PROJECT_DIR)
    results = run_embedding_analysis(PROJECT_DIR, patterns)
    
    # Render report
    output_path = EXPORTS_DIR / "semantic_clusters.md"
    render_semantic_report(results, str(output_path))
```

---

**Option 3: Embedding as Standalone Tool**

**Interface:**
```python
# embedding/embedding_analyzer.py
from typing import Dict, List
from pathlib import Path

class EmbeddingAnalyzer:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.cache_dir = project_root / ".project-control" / "embeddings"
    
    def analyze(self, snapshot: Dict, config: Dict) -> Dict:
        """
        Perform semantic analysis.
        
        Returns:
            {
                "clusters": [...],
                "orphans_by_similarity": [...],
                "refactoring_suggestions": [...]
            }
        """
        pass

def main(project_root: Path, config: Dict) -> Dict:
    analyzer = EmbeddingAnalyzer(project_root)
    snapshot = load_snapshot(project_root)
    return analyzer.analyze(snapshot, config)
```

**Usage:**
```python
# embedding/qwen_embed.py (or similar)
from pathlib import Path
from core.snapshot_service import load_snapshot
from embedding.embedding_analyzer import main

results = main(Path.cwd(), {})
print(results)
```

---

### Recommended Approach

**Phase 1: Simple Embedding Cache (Low Effort)**
1. Add embedding computation to scan phase
2. Cache embeddings by SHA256
3. Use embeddings for similarity detection

**Phase 2: Semantic Detector (Medium Effort)**
1. Implement `semantic_detector.py` as detector
2. Add clustering logic
3. Integrate into ghost flow

**Phase 3: Full Integration (High Effort)**
1. Implement `embedding_service.py`
2. Add `pc embedding` command
3. Add semantic reports
4. Add embedding-based orphan detection

---

### Implementation Example

```python
# analysis/semantic_detector.py
from typing import Any, Dict, List
from pathlib import Path
from core.snapshot_service import load_snapshot

def compute_embedding(file_path: str) -> List[float]:
    """Compute embedding for a single file."""
    content = Path(file_path).read_text(encoding="utf-8")
    # Call embedding model (e.g., OpenAI, local model)
    # Return embedding vector
    return [0.1, 0.2, ...]  # Placeholder

def cluster_embeddings(embeddings: Dict[str, List[float]], threshold: float = 0.85) -> List[Dict]:
    """Cluster similar embeddings."""
    # Implement clustering (e.g., hierarchical, DBSCAN)
    clusters = []
    # ... clustering logic ...
    return clusters

def analyze(snapshot: Dict[str, Any], patterns: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Perform semantic analysis and identify similar files.
    """
    files = snapshot.get("files", [])
    embeddings = {}
    
    # Compute embeddings
    for file in files:
        path = file["path"]
        try:
            embeddings[path] = compute_embedding(path)
        except Exception:
            continue
    
    # Cluster embeddings
    config = patterns.get("embedding", {})
    clusters = cluster_embeddings(
        embeddings,
        threshold=config.get("similarity_threshold", 0.85)
    )
    
    # Return clusters
    return clusters

# Add to core/ghost.py
from analysis import semantic_detector

def analyze_ghost(...):
    result = {
        "orphans": _run_detector(orphan_detector, snapshot, patterns),
        # ...
        "semantic_clusters": _run_detector(semantic_detector, snapshot, patterns),
    }
    return result

# Add to core/markdown_renderer.py
SEVERITY_MAP["semantic_clusters"] = "INFO"
```

---

### Conclusion

**Embedding Integration Readiness: 5/5**

PROJECT CONTROL's architecture is excellent for embedding integration:

- ✅ Snapshot schema is suitable (with minimal extensions)
- ✅ SHA256 provides perfect cache keys
- ✅ Modular design enables easy injection
- ✅ Clear extension points exist
- ✅ Detector protocol is flexible
- ✅ Service layer abstraction is solid

**Effort to add embedding support:** Low to Medium

**Recommended path:**
1. Start with detector-based approach (Option 1)
2. Add caching by SHA256
3. Integrate into ghost flow
4. Add semantic clusters to reports

**Potential use cases:**
- Semantic orphan detection (files not used AND semantically isolated)
- Code similarity detection (potential refactoring targets)
- Documentation generation (semantic summaries)
- Search enhancement (semantic code search)

---

## Appendix A: File Structure

```
PROJECT_CONTROL/
├── pc.py                          # CLI entry point
├── core/
│   ├── ghost.py                   # Ghost detection orchestrator
│   ├── ghost_service.py           # Ghost execution and reporting
│   ├── scanner.py                 # File scanning and hashing
│   ├── snapshot.py                # Snapshot loading (legacy)
│   ├── snapshot_service.py       # Snapshot creation and persistence
│   ├── import_parser.py          # JS/TS import extraction
│   ├── markdown_renderer.py     # Report generation
│   └── writers.py                # Writer pattern analysis
├── analysis/
│   ├── orphan_detector.py        # Unused file detection
│   ├── duplicate_detector.py     # Duplicate file detection
│   ├── legacy_detector.py        # Legacy pattern detection
│   ├── session_detector.py       # Session file detection
│   ├── import_graph_detector.py # Import graph orphan detection
│   └── tree_renderer.py          # ASCII tree rendering
├── config/
│   └── patterns_loader.py        # Configuration loading
├── utils/
│   └── fs_helpers.py             # Filesystem helpers (ripgrep wrapper)
├── embedding/
│   └── qwen_embed.py            # Example embedding integration
├── contract/                     # Empty (future use)
├── documentation/                # Project documentation
├── AUDITY/                       # Audit reports
└── .project-control/
    ├── snapshot.json            # File inventory snapshot
    ├── patterns.yaml            # Configuration
    ├── status.yaml              # Status tracking
    └── exports/                 # Generated reports
        ├── ghost_candidates.md
        ├── import_graph_orphans.md
        ├── writers_report.md
        └── checklist.md
```

---

## Appendix B: Severity Levels

| Severity | Description | Examples |
|----------|-------------|----------|
| CRITICAL | Import graph orphans - highly likely dead code | Files unreachable from entrypoints |
| HIGH | Orphans - possibly dead code | Files not imported anywhere |
| MEDIUM | Legacy - deprecated code | Files with legacy patterns |
| LOW | Session - temporary files | Files containing "session" |
| INFO | Duplicates - potential refactoring | Files with same basename |

---

## Appendix C: Exit Codes

| Code | Meaning | Usage |
|------|---------|-------|
| 0 | Success | All successful operations |
| 1 | General error | Unhandled exceptions |
| 2 | Limit violation | Ghost limits exceeded |

---

## Appendix D: Environment Variables

**Currently used:** None

**Potential future use:**
- `PROJECT_CONTROL_HOME` - Custom control directory
- `PROJECT_CONTROL_CONFIG` - Custom config file
- `OPENAI_API_KEY` - For embedding services
- `PROJECT_CONTROL_VERBOSE` - Verbose logging

---

## Appendix E: External Dependencies

| Tool | Purpose | Required |
|------|---------|----------|
| ripgrep (rg) | Pattern searching | Yes (degraded if missing) |
| Python 3.8+ | Runtime | Yes |
| None | Other | No |

---

## Appendix F: Configuration Reference

### patterns.yaml

```yaml
# Writer patterns to search for
writers:
  - scale
  - emissive
  - opacity
  - position

# Entrypoint files (for import graph)
entrypoints:
  - main.js
  - index.ts

# Directories to ignore during scan
ignore_dirs:
  - .git
  - .project-control
  - node_modules
  - __pycache__

# File extensions to include
extensions:
  - .py
  - .js
  - .ts
  - .md
  - .txt

# Legacy filename patterns (optional)
legacy_patterns:
  - old
  - deprecated
  - v1

# Graph ignore patterns (optional)
graph_ignore_patterns:
  - test
  - spec
  - example

# Embedding configuration (future)
embedding:
  model: "text-embedding-3-small"
  cache_dir: ".project-control/embeddings"
  similarity_threshold: 0.85
  max_clusters: 20
```

---

## Conclusion

PROJECT CONTROL is a well-architected, production-ready static analysis tool with clear separation of concerns and a modular design. It successfully identifies dead code, duplicates, and structural issues in JavaScript, TypeScript, and Python projects.

The architecture is highly suitable for future enhancements, particularly semantic embedding integration. The main limitations are in scalability (no concurrency, no caching) and extensibility (no plugin system), but these are design choices appropriate for the current scope.

For teams seeking a reliable static analysis tool with the flexibility to extend functionality, PROJECT CONTROL provides a solid foundation with minimal technical debt and clear paths for future development.