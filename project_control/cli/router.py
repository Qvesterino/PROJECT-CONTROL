"""CLI router that delegates commands to core services."""

from __future__ import annotations

import argparse
import logging
import yaml
from pathlib import Path
from typing import Optional

from project_control.config.patterns_loader import load_patterns
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR
from project_control.core.ghost_service import run_ghost, write_ghost_report
from project_control.core.markdown_renderer import render_writer_report
from project_control.core.snapshot_service import create_snapshot, load_snapshot, save_snapshot
from project_control.core.writers import run_writers_analysis
from project_control.core.error_handler import ErrorHandler, ErrorContext
from project_control.utils.fs_helpers import run_rg
from project_control.cli.graph_cmd import graph_build, graph_report, graph_trace
from project_control.utils.renderers import render_unused, render_patterns, render_search
from project_control.render.dead_renderer import render_dead
from project_control.analysis.dead_analyzer import analyze_dead_code
from project_control.analysis.unused_analyzer import analyze_unused_systems
from project_control.analysis.patterns_analyzer import analyze_patterns
from project_control.analysis.search_analyzer import smart_search
import json
from project_control.cli.menu import run_menu

logger = logging.getLogger(__name__)

PROJECT_DIR = Path.cwd()
CONTROL_DIR = PROJECT_DIR / ".project-control"
EXPORTS_DIR = CONTROL_DIR / "exports"
STATUS_FILE = CONTROL_DIR / "status.yaml"
PATTERNS_FILE = CONTROL_DIR / "patterns.yaml"

DEFAULT_PATTERNS = {
    "writers": ["scale", "emissive", "opacity", "position"],
    "entrypoints": ["main.js", "index.ts"],
    "ignore_dirs": [".git", ".project-control", "node_modules", "__pycache__"],
    "extensions": [".py", ".js", ".ts", ".md", ".txt"],
}


def ensure_control_dirs() -> None:
    CONTROL_DIR.mkdir(exist_ok=True)
    EXPORTS_DIR.mkdir(exist_ok=True)


def _load_existing_snapshot() -> Optional[dict]:
    try:
        return load_snapshot(PROJECT_DIR)
    except FileNotFoundError:
        print("Run 'pc scan' first.")
        return None


def _ensure_gitignore() -> None:
    """Add .project-control/ to .gitignore if not already present."""
    gitignore = PROJECT_DIR / ".gitignore"
    entry = ".project-control/"

    existing_lines: list[str] = []
    if gitignore.exists():
        existing_lines = gitignore.read_text(encoding="utf-8").splitlines()

    if any(line.strip() == entry.rstrip("/") or line.strip() == entry for line in existing_lines):
        return  # Already ignored

    with gitignore.open("a", encoding="utf-8") as f:
        if existing_lines and existing_lines[-1].strip() != "":
            f.write("\n")
        f.write(f"\n# Project Control artifacts\n{entry}\n")

    print(f"  Added '{entry}' to .gitignore")


def cmd_init(args: argparse.Namespace) -> int:
    ensure_control_dirs()
    _ensure_gitignore()

    if not PATTERNS_FILE.exists():
        with PATTERNS_FILE.open("w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_PATTERNS, f)

    if not STATUS_FILE.exists():
        with STATUS_FILE.open("w", encoding="utf-8") as f:
            yaml.dump({"tags": {}}, f)

    print("PROJECT CONTROL initialized.")
    return EXIT_OK


def cmd_scan(args: argparse.Namespace) -> int:
    """Scan project and create snapshot with error handling."""
    try:
        with ErrorContext("Scanning project"):
            ensure_control_dirs()
            run_scan(PROJECT_DIR)
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Scan command")


def cmd_checklist(args: argparse.Namespace) -> int:
    """Generate checklist from snapshot with error handling."""
    try:
        with ErrorContext("Generating checklist"):
            snapshot = _load_existing_snapshot()
            if snapshot is None:
                return EXIT_OK

            ensure_control_dirs()

            output = ["# PROJECT CHECKLIST\n"]
            for file in snapshot["files"]:
                output.append(f"- [ ] {file['path']}")

            checklist_path = EXPORTS_DIR / "checklist.md"
            checklist_path.write_text("\n".join(output), encoding="utf-8")

            print(f"Checklist generated: {checklist_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Checklist command")


def cmd_find(args: argparse.Namespace) -> int:
    """Find symbol usage with error handling."""
    if not args.symbol:
        print("Provide symbol to search.")
        return EXIT_VALIDATION_ERROR

    try:
        with ErrorContext("Searching for symbol"):
            ensure_control_dirs()

            result = run_rg(args.symbol)
            output_path = EXPORTS_DIR / f"find_{args.symbol}.md"

            output_path.write_text(
                f"# Usage of: {args.symbol}\n\n{result or 'No matches found.'}",
                encoding="utf-8",
            )

            print(f"Search results saved: {output_path}")
        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Find command")


def cmd_ghost(args: argparse.Namespace) -> int:
    """Run shallow ghost analysis using canonical ghost core with error handling."""
    try:
        with ErrorContext("Running ghost analysis"):
            ghost_data = run_ghost(args, PROJECT_DIR)
            if ghost_data is None:
                return EXIT_OK

            result = ghost_data["result"]
            counts = ghost_data["counts"]

            # Write markdown report
            write_ghost_report(result, PROJECT_DIR)

            # Print summary
            print("\nGhost Results")
            print("-------------")
            print(f"Orphans:   {counts.get('orphans', 0)}")
            print(f"Legacy:    {counts.get('legacy', 0)}")
            print(f"Sessions:  {counts.get('sessions', 0)}")
            print(f"Duplicates: {counts.get('duplicates', 0)}")
            print(f"Semantic:  {counts.get('semantic', 0)}")

            if ghost_data.get("limit_violation"):
                print(f"\n⚠️  {ghost_data['limit_violation']['message']}")
                return ghost_data["limit_violation"]["exit_code"]

        return EXIT_OK
    except SystemExit:
        raise
    except Exception as e:
        return ErrorHandler.handle(e, "Ghost command")

    return EXIT_OK


def cmd_writers(args: argparse.Namespace) -> int:
    ensure_control_dirs()

    results = run_writers_analysis(PROJECT_DIR)
    output_path = EXPORTS_DIR / "writers_report.md"
    render_writer_report(results, str(output_path))

    print(f"Writers report saved: {output_path}")
    return EXIT_OK


def cmd_dead(args: argparse.Namespace) -> int:
    """Dead Code Radar - finds files with zero or minimal usage."""
    try:
        threshold = getattr(args, "threshold", 2)
        json_output = getattr(args, "json", False)

        # Load snapshot to get file list
        snapshot = load_snapshot(PROJECT_DIR)
        if snapshot is None:
            print("Error: No snapshot found. Run 'pc scan' first.")
            return EXIT_VALIDATION_ERROR

        # Extract file paths from snapshot
        files = [f.get("path") for f in snapshot.get("files", [])]

        # Run analysis
        result = analyze_dead_code(files, low_usage_threshold=threshold)

        if json_output:
            print(json.dumps(result, indent=2))
        else:
            output = render_dead(result)
            _safe_print(output)

        return EXIT_OK
    except Exception as e:
        logger.error(f"Dead code analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return EXIT_VALIDATION_ERROR


def cmd_unused(args: argparse.Namespace) -> int:
    """Unused System Scan - finds systems that exist but aren't used."""
    try:
        json_output = getattr(args, "json", False)
        no_color = getattr(args, "no_color", False)
        result = analyze_unused_systems(PROJECT_DIR)

        if json_output:
            print(json.dumps(result, indent=2))
        else:
            output = render_unused(result, colored=not no_color)
            _safe_print(output)

        return EXIT_OK
    except Exception as e:
        logger.error(f"Unused systems analysis failed: {e}")
        return EXIT_VALIDATION_ERROR


def cmd_patterns(args: argparse.Namespace) -> int:
    """Suspicious Patterns - detects forbidden code patterns."""
    try:
        patterns_file = getattr(args, "file", None)
        json_output = getattr(args, "json", False)
        no_color = getattr(args, "no_color", False)
        result = analyze_patterns(PROJECT_DIR, patterns_file=patterns_file)

        if json_output:
            print(json.dumps(result, indent=2))
        else:
            output = render_patterns(result, colored=not no_color)
            _safe_print(output)

        return EXIT_OK
    except Exception as e:
        logger.error(f"Patterns analysis failed: {e}")
        return EXIT_VALIDATION_ERROR


def cmd_search(args: argparse.Namespace) -> int:
    """Smart Search - power-user code search."""
    try:
        patterns = getattr(args, "pattern", [])
        invert = getattr(args, "invert", False)
        files_only = getattr(args, "files_only", False)
        json_output = getattr(args, "json", False)
        no_color = getattr(args, "no_color", False)

        if not patterns:
            print("Error: At least one pattern is required")
            return EXIT_VALIDATION_ERROR

        result = smart_search(patterns, PROJECT_DIR, invert=invert, files_only=files_only)

        if json_output:
            print(json.dumps(result, indent=2))
        else:
            output = render_search(result, colored=not no_color)
            _safe_print(output)

        return EXIT_OK
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return EXIT_VALIDATION_ERROR


def dispatch(args: argparse.Namespace) -> int:
    if args.command == "init":
        return cmd_init(args)
    if args.command == "scan":
        return cmd_scan(args)
    if args.command == "checklist":
        return cmd_checklist(args)
    if args.command == "find":
        return cmd_find(args)
    if args.command == "ghost":
        return cmd_ghost(args)
    if args.command == "writers":
        return cmd_writers(args)
    if args.command == "dead":
        return cmd_dead(args)
    if args.command == "unused":
        return cmd_unused(args)
    if args.command == "patterns":
        return cmd_patterns(args)
    if args.command == "search":
        return cmd_search(args)
    if args.command == "ui":
        run_menu(PROJECT_DIR)
        return EXIT_OK
    if args.command == "graph":
        project_root = Path(getattr(args, "project_root", ".")).resolve()
        config_path = Path(args.config).resolve() if getattr(args, "config", None) else None
        if getattr(args, "graph_cmd", None) == "build":
            return graph_build(project_root, config_path)
        if getattr(args, "graph_cmd", None) == "report":
            return graph_report(project_root, config_path)
        if getattr(args, "graph_cmd", None) == "trace":
            direction = getattr(args, "direction", "both")
            max_depth = None if getattr(args, "no_limits", False) or getattr(args, "all", False) else getattr(args, "max_depth", None)
            max_paths = None if getattr(args, "no_limits", False) or getattr(args, "all", False) else getattr(args, "max_paths", None)
            return graph_trace(
                project_root,
                config_path,
                getattr(args, "target", ""),
                direction,
                max_depth,
                max_paths,
                getattr(args, "line", False),
            )
    if args.command == "embed":
        try:
            from project_control.embedding.index_builder import build_index
            from project_control.embedding.config import EmbedConfig
            from project_control.embedding.search_engine import SearchEngine
        except ImportError as e:
            print("❌ Embedding dependencies not installed.")
            print("   Install with: pip install -e '.[embedding]'")
            print(f"   Error: {e}")
            return EXIT_VALIDATION_ERROR

        root = Path(getattr(args, "path", ".")).resolve()
        cfg = EmbedConfig()

        if getattr(args, "embed_cmd", None) == "build":
            try:
                files, chunks, dim = build_index(root, cfg, overwrite=False)
                print(f"Embedding build complete. Files: {files}, Chunks: {chunks}, Dim: {dim}")
                print(f"Index: {cfg.index_path}")
                return EXIT_OK
            except Exception as e:
                print(f"❌ Embedding build failed: {e}")
                print("   Ensure Ollama is running: ollama serve")
                print(f"   Download model: ollama pull {cfg.model}")
                return EXIT_VALIDATION_ERROR
        if getattr(args, "embed_cmd", None) == "rebuild":
            try:
                files, chunks, dim = build_index(root, cfg, overwrite=True)
                print(f"Embedding rebuild complete. Files: {files}, Chunks: {chunks}, Dim: {dim}")
                return EXIT_OK
            except Exception as e:
                print(f"❌ Embedding rebuild failed: {e}")
                return EXIT_VALIDATION_ERROR
        if getattr(args, "embed_cmd", None) == "search":
            try:
                engine = SearchEngine(cfg)
                hits = engine.search(getattr(args, "query", ""), top_k=getattr(args, "top_k", 5))
                for rank, hit in enumerate(hits, 1):
                    print(f"  {rank}. {hit['path']} (score={hit['score']:.4f})")
                return EXIT_OK
            except Exception as e:
                print(f"❌ Embedding search failed: {e}")
                return EXIT_VALIDATION_ERROR

    # Preset commands
    if args.command == "preset":
        return _handle_preset_command(args)

    # Export commands
    if args.command == "export":
        return _handle_export_command(args)

    # Import commands
    if args.command == "import":
        return _handle_import_command(args)

    # Explore command
    if args.command == "explore":
        return _handle_explore_command(args)

    print(f"Unknown command: {args.command}")
    return EXIT_VALIDATION_ERROR


# Backward compat — used by cmd_scan
def run_scan(project_root: Path) -> None:
    """Run scan with configuration."""
    patterns = load_patterns(project_root)
    snapshot = create_snapshot(project_root, patterns.get("ignore_dirs", []), patterns.get("extensions", []))
    save_snapshot(snapshot, project_root)
    print(f"Scan complete. {len(snapshot.get('files', []))} files indexed.")


# ── Preset Commands ───────────────────────────────────────────────────────

def _handle_preset_command(args: argparse.Namespace) -> int:
    """Handle preset subcommands."""
    from project_control.config.presets import PresetManager

    project_root = Path(getattr(args, "project_root", ".")).resolve()
    manager = PresetManager(project_root)

    if getattr(args, "preset_cmd", None) == "list":
        presets = manager.list_presets()
        print("Available Presets:")
        print("=" * 60)
        for preset in presets:
            category_mark = " [builtin]" if preset["category"] == "builtin" else " [custom]"
            print(f"  • {preset['name']}{category_mark}")
            print(f"    {preset['description']}")
        print()

        # Show current preset
        current = manager.get_current_preset_name()
        if current:
            print(f"Current preset: {current}")
        else:
            print("Current configuration doesn't match any preset")
        return EXIT_OK

    if getattr(args, "preset_cmd", None) == "apply":
        name = getattr(args, "name", None)
        if not name:
            print("Error: Preset name is required")
            return EXIT_VALIDATION_ERROR

        backup = not getattr(args, "no_backup", False)
        if manager.apply_preset(name, backup=backup):
            print(f"[OK] Applied preset: {name}")
            if backup:
                print("  (Backup created in .project-control/backups/)")
            return EXIT_OK
        else:
            print(f"[ERROR] Preset not found: {name}")
            return EXIT_VALIDATION_ERROR

    if getattr(args, "preset_cmd", None) == "save":
        name = getattr(args, "name", None)
        if not name:
            print("Error: Preset name is required")
            return EXIT_VALIDATION_ERROR

        description = getattr(args, "description", "") or f"Custom preset: {name}"
        if manager.save_custom_preset(name, description):
            print(f"[OK] Saved custom preset: {name}")
            print(f"  Description: {description}")
            return EXIT_OK
        else:
            print(f"[ERROR] Failed to save preset: {name}")
            return EXIT_VALIDATION_ERROR

    if getattr(args, "preset_cmd", None) == "delete":
        name = getattr(args, "name", None)
        if not name:
            print("Error: Preset name is required")
            return EXIT_VALIDATION_ERROR

        if manager.delete_custom_preset(name):
            print(f"[OK] Deleted custom preset: {name}")
            return EXIT_OK
        else:
            print(f"[ERROR] Cannot delete preset '{name}' (not found or is built-in)")
            return EXIT_VALIDATION_ERROR

    print("Error: No preset subcommand specified")
    print("Use: pc preset {list|apply|save|delete}")
    return EXIT_VALIDATION_ERROR


# ── Export Commands ───────────────────────────────────────────────────────

def _handle_export_command(args: argparse.Namespace) -> int:
    """Handle export subcommands."""
    from project_control.persistence.state_manager import StateManager

    project_root = Path(getattr(args, "project_root", ".")).resolve()
    manager = StateManager(project_root)

    if getattr(args, "export_cmd", None) == "state":
        export_path = getattr(args, "path", None)
        if export_path:
            export_path = Path(export_path).resolve()

        include_metadata = not getattr(args, "no_metadata", False)

        try:
            result_path = manager.export_state(export_path, include_metadata=include_metadata)
            print(f"[OK] State exported to: {result_path}")
            return EXIT_OK
        except Exception as e:
            print(f"[ERROR] Export failed: {e}")
            return EXIT_VALIDATION_ERROR

    print("Error: No export subcommand specified")
    print("Use: pc export {state}")
    return EXIT_VALIDATION_ERROR


# ── Import Commands ───────────────────────────────────────────────────────

def _handle_import_command(args: argparse.Namespace) -> int:
    """Handle import subcommands."""
    from project_control.persistence.state_manager import StateManager

    project_root = Path(getattr(args, "project_root", ".")).resolve()
    manager = StateManager(project_root)

    if getattr(args, "import_cmd", None) == "state":
        import_path = Path(getattr(args, "path", None))
        if not import_path or not import_path.exists():
            print(f"[ERROR] Import file not found: {import_path}")
            return EXIT_VALIDATION_ERROR

        merge = getattr(args, "merge", False)

        try:
            manager.import_state(import_path, merge=merge)
            mode = "merged" if merge else "imported"
            print(f"[OK] State {mode} from: {import_path}")
            return EXIT_OK
        except Exception as e:
            print(f"[ERROR] Import failed: {e}")
            return EXIT_VALIDATION_ERROR

    print("Error: No import subcommand specified")
    print("Use: pc import {state}")
    return EXIT_VALIDATION_ERROR


# ── Explore Command ───────────────────────────────────────────────────────

def _handle_explore_command(args: argparse.Namespace) -> int:
    """Handle explore command."""
    from project_control.ui.file_explorer import FileExplorer

    project_root = Path(getattr(args, "project_root", ".")).resolve()
    start_path = Path(getattr(args, "path", ".")).resolve()

    # Resolve start_path relative to project_root if needed
    try:
        start_path = start_path.relative_to(project_root)
    except ValueError:
        # If not relative, use as-is if it's within project_root
        if not str(start_path).startswith(str(project_root)):
            print(f"[ERROR] Path must be within project root: {project_root}")
            return EXIT_VALIDATION_ERROR

    start_path = project_root / start_path

    try:
        explorer = FileExplorer(project_root)

        if start_path.is_dir():
            explorer.change_directory(str(start_path.relative_to(project_root)))
            output = explorer.render_file_list()
            _safe_print(output)
        elif start_path.is_file():
            rel_path = str(start_path.relative_to(project_root))
            output = explorer.render_file_details(rel_path)
            _safe_print(output)
        else:
            print(f"[ERROR] Path not found: {start_path}")
            return EXIT_VALIDATION_ERROR

        return EXIT_OK
    except Exception as e:
        print(f"[ERROR] Explore failed: {e}")
        return EXIT_VALIDATION_ERROR


def _safe_print(text: str) -> None:
    """Print text safely, handling Unicode encoding issues on Windows."""
    import sys
    try:
        print(text)
    except UnicodeEncodeError:
        # Fallback for Windows console with limited encoding
        if sys.platform == "win32":
            # Encode with error replacement
            safe_text = text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
            print(safe_text)
        else:
            # For other platforms, try UTF-8
            try:
                print(text.encode("utf-8", errors="replace").decode("utf-8"))
            except Exception:
                print(text.encode("ascii", errors="replace").decode("ascii"))
