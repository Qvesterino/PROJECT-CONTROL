"""Help and documentation service for PROJECT_CONTROL.

Provides comprehensive help content for new users and reference
material for all features.
"""

from __future__ import annotations

from project_control.utils.terminal import print_header, print_section


# ── Help Content ───────────────────────────────────────────────────────

def get_quick_start() -> str:
    """Get quick start tutorial content."""
    return """
PROJECT CONTROL - 30-SECOND TUTORIAL
======================================

GET STARTED IN 3 STEPS:

1. INITIALIZE
   $ pc init
   Creates .project-control/ directory with default config

2. SCAN YOUR PROJECT
   $ pc scan
   Indexes all files with SHA256 hashing

3. ANALYZE
   $ pc ghost          - Find orphan/legacy code
   $ pc graph build    - Build dependency graph
   $ pc graph report   - View analysis results

THAT'S IT!
Now you know what's happening in your codebase.

INTERACTIVE MODE:
   $ pc ui
   Access all features through a friendly text-based menu.

COMMON WORKFLOW:
   1) pc scan           - Get current state
   2) pc ghost          - Find dead code
   3) pc graph build    - Analyze dependencies
   4) pc graph report   - View results

NEED MORE?
   Use 'pc --help' for command reference
   Use 'pc ui' for interactive menu with built-in help
"""


def get_command_reference() -> str:
    """Get comprehensive command reference."""
    return """
COMMAND REFERENCE
=================

PROJECT MANAGEMENT:
  pc init           Initialize .project-control/ in current directory
  pc scan           Scan project files and create snapshot
  pc checklist      Generate markdown checklist from snapshot

ANALYSIS & SEARCH:
  pc ghost          Run ghost analysis (orphans, legacy, sessions, etc.)
  pc ghost --mode strict     Strict mode - no ignore patterns
  pc find <symbol>  Search for symbol usage across project

DEPENDENCY GRAPH:
  pc graph build    Build import dependency graph
  pc graph report   Generate graph report (uses cache if valid)
  pc graph trace <target>    Trace dependency paths

INTERACTIVE UI:
  pc ui             Launch interactive text-based menu

CODE QUALITY:
  pc writers        Analyze writer patterns in codebase

EMBEDDING (OPTIONAL):
  pc embed build    Build FAISS embedding index
  pc embed rebuild  Rebuild index from scratch
  pc embed search "query"    Semantic code search

GLOBAL OPTIONS:
  --help, -h       Show help message
  --version        Show version number

PATH ARGUMENTS:
  Most commands accept an optional project_root path:
  pc scan /path/to/project
  pc ghost /path/to/project

If not provided, uses current directory.
"""


def get_ghost_analysis_help() -> str:
    """Get ghost analysis explanation."""
    return """
GHOST ANALYSIS EXPLAINED
=========================

WHAT IS GHOST ANALYSIS?

Ghost analysis finds parts of your codebase that no longer matter:
code that exists but isn't being used, or shouldn't exist at all.

THE FIVE DETECTORS:

1. ORPHANS (HIGH SEVERITY)
   Files that are never referenced by anything.
   - No imports, no require() calls, no references
   - Often leftover from refactoring
   - Safe to delete (usually)

2. LEGACY (MEDIUM SEVERITY)
   Outdated code matching known legacy patterns.
   - Old API calls
   - Deprecated patterns
   - TODO/FIXME comments left behind

3. SESSIONS (LOW SEVERITY)
   Temporary or session artifacts.
   - Test files in production code
   - Debug logs
   - Temporary scripts

4. DUPLICATES (INFO SEVERITY)
   Files with identical names in different paths.
   - Potential naming conflicts
   - May indicate copy-paste issues

5. SEMANTIC (MEDIUM SEVERITY)
   Files that don't belong (requires Ollama).
   - Uses semantic embeddings
   - Identifies outliers based on content similarity
   - Optional - requires Ollama to be running

MODES:

  PRAGMATIC (default)
  Applies ignore patterns from .project-control/patterns.yaml
  Ignores common noise (node_modules, __pycache__, etc.)

  STRICT (--mode strict)
  No ignore patterns applied
  Analyzes everything - more results, more noise

REPORTS:

Results are saved to:
  .project-control/exports/ghost_candidates.md

Each finding includes:
  - Severity level (HIGH, MEDIUM, LOW, INFO)
  - File path and line number
  - Reason for flagging
  - Suggested action (delete, review, etc.)

TYPICAL WORKFLOW:

  1) pc scan          - Get current state
  2) pc ghost         - Find ghosts
  3) Review report    - Check .project-control/exports/ghost_candidates.md
  4) Delete orphans   - Remove dead code
  5) Rescan           - Verify cleanup

BEST PRACTICES:

  - Review HIGH severity findings first (orphans)
  - Check MEDIUM findings for actual issues
  - IGNORE/INFO findings are usually safe to ignore
  - Always review before deleting - some orphans might be used
  - Use strict mode for thorough analysis (more noise)

LIMITATIONS:

  - Static analysis only - can't detect dynamic requires/imports
  - May miss edge cases in complex code
  - Semantic analysis requires Ollama (optional)
  - Not a replacement for human review
"""


def get_dependency_graph_help() -> str:
    """Get dependency graph explanation."""
    return """
DEPENDENCY GRAPH EXPLAINED
===========================

WHAT IS THE DEPENDENCY GRAPH?

The dependency graph maps how files in your project depend on each other:
- Nodes = files
- Edges = import/require relationships

SUPPORTED LANGUAGES:

  PYTHON
  - import statements
  - from ... import ...
  - Uses AST parsing (accurate)

  JAVASCRIPT / TYPESCRIPT
  - import ... from ...
  - require(...)
  - Uses regex (fast, may have edge cases)

HOW IT WORKS:

1. SCAN
   pc scan
   Creates snapshot with all files and their content

2. BUILD GRAPH
   pc graph build
   - Reads snapshot
   - Extracts imports from each file
   - Resolves import paths to files
   - Builds graph structure

3. ANALYZE
   pc graph report
   Shows metrics:
   - Total nodes (files)
   - Total edges (imports)
   - Orphan candidates (files with no dependencies)
   - Circular dependencies (cycles)

KEY METRICS:

  FAN-IN
  How many files depend on this file.
  High fan-in = important, widely used.

  FAN-OUT
  How many files this file depends on.
  High fan-out = complex, may need refactoring.

  CYCLES
  Circular dependencies (A imports B, B imports A).
  Can cause issues and should be broken.

  DEPTH
  Maximum depth of dependency chain.
  Deep chains indicate tightly coupled code.

TRACING:

  Trace dependencies to/from any file:

  pc graph trace src/utils.js
  Shows both incoming and outgoing dependencies.

  pc graph trace src/utils.js --direction inbound
  Shows only what depends on this file.

  pc graph trace src/utils.js --max-depth 3
  Limits trace depth to 3 levels.

CACHE & PERFORMANCE:

  Graph is cached in .project-control/out/
  Rebuilds only if snapshot changes
  Use --force to rebuild manually

REPORTS:

  Graph report:  .project-control/out/graph.report.md
  Metrics JSON:  .project-control/out/graph.metrics.json

USE CASES:

  1. REFRACTORING
     - Find files with high fan-out (too complex)
     - Identify core files (high fan-in)
     - Break circular dependencies

  2. UNDERSTANDING CODEBASE
     - Trace how features connect
     - Find entry points
     - Understand architecture

  3. IMPACT ANALYSIS
     - See what would break if you delete a file
     - Identify affected modules before changes

  4. TECHNICAL DEBT
     - Find cycles (bad for maintainability)
     - Identify orphaned files
     - Measure coupling

LIMITATIONS:

  - Static analysis only (no runtime resolution)
  - May miss dynamic imports (require(variable), import())
  - JS/TS uses regex (less accurate than AST)
  - Doesn't resolve npm packages or Python stdlib
"""


def get_troubleshooting_help() -> str:
    """Get troubleshooting guide."""
    return """
TROUBLESHOOTING
===============

COMMON ISSUES & SOLUTIONS

1. "Snapshot not found"
   CAUSE: No .project-control/snapshot.json
   SOLUTION: Run 'pc scan' first

2. "Graph not found"
   CAUSE: No dependency graph built
   SOLUTION: Run 'pc graph build' first

3. "Ripgrep not found"
   CAUSE: ripgrep (rg) not installed
   SOLUTION: Install ripgrep
     - Windows: choco install ripgrep
     - Mac:     brew install ripgrep
     - Linux:   apt install ripgrep

4. "Ollama not available"
   CAUSE: Ollama server not running
   SOLUTION: (Optional - only for semantic analysis)
     - Install Ollama: https://ollama.ai
     - Start server: ollama serve
     - Pull model: ollama pull qwen3-embedding:8b
   Note: Project works fine without Ollama!

5. "Corrupted snapshot"
   CAUSE: snapshot.json is invalid JSON
   SOLUTION:
     - Delete .project-control/snapshot.json
     - Run 'pc scan' to recreate

6. "Corrupted graph"
   CAUSE: graph files are corrupted
   SOLUTION:
     - Use Tools → Clear Cache
     - Or delete .project-control/out/
     - Run 'pc graph build'

7. "No Python files found"
   CAUSE: Wrong extensions or ignore patterns
   SOLUTION:
     - Check .project-control/patterns.yaml
     - Ensure .py is in extensions list
     - Check ignore_dirs doesn't include your files

8. "Too many false positives in ghost"
   CAUSE: Strict mode or dynamic imports
   SOLUTION:
     - Use default (pragmatic) mode
     - Adjust patterns.yaml ignore patterns
     - Manual review is normal!

9. "Out of memory during scan"
   CAUSE: Very large project
   SOLUTION:
     - Use more specific ignore patterns
     - Exclude large directories (node_modules, etc.)

10. "Import resolution failed"
    CAUSE: Complex module paths
    SOLUTION:
      - Check graph.config.yaml alias settings
      - Adjust include_globs/exclude_globs
      - May need to update resolver logic

PERFORMANCE TIPS:

1. Use incremental scans
   - pc scan only rescans changed files
   - Graph rebuilds only if snapshot changes

2. Exclude noise early
   - Add node_modules, __pycache__, etc. to ignore_dirs
   - Use .gitignore patterns in patterns.yaml

3. Use pragmatic mode
   - Default mode ignores common noise
   - Use strict only when needed

4. Cache when possible
   - Graph results are cached
   - Don't rebuild unnecessarily

GETTING MORE HELP:

1. Check logs
   - Logs are written to standard output
   - Use --verbose flag (if available)

2. Try interactive mode
   - pc ui has built-in diagnostics
   - Tools → Diagnostics shows system info

3. Check documentation
   - MANU​AL.md has detailed command reference
   - README.md has overview and examples

4. Report bugs
   - GitHub: https://github.com/danielhlavac/project-control/issues
   - Include: Python version, OS, error message, steps to reproduce

RECOVERY OPTIONS:

If everything is broken:

1. Reset to defaults
   - Delete .project-control/ directory
   - Run 'pc init'
   - Run 'pc scan'

2. Use backups
   - Tools → Restore Backup
   - Choose a working backup

3. Clear and rebuild
   - Tools → Clear Cache
   - pc scan
   - pc graph build
"""


def get_keyboard_shortcuts_help() -> str:
    """Get keyboard shortcuts reference."""
    return """
KEYBOARD SHORTCUTS
==================

MAIN MENU:
  0        Return to previous menu / Exit
  1-8      Select menu option by number
  Q        Open Quick Actions menu
  Enter    Confirm selection / Continue

QUICK ACTIONS MENU (Q):
  1        Full Analysis (scan → ghost → graph → report)
  2        Health Check
  3        Find Orphans
  4        Find Cycles
  5        Dependency Audit
  6        Favorites
  7        History
  0        Back

TOOLS MENU (7):
  1        List Backups
  2        Create Manual Backup
  3        Restore Backup
  4        Delete Backup
  5        Cleanup Old Backups
  6        Clear Graph Cache
  7        Show Diagnostics
  0        Back

EXPLORE MENU (4):
  [1-N]    Select favorite by number
  f        Add current target to favorites
  0        Back

FAVORITES MENU (Quick Actions → 6):
  1        Add current target to favorites
  2        Trace a favorite
  3        Remove a favorite
  0        Back

NAVIGATION:
  0        Always returns to previous menu
          (or exits if at main menu)

INPUT TIPS:
  - Press Enter with empty input to cancel
  - Use 'y' or 'Y' to confirm destructive actions
  - Any other key cancels confirmation

CONTEXT HELP:
  Most menus show current settings and options
  Status indicators in header show project health
  Notifications show warnings and suggestions

MENUS WITH SHORTCUTS:

Main Menu
  0 = Exit
  1-7 = Menu options
  Q = Quick Actions
  8 = Reports (NEW!)

Quick Actions
  0 = Back
  1-7 = Quick action options

Reports
  0 = Back
  1-6 = View specific report

Tools
  0 = Back
  1-7 = Tool options

EXPLORE MODE:
  - Enter file path or symbol to trace
  - [1-N] to select favorite
  - 'f' to add to favorites
  - '0' to cancel

TIPS:
  - Favorites save time for frequently traced files
  - History shows recent actions
  - Use Quick Actions for common workflows
  - Check Health menu for project status
"""


# ── Help Display Functions ─────────────────────────────────────────────

def show_quick_start() -> None:
    """Display quick start tutorial."""
    print_header("QUICK START", width=60)
    print(get_quick_start())


def show_command_reference() -> None:
    """Display command reference."""
    print_header("COMMAND REFERENCE", width=60)
    print(get_command_reference())


def show_ghost_analysis_help() -> None:
    """Display ghost analysis explanation."""
    print_header("GHOST ANALYSIS", width=60)
    print(get_ghost_analysis_help())


def show_dependency_graph_help() -> None:
    """Display dependency graph explanation."""
    print_header("DEPENDENCY GRAPH", width=60)
    print(get_dependency_graph_help())


def show_troubleshooting_help() -> None:
    """Display troubleshooting guide."""
    print_header("TROUBLESHOOTING", width=60)
    print(get_troubleshooting_help())


def show_keyboard_shortcuts_help() -> None:
    """Display keyboard shortcuts reference."""
    print_header("KEYBOARD SHORTCUTS", width=60)
    print(get_keyboard_shortcuts_help())


# ── Help Menu ─────────────────────────────────────────────────────

def help_menu_options() -> list[dict]:
    """Get help menu options."""
    return [
        {
            "key": "1",
            "label": "Quick Start",
            "description": "30-second tutorial to get started",
            "action": show_quick_start
        },
        {
            "key": "2",
            "label": "Command Reference",
            "description": "All commands and their usage",
            "action": show_command_reference
        },
        {
            "key": "3",
            "label": "Ghost Analysis",
            "description": "What ghost analysis finds and how it works",
            "action": show_ghost_analysis_help
        },
        {
            "key": "4",
            "label": "Dependency Graph",
            "description": "How the dependency graph works and how to use it",
            "action": show_dependency_graph_help
        },
        {
            "key": "5",
            "label": "Troubleshooting",
            "description": "Common issues and solutions",
            "action": show_troubleshooting_help
        },
        {
            "key": "6",
            "label": "Keyboard Shortcuts",
            "description": "All keyboard shortcuts and navigation",
            "action": show_keyboard_shortcuts_help
        }
    ]


def display_help_menu() -> None:
    """Display the help menu options."""
    options = help_menu_options()

    print("\n" + "="*60)
    print("  HELP")
    print("="*60)

    for opt in options:
        print(f"\n{opt['key']}) {opt['label']}")
        print(f"   {opt['description']}")

    print("\n0) Back")


def execute_help_menu_choice(choice: str) -> bool:
    """
    Execute a help menu choice.

    Args:
        choice: Menu option selected

    Returns:
        True if should stay in help menu, False if should go back
    """
    if choice == "0":
        return False

    options = help_menu_options()
    for opt in options:
        if opt["key"] == choice:
            opt["action"]()
            return True

    return True
