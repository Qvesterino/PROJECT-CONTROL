#!/usr/bin/env python3
"""
PROJECT CONTROL CLI entrypoint.
Parses arguments and dispatches to router.
"""

from __future__ import annotations

import argparse
from pathlib import Path
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
        "--deprecated-deep",
        action="store_true",
        help="Deprecated: no-op; legacy ghost deep removed.",
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
