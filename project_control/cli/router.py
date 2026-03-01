"""CLI router that delegates commands to core services/usecases."""

from __future__ import annotations

import argparse
import yaml
from pathlib import Path
from typing import Optional

from project_control.config.patterns_loader import load_patterns
from project_control.core.exit_codes import EXIT_OK, EXIT_VALIDATION_ERROR
from project_control.core.ghost_service import run_ghost, write_ghost_reports
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


def cmd_init(args: argparse.Namespace) -> int:
    ensure_control_dirs()

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
    # Shallow ghost only
    try:
        result = run_ghost(args, PROJECT_DIR)
    except SystemExit as exc:
        return int(exc.code)
    if result is None:
        return EXIT_OK
    dto = result["dto"]
    validation_section = dto.get("validation") or {}

    print("\nGhost Results (shallow)")
    print("-----------------------")
    print(f"Orphans: {len(validation_section.get('orphans', []))}")
    print(f"Legacy: {len(validation_section.get('legacy', []))}")
    print(f"Session: {len(validation_section.get('session', []))}")
    print(f"Duplicates: {len(validation_section.get('duplicates', []))}")
    print(f"Semantic findings: {len(validation_section.get('semantic_findings', []))}")
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
        if getattr(args, "deprecated_deep", False):
            print("Deprecated: ghost deep legacy graph removed; running shallow detectors instead.")
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
        from project_control.embedding.index_builder import build_index
        from project_control.embedding.config import EmbedConfig
        from project_control.embedding.search_engine import SearchEngine

        root = Path(getattr(args, "path", ".")).resolve()
        cfg = EmbedConfig()

        if getattr(args, "embed_cmd", None) == "build":
            files, chunks, dim = build_index(root, cfg, overwrite=False)
            print(f"Embedding build complete. Files: {files}, Chunks: {chunks}, Dim: {dim}")
            print(f"Index: {cfg.index_path}")
            return EXIT_OK
        if getattr(args, "embed_cmd", None) == "rebuild":
            files, chunks, dim = build_index(root, cfg, overwrite=True)
            print(f"Embedding rebuild complete. Files: {files}, Chunks: {chunks}, Dim: {dim}")
            print(f"Index: {cfg.index_path}")
            return EXIT_OK
        if getattr(args, "embed_cmd", None) == "search":
            engine = SearchEngine(root, cfg)
            top_k = getattr(args, "top_k", 5)
            results = engine.search(getattr(args, "query", ""), top_k=top_k)
            for res in results:
                print(f"{res.file_path}:{res.start_offset}-{res.end_offset} score={res.similarity_score:.3f}")
                print(res.preview_text)
            return EXIT_OK
    return EXIT_OK
