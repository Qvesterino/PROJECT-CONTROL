#!/usr/bin/env python3
"""
PROJECT CONTROL CLI entrypoint.
Parses arguments and dispatches to router.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from project_control.cli.router import dispatch
from project_control import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="PROJECT CONTROL - Deterministic architectural analysis engine",
        epilog="Find dead code. Understand your architecture. Stop guessing."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}"
    )
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init")
    subparsers.add_parser("scan")
    subparsers.add_parser("checklist")

    # New diagnostic commands
    dead_parser = subparsers.add_parser("dead", help="Dead Code Radar - finds unused files")
    dead_parser.add_argument("--threshold", type=int, default=2, help="Max usage count for low-usage files")
    dead_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    dead_parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    unused_parser = subparsers.add_parser("unused", help="Unused System Scan - finds unused systems")
    unused_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    unused_parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    patterns_parser = subparsers.add_parser("patterns", help="Suspicious Patterns - detects forbidden patterns")
    patterns_parser.add_argument("--file", type=str, help="Path to patterns YAML file")
    patterns_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    patterns_parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    search_parser = subparsers.add_parser("search", help="Smart Search - power-user code search")
    search_parser.add_argument("pattern", nargs="+", help="Pattern(s) to search for")
    search_parser.add_argument("--not", action="store_true", dest="invert", help="Find files that DO NOT match")
    search_parser.add_argument("--files-only", action="store_true", help="Return only file paths")
    search_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    search_parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    find_parser = subparsers.add_parser("find")
    find_parser.add_argument("symbol", nargs="?")

    ghost_parser = subparsers.add_parser("ghost")
    ghost_parser.add_argument("--mode", choices=["strict", "pragmatic"], default="pragmatic")
    ghost_parser.add_argument("--max-high", type=int, default=-1)
    ghost_parser.add_argument("--max-medium", type=int, default=-1)
    ghost_parser.add_argument("--max-low", type=int, default=-1)
    ghost_parser.add_argument("--max-info", type=int, default=-1)
    ghost_parser.add_argument("--tree", action="store_true", help="Export results as ASCII tree files")

    subparsers.add_parser("writers")

    graph_parser = subparsers.add_parser("graph")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_cmd")

    graph_build_parser = graph_subparsers.add_parser("build")
    graph_build_parser.add_argument("project_root", nargs="?", default=".")
    graph_build_parser.add_argument("--config", type=str, help="Path to graph config YAML", default=None)

    graph_report_parser = graph_subparsers.add_parser("report")
    graph_report_parser.add_argument("project_root", nargs="?", default=".")
    graph_report_parser.add_argument("--config", type=str, help="Path to graph config YAML", default=None)

    graph_trace_parser = graph_subparsers.add_parser("trace")
    graph_trace_parser.add_argument("target")
    graph_trace_parser.add_argument("--all", action="store_true", help="Show all paths (alias for --no-limits)")
    graph_trace_parser.add_argument("--line", action="store_true", help="Include line-level context for each hop")
    graph_trace_parser.add_argument(
        "--direction",
        choices=["inbound", "outbound", "both"],
        default="both",
        help="Traversal direction for trace",
    )
    graph_trace_parser.add_argument("--max-depth", type=int, default=10, help="Limit traversal depth")
    graph_trace_parser.add_argument("--max-paths", type=int, default=50, help="Limit number of returned paths")
    graph_trace_parser.add_argument("--no-limits", action="store_true", help="Disable depth/path limits")
    graph_trace_parser.add_argument("--config", type=str, help="Path to graph config YAML", default=None)

    subparsers.add_parser("ui")

    # Preset management
    preset_parser = subparsers.add_parser("preset", help="Manage project presets")
    preset_subparsers = preset_parser.add_subparsers(dest="preset_cmd")

    preset_list_parser = preset_subparsers.add_parser("list", help="List all available presets")
    preset_list_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")

    preset_apply_parser = preset_subparsers.add_parser("apply", help="Apply a preset")
    preset_apply_parser.add_argument("name", help="Preset name to apply")
    preset_apply_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")
    preset_apply_parser.add_argument("--no-backup", action="store_true", help="Skip creating backup")

    preset_save_parser = preset_subparsers.add_parser("save", help="Save custom preset")
    preset_save_parser.add_argument("name", help="Preset name")
    preset_save_parser.add_argument("--description", help="Preset description")
    preset_save_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")

    preset_delete_parser = preset_subparsers.add_parser("delete", help="Delete custom preset")
    preset_delete_parser.add_argument("name", help="Preset name to delete")
    preset_delete_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")

    # State export/import
    export_parser = subparsers.add_parser("export", help="Export project state")
    export_subparsers = export_parser.add_subparsers(dest="export_cmd")

    export_state_parser = export_subparsers.add_parser("state", help="Export state to file")
    export_state_parser.add_argument("--path", help="Export path (default: .project-control/exports/state.<timestamp>.json)")
    export_state_parser.add_argument("--no-metadata", action="store_true", help="Exclude project-specific metadata")
    export_state_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")

    import_parser = subparsers.add_parser("import", help="Import project state")
    import_subparsers = import_parser.add_subparsers(dest="import_cmd")

    import_state_parser = import_subparsers.add_parser("state", help="Import state from file")
    import_state_parser.add_argument("path", help="Import file path")
    import_state_parser.add_argument("--merge", action="store_true", help="Merge with existing state instead of replacing")
    import_state_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")

    # File explorer
    explore_parser = subparsers.add_parser("explore", help="Interactive file explorer")
    explore_parser.add_argument("path", nargs="?", default=".", help="Starting path")
    explore_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")

    embed_parser = subparsers.add_parser("embed")
    embed_sub = embed_parser.add_subparsers(dest="embed_cmd")
    embed_build = embed_sub.add_parser("build")
    embed_build.add_argument("path", nargs="?", default=".")
    embed_rebuild = embed_sub.add_parser("rebuild")
    embed_rebuild.add_argument("path", nargs="?", default=".")
    embed_search = embed_sub.add_parser("search")
    embed_search.add_argument("query")
    embed_search.add_argument("path", nargs="?", default=".")
    embed_search.add_argument("--top-k", type=int, default=5)
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        from project_control.cli.menu import run_menu
        run_menu(Path.cwd())
        return
    exit_code = dispatch(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
