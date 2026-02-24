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
from project_control.ui import launch_ui

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
    patterns = load_patterns(PROJECT_DIR)

    snapshot = create_snapshot(
        PROJECT_DIR,
        patterns.get("ignore_dirs", []),
        patterns.get("extensions", []),
    )
    save_snapshot(snapshot, PROJECT_DIR)

    print(f"Scan complete. {snapshot['file_count']} files indexed.")
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
    try:
        result = run_ghost(args, PROJECT_DIR)
    except SystemExit as exc:
        return int(exc.code)

    if result is None:
        return EXIT_OK
    dto = result["dto"]
    validation_section = dto.get("validation") or {}

    if args.stats:
        print("\nGhost Stats")
        print("-----------")
        if args.deep:
            print(f"Import graph orphans (CRITICAL): {len(validation_section.get('graph_orphans', []))}")
        print(f"Orphans (HIGH): {len(validation_section.get('orphans', []))}")
        print(f"Legacy snippets (MEDIUM): {len(validation_section.get('legacy', []))}")
        print(f"Session files (LOW): {len(validation_section.get('session', []))}")
        print(f"Duplicates (INFO): {len(validation_section.get('duplicates', []))}")
        return EXIT_OK

    if result["limit_violation"]:
        print(result["limit_violation"]["message"])
        return int(result["limit_violation"]["exit_code"])

    write_ghost_reports(result, PROJECT_DIR, args)

    if not (args.deep and args.tree_only):
        print(f"Smart ghost report saved: {PROJECT_DIR / result['ghost_report_path']}")
    if args.deep and result["deep_report_path"] is not None:
        print(f"Import graph report saved: {PROJECT_DIR / result['deep_report_path']}")

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
        launch_ui(PROJECT_DIR)
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
    return EXIT_OK
