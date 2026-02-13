#!/usr/bin/env python3
"""
PROJECT CONTROL v1.3 - Smart Ghost Detection v2
------------------------------------------------
Uses modular components for scanning, analysis, and reporting.
"""

import argparse
import json
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from config.patterns_loader import load_patterns
from core.scanner import scan_project
from core.snapshot import load_snapshot
from core.ghost import analyze_ghost
from core.markdown_renderer import render_ghost_report, render_writer_report
from core.writers import run_writers_analysis
from utils.fs_helpers import run_rg

PROJECT_DIR = Path.cwd()
CONTROL_DIR = PROJECT_DIR / ".project-control"
EXPORTS_DIR = CONTROL_DIR / "exports"
SNAPSHOT_FILE = CONTROL_DIR / "snapshot.json"
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


def cmd_init(args: argparse.Namespace) -> None:
    ensure_control_dirs()

    if not PATTERNS_FILE.exists():
        with PATTERNS_FILE.open("w", encoding="utf-8") as f:
            yaml.dump(DEFAULT_PATTERNS, f)

    if not STATUS_FILE.exists():
        with STATUS_FILE.open("w", encoding="utf-8") as f:
            yaml.dump({"tags": {}}, f)

    print("PROJECT CONTROL initialized.")


def cmd_scan(args: argparse.Namespace) -> None:
    ensure_control_dirs()
    patterns = load_patterns(PROJECT_DIR)

    snapshot = scan_project(
        PROJECT_DIR,
        patterns.get("ignore_dirs", []),
        patterns.get("extensions", []),
    )
    snapshot["generated_at"] = datetime.now(timezone.utc).isoformat()

    with SNAPSHOT_FILE.open("w", encoding="utf-8") as f:
        json.dump(snapshot, f, indent=2)

    print(f"Scan complete. {snapshot['file_count']} files indexed.")


def cmd_checklist(args: argparse.Namespace) -> None:
    snapshot = _load_existing_snapshot()
    if snapshot is None:
        return

    ensure_control_dirs()

    output = ["# PROJECT CHECKLIST\n"]
    for file in snapshot["files"]:
        output.append(f"- [ ] {file['path']}")

    checklist_path = EXPORTS_DIR / "checklist.md"
    checklist_path.write_text("\n".join(output), encoding="utf-8")

    print(f"Checklist generated: {checklist_path}")


def cmd_find(args: argparse.Namespace) -> None:
    if not args.symbol:
        print("Provide symbol to search.")
        return

    ensure_control_dirs()

    result = run_rg(args.symbol)
    output_path = EXPORTS_DIR / f"find_{args.symbol}.md"

    output_path.write_text(
        f"# Usage of: {args.symbol}\n\n{result or 'No matches found.'}",
        encoding="utf-8",
    )

    print(f"Search results saved: {output_path}")


def cmd_ghost(args: argparse.Namespace) -> None:
    snapshot = _load_existing_snapshot()
    if snapshot is None:
        return

    ensure_control_dirs()
    patterns = load_patterns(PROJECT_DIR)

    result = analyze_ghost(snapshot, patterns)
    output_path = EXPORTS_DIR / "ghost_candidates.md"
    render_ghost_report(result, str(output_path))

    print(f"Smart ghost report saved: {output_path}")


def cmd_writers(args: argparse.Namespace) -> None:
    ensure_control_dirs()

    results = run_writers_analysis(PROJECT_DIR)
    output_path = EXPORTS_DIR / "writers_report.md"
    render_writer_report(results, str(output_path))

    print(f"Writers report saved: {output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="PROJECT CONTROL CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init")
    subparsers.add_parser("scan")
    subparsers.add_parser("checklist")

    find_parser = subparsers.add_parser("find")
    find_parser.add_argument("symbol", nargs="?")

    subparsers.add_parser("ghost")
    subparsers.add_parser("writers")

    args = parser.parse_args()

    if args.command == "init":
        cmd_init(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "checklist":
        cmd_checklist(args)
    elif args.command == "find":
        cmd_find(args)
    elif args.command == "ghost":
        cmd_ghost(args)
    elif args.command == "writers":
        cmd_writers(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
