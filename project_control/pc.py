#!/usr/bin/env python3
"""
PROJECT CONTROL CLI entrypoint.
Parses arguments and dispatches to router.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from project_control.cli.router import dispatch
from project_control import __version__


def _add_tui_subcommands(parser: argparse.ArgumentParser, dest: str) -> None:
    """Attach shared TUI subcommands to a parser."""
    subparsers = parser.add_subparsers(dest=dest)

    subparsers.add_parser("menu", help="Launch the TUI text-based menu")

    verify_parser = subparsers.add_parser("verify", help="Run configurable browser-based UI verification")
    verify_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")
    verify_parser.add_argument("--config", help="Path to the UI verification YAML profile")
    verify_parser.add_argument("--profile", help="Discovered UI verification profile name")
    verify_parser.add_argument("--list-profiles", action="store_true", help="List discovered UI verification profiles")
    verify_parser.add_argument("--url", help="Override the profile base URL")
    verify_parser.add_argument("--image", help="Override the configured test image path")
    verify_parser.add_argument("--screenshots", help="Directory for screenshots")
    verify_parser.add_argument("--output", help="Output directory for reports")
    verify_parser.add_argument("--html", action="store_true", help="Generate HTML dashboard output")
    verify_parser.add_argument("--json", action="store_true", help="Print structured JSON to stdout")
    verify_parser.add_argument("--headless", action="store_true", default=True, help="Run browser headless")
    verify_parser.add_argument("--no-headless", action="store_false", dest="headless", help="Show browser window")


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
    
    # Quick analysis commands
    quick_parser = subparsers.add_parser("quick", help="Quick analysis - scan, find issues, and build dependencies")
    quick_parser.add_argument("--health", action="store_true", help="Run health check only")
    quick_parser.add_argument("--orphans", action="store_true", help="Find orphans only")
    quick_parser.add_argument("--tree", action="store_true", help="Export results as ASCII tree files")

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

    nebula_parser = subparsers.add_parser("nebula", help="Codebase Nebula bridge commands")
    nebula_parser.add_argument("--project-root", help="Project root path")
    nebula_subparsers = nebula_parser.add_subparsers(dest="nebula_cmd")
    nebula_subparsers.add_parser("export", help="Export the locked nebula_bridge.json artifact")

    search_parser = subparsers.add_parser("search", help="Smart Search - power-user code search")
    search_parser.add_argument("pattern", nargs="+", help="Pattern(s) to search for")
    search_parser.add_argument("--not", action="store_true", dest="invert", help="Find files that DO NOT match")
    search_parser.add_argument("--files-only", action="store_true", help="Return only file paths")
    search_parser.add_argument("--json", action="store_true", help="Output in JSON format")
    search_parser.add_argument("--no-color", action="store_true", help="Disable colored output")

    find_parser = subparsers.add_parser("find")
    find_parser.add_argument("symbol", nargs="?")

    audit_parser = subparsers.add_parser("audit", help="Run architecture and contract audits")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_cmd")

    audit_vfx_parser = audit_subparsers.add_parser("vfx", help="VFX contract audit for FX-oriented JavaScript files")
    audit_vfx_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")
    audit_vfx_parser.add_argument("--output", help="Output directory for reports")
    audit_vfx_parser.add_argument("--json", action="store_true", help="Print JSON to stdout")

    audits_parser = subparsers.add_parser("audits", help="Retention and hygiene workflows for generated audits")
    audits_subparsers = audits_parser.add_subparsers(dest="audits_cmd")
    audits_retention_parser = audits_subparsers.add_parser("retention", help="Audit Retention Engine - find stale generated audits and reports")
    audits_retention_parser.add_argument("--older-than", type=int, dest="older_than", help="Override audit_retention.older_than_days for this run")
    audits_retention_parser.add_argument("--min-score", type=int, dest="min_score", help="Override audit_retention.min_score for this run")
    audits_retention_parser.add_argument("--keep-latest", type=int, dest="keep_latest", help="Override audit_retention.keep_latest_per_family for this run")
    audits_retention_parser.add_argument("--by-family", action="store_true", help="Include grouped-by-family summary in console output")
    audits_retention_output_group = audits_retention_parser.add_mutually_exclusive_group()
    audits_retention_output_group.add_argument("--json", action="store_true", help="Print audit retention JSON payload to stdout")
    audits_retention_output_group.add_argument("--delete-list", action="store_true", help="Print delete candidate paths to stdout")

    ghost_parser = subparsers.add_parser("ghost")
    ghost_parser.add_argument("--mode", choices=["strict", "pragmatic"], default="pragmatic")
    ghost_parser.add_argument("--max-high", type=int, default=-1)
    ghost_parser.add_argument("--max-medium", type=int, default=-1)
    ghost_parser.add_argument("--max-low", type=int, default=-1)
    ghost_parser.add_argument("--max-info", type=int, default=-1)
    ghost_parser.add_argument("--tree", action="store_true", help="Export results as ASCII tree files")

    artifacts_parser = subparsers.add_parser("artifacts", help="Artifact Hygiene Engine - find temporary visual assets")
    artifacts_parser.add_argument("--older-than", type=int, dest="older_than", help="Override artifacts.older_than_days for this run")
    artifacts_parser.add_argument("--min-score", type=int, dest="min_score", help="Override artifacts.min_score for this run")
    artifacts_parser.add_argument("--by-resolution", action="store_true", help="Include grouped-by-resolution summary in console output")
    artifacts_output_group = artifacts_parser.add_mutually_exclusive_group()
    artifacts_output_group.add_argument("--json", action="store_true", help="Print artifact JSON payload to stdout")
    artifacts_output_group.add_argument("--delete-list", action="store_true", help="Print delete candidate paths to stdout")

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

    tui_parser = subparsers.add_parser("tui", help="TUI and UI verification tools")
    _add_tui_subcommands(tui_parser, "tui_cmd")

    gui_parser = subparsers.add_parser("gui", help="Launch the desktop Tkinter GUI")
    gui_parser.add_argument("project_root", nargs="?", default=".", help="Project root path")

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

    # Setup wizard
    wizard_parser = subparsers.add_parser("wizard", help="Interactive setup wizard for first-time configuration")
    wizard_parser.add_argument("--project-root", nargs="?", default=".", help="Project root path")
    wizard_parser.add_argument("--reset", action="store_true", help="Force wizard to run even if already configured")

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


def _removed_ui_message(raw_args: list[str]) -> str | None:
    """Return a migration message when a removed `pc ui*` command is used."""
    if not raw_args or raw_args[0] != "ui":
        return None

    replacement = "pc tui"
    if len(raw_args) >= 2 and raw_args[1] == "verify":
        replacement = "pc tui verify"
    elif len(raw_args) >= 2 and raw_args[1] == "menu":
        replacement = "pc tui menu"

    return f"pc ui was removed in this release. Use '{replacement}' instead."


def main() -> None:
    migration_message = _removed_ui_message(sys.argv[1:])
    if migration_message is not None:
        print(migration_message, file=sys.stderr)
        raise SystemExit(2)

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
