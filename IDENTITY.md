# IDENTITY.md

This document defines who PROJECT_CONTROL is—its personality, role, and essence.

## Who Am I?

**I am a deterministic architectural analysis engine.**

I am not a developer tool in the traditional sense. I am a static analysis engine that examines codebases at rest and reveals their structure, dependencies, and dead code.

### My Identity

```
Name: PROJECT_CONTROL (alias: pc)
Type: Static Analysis Engine
Nature: Deterministic, Immutable, Pure
Language: Python 3.10+
Purpose: Architectural clarity through deterministic analysis
```

## My Personality

### Analytical and Precise
I don't guess. I don't approximate. I compute.
- Every file has a SHA256 hash
- Every analysis is deterministic
- Every result is reproducible

### Quiet and Non-Intrusive
I don't require runtime instrumentation. I don't modify your code. I don't need to be installed into your project. I scan, analyze, and report.

### Minimalist and Direct
- 4 commands to get started: `pc init`, `pc scan`, `pc ghost`, `pc graph report`
- Text-based output, markdown reports
- No complex UI, no dashboards, no graphs
- Just the facts

### Independent and Self-Contained
- No database required
- No cloud services
- No API keys
- No authentication
- Local analysis only

### Strict but Forgiving
- I enforce determinism in core functions
- I warn about unreadable files but continue
- I provide graceful degradation (e.g., ripgrep not found)
- I separate "must-have" from "nice-to-have" (embedding is optional)

## My Role in Your Workflow

### The Architectural Microscope
I examine code at the structural level:
- Which files are orphans (never referenced)?
- Which files are duplicates (identical content)?
- Which files have semantic outliers?
- What are the actual import dependencies?

### The Dependency Tracer
I follow the thread of connections:
- `pc graph build` constructs the import graph
- `pc graph trace` follows paths to/from any file
- `pc graph report` computes metrics (fan-in/out, cycles, depth)

### The Dead Code Detector
I find what no longer matters:
- Orphaned files not referenced anywhere
- Legacy code matching known patterns
- Session files left behind
- Duplicate files with identical names
- Semantic outliers (via embeddings, optional)

### The Static Snapshotter
I capture the state of your codebase deterministically:
- Content-addressable file storage (SHA256)
- Deduplicated content blobs
- Immutable snapshot metadata
- Cached analysis results

## What I Am Not

| I Am NOT | Why |
|----------|-----|
| A performance profiler | I analyze structure, not runtime behavior |
| A test runner | I find what exists, not whether it works |
| A linter/formatter | I find dead code, not style violations |
| A CI/CD tool | I'm a standalone analysis engine |
| A cloud service | I run locally, no data leaves your machine |
| A magic AI | I'm deterministic, not probabilistic |

## My Communication Style

### Output Format
- **Plain text**: Simple, readable, parseable
- **Markdown**: Structured, human-readable, version-controllable
- **JSON**: Machine-readable, structured metadata

### Error Handling
- I log warnings and continue where possible
- I don't crash on individual file errors
- I provide clear error messages
- I validate inputs and exit with proper exit codes

### Tone
- Factual, not opinionated
- Direct, not verbose
- Structured, not conversational
- Precise, not ambiguous

## My Core Competencies

### 1. Ghost Analysis
`pc ghost` runs 5 detectors:
- **Orphans**: Files never referenced by anything (ripgrep-based)
- **Legacy**: Files matching legacy patterns
- **Sessions**: Temporary/session artifacts
- **Duplicates**: Files with identical names in different paths
- **Semantic**: Semantically similar or orphan files (embedding-based, optional)

### 2. Graph Engine
`pc graph build/report/trace` provides:
- AST-based import extraction for Python
- Regex-based import extraction for JS/TS
- Dependency graph construction
- Metrics: fan-in/out, depth, cycles (Tarjan SCC)
- Path tracing to/from any node

### 3. Snapshot System
`pc scan` creates:
- Content-addressable file storage (SHA256)
- Deduplicated content blobs
- Deterministic snapshot metadata
- Cached analysis results

### 4. Embedding Search (Optional)
`pc embed build/search` provides:
- Local Ollama-based embeddings
- FAISS vector similarity search
- Semantic code discovery
- Outlier detection

## My Technical Personality

### Pure Functions Where Possible
- `ghost()` in `core/ghost.py` is the canonical pure function
- Detectors expose `analyze()` functions
- No side effects in core analysis

### Explicit Over Implicit
- Configuration in YAML files
- Clear command-line arguments
- Explicit error messages
- No magic behavior

### Unix Philosophy
- Do one thing well (architectural analysis)
- Composable commands (`scan → ghost → graph`)
- Text-based input/output
- Piped workflows supported

### Type Safety
- TypedDict for structured data
- Type hints throughout
- mypy checking (non-blocking)

## My Relationship With Users

### I Serve Developers Who:
- Work on large, complex codebases
- Need to understand architectural structure
- Want to find dead code before refactoring
- Value determinism and reproducibility
- Prefer local tools over cloud services

### I Don't Serve Developers Who Want:
- Real-time performance profiling
- Automated code generation
- Cloud-hosted analysis
- Complex UI dashboards
- Magic AI that "fixes everything"

## My Motto

> **"Find dead code. Understand your architecture. Stop guessing."**

This isn't just a tagline—it's my identity. I exist to reveal the truth about your codebase, not to guess, not to approximate, but to show you exactly what is there through deterministic analysis.

---

**I am PROJECT_CONTROL. I am your architectural microscope. I reveal what is actually there.**
