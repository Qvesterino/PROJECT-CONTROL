# SOUL.md

This document captures the philosophy, guiding principles, and soul of PROJECT_CONTROL.

## Core Philosophy

**Architectural truth through deterministic analysis.**

PROJECT_CONTROL exists because codebases accumulate complexity, and complexity hides truth. The soul of this project is to reveal that truth—not to guess, not to approximate, but to expose what is actually there through deterministic, verifiable analysis.

## Guiding Principles

### 1. Determinism Over Heuristics
Every operation should produce the same output given the same input:
- Snapshots are content-addressable using SHA256 hashes
- Graph nodes are assigned sequential IDs starting from 1
- All lists are sorted before serialization
- Results are cached based on deterministic hash computation

**No randomness. No ambiguity. No guessing.**

### 2. Purity Over Side Effects
Core analysis functions should be pure:
- `ghost()` in `core/ghost.py` is the canonical pure function
- Detectors expose `analyze()` functions that return lists
- File reads go through ContentStore, not direct filesystem access
- Separation of concerns: analysis vs. execution

**Side effects belong in service layers, not in the core.**

### 3. Reality Over Abstraction
The tool deals with what actually exists, not what should exist:
- Ghost analysis finds what is NOT referenced, not what "should be" removed
- Dependency graphs show actual imports, not intended architecture
- Content deduplication reveals identical files across paths
- Semantic detection finds outliers based on actual embeddings

**Discover the present, don't prescribe the future.**

### 4. Static Over Dynamic
Analysis happens at rest, not at runtime:
- No code execution, no instrumentation, no runtime dependencies
- AST-based extraction for Python (accurate but slow)
- Regex-based extraction for JS/TS (fast but less accurate)
- Ripgrep for symbol search (fast, reliable)
- Optional embedding analysis (local Ollama, no cloud)

**Analyze the code as it sits on disk, not as it behaves in memory.**

### 5. Minimalism Over Features
Do one thing well, with minimal dependencies:
- Core requires only Python 3.10+ and ripgrep
- Embedding is optional and clearly marked as such
- No complex UI—text-based, markdown reports
- No database—JSON files, content blobs
- No authentication, no cloud, no API keys

**Less is more. Complexity is the enemy of clarity.**

### 6. Precision Over Performance
When there's a tradeoff, choose precision:
- AST parsing over regex when accuracy matters (Python)
- ContentStore abstraction for filesystem independence
- Sorted lists for deterministic serialization
- Explicit error handling over silent failures

**Correctness first, optimization second.**

## The Soul in Practice

### What Matters
- **Truth**: What code actually does, not what we think it does
- **Clarity**: Making invisible dependencies visible
- **Determinism**: Same code, same result, every time
- **Simplicity**: Minimal setup, maximal insight

### What Doesn't Matter
- **Runtime behavior**: We analyze static code, not running systems
- **Performance profiling**: That's a different tool's job
- **Code style**: We find structure, not style violations
- **Business logic**: We find what exists, not what it should do
- **Trend analysis**: We analyze the present, not the history

## The Anti-Goals

PROJECT_CONTROL is NOT:
- A performance profiler
- A runtime debugger
- A code formatter/linter
- A test runner
- A CI/CD pipeline tool
- A cloud service
- A "magic" AI that fixes everything

## The Essence

PROJECT_CONTROL is a mirror for your codebase. It doesn't judge. It doesn't prescribe. It simply reflects what is there—deterministically, precisely, and completely.

**Stop guessing. Start knowing.**
