#!/usr/bin/env python3
"""
PROJECT CONTROL CLI entrypoint.
Parses arguments and dispatches to router.
"""

from __future__ import annotations

import argparse
from project_control.cli.router import dispatch


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PROJECT CONTROL CLI")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init")
    subparsers.add_parser("scan")
    subparsers.add_parser("checklist")

    find_parser = subparsers.add_parser("find")
    find_parser.add_argument("symbol", nargs="?")

    ghost_parser = subparsers.add_parser("ghost")
    ghost_parser.add_argument(
        "--deep",
        action="store_true",
        help="Run deep import graph analysis (slow)",
    )
    ghost_parser.add_argument(
        "--stats",
        action="store_true",
        help="Print only statistics without generating markdown report",
    )
    ghost_parser.add_argument(
        "--tree-only",
        action="store_true",
        help="Write only the tree view section to import_graph_orphans.md (no flat list)",
    )
    ghost_parser.add_argument(
        "--export-graph",
        action="store_true",
        help="Export the combined import graph in DOT and Mermaid formats when running deep analysis",
    )
    ghost_parser.add_argument(
        "--mode",
        choices=["strict", "pragmatic"],
        default="pragmatic",
        help="Ghost detection mode: strict = no ignore patterns, pragmatic = apply ignore patterns",
    )
    ghost_parser.add_argument("--max-high", type=int, default=-1, help="Fail if high-severity count exceeds this value.")
    ghost_parser.add_argument("--max-medium", type=int, default=-1, help="Fail if medium-severity count exceeds this value.")
    ghost_parser.add_argument("--max-low", type=int, default=-1, help="Fail if low-severity count exceeds this value.")
    ghost_parser.add_argument("--max-info", type=int, default=-1, help="Fail if info-severity count exceeds this value.")
    ghost_parser.add_argument(
        "--compare-snapshot",
        type=str,
        help="Path to previous snapshot JSON for architectural drift comparison (requires --deep)",
    )
    ghost_parser.add_argument(
        "--validate-architecture",
        action="store_true",
        help="Validate analysis layer boundaries before running ghost",
    )
    ghost_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug output for deep analysis and validation",
    )
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
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return
    exit_code = dispatch(args)
    raise SystemExit(exit_code)


if __name__ == "__main__":
    main()
