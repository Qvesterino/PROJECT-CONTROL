"""CLI router that delegates commands to core services."""

from __future__ import annotations

import argparse
import yaml
from pathlib import Path
from typing import Optional

from project_control.config.patterns_loader import load_patterns
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR
from project_control.core.ghost_service import run_ghost, write_ghost_report
from project_control.core.markdown_renderer import render_writer_report
from project_control.core.snapshot_service import create_snapshot, load_snapshot, save_snapshot
from project_control.core.writers import run_writers_analysis
from project_control.utils.fs_helpers import run_rg
from project_control.cli.graph_cmd import graph_build, graph_report, graph_trace
from project_control.cli.menu import run_menu

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
    ensure_control_dirs()
    run_scan(PROJECT_DIR)
    return EXIT_OK


def cmd_checklist(args: argparse.Namespace) -> int:
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


def cmd_find(args: argparse.Namespace) -> int:
    if not args.symbol:
        print("Provide symbol to search.")
        return EXIT_VALIDATION_ERROR

    ensure_control_dirs()

    result = run_rg(args.symbol)
    output_path = EXPORTS_DIR / f"find_{args.symbol}.md"

    output_path.write_text(
        f"# Usage of: {args.symbol}\n\n{result or 'No matches found.'}",
        encoding="utf-8",
    )

    print(f"Search results saved: {output_path}")
    return EXIT_OK


def cmd_ghost(args: argparse.Namespace) -> int:
    """Run shallow ghost analysis using canonical ghost core."""
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


def cmd_writers(args: argparse.Namespace) -> int:
    ensure_control_dirs()

    results = run_writers_analysis(PROJECT_DIR)
    output_path = EXPORTS_DIR / "writers_report.md"
    render_writer_report(results, str(output_path))

    print(f"Writers report saved: {output_path}")
    return EXIT_OK


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

    print(f"Unknown command: {args.command}")
    return EXIT_VALIDATION_ERROR


# Backward compat — used by cmd_scan
def run_scan(project_root: Path) -> None:
    from project_control.core.scanner import scan_project
    snapshot = scan_project(project_root)
    save_snapshot(snapshot, project_root)
    print(f"Scan complete. {len(snapshot.get('files', []))} files indexed.")
