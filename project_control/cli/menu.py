"""Menu-first interactive CLI."""

from __future__ import annotations

import os
from pathlib import Path

from project_control.ui.state import AppState, load_state, save_state
from project_control.services.scan_service import run_scan
from project_control.services.graph_service import build_graph, show_report
from project_control.services.analyze_service import ghost_fast, ghost_structural
from project_control.services.explore_service import run_trace


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


def run_menu(project_root: Path) -> None:
    state = load_state(project_root)
    while True:
        clear_screen()
        _header(project_root, state)
        print("1) Snapshot")
        print("2) Graph")
        print("3) Analyze")
        print("4) Explore")
        print("5) Settings")
        print("6) Exit")
        choice = input("\nSelect option (1-6): ").strip()
        if choice == "1":
            _snapshot_menu(project_root, state)
        elif choice == "2":
            _graph_menu(project_root, state)
        elif choice == "3":
            _analyze_menu(project_root, state)
        elif choice == "4":
            _explore_menu(project_root, state)
        elif choice == "5":
            state = _settings_menu(project_root, state)
        elif choice == "6":
            save_state(project_root, state)
            print("Goodbye.")
            return
        else:
            input("Invalid selection. Press Enter...")


def _header(project_root: Path, state: AppState) -> None:
    print("---------------------------------------")
    print("PROJECT CONTROL")
    print("---------------------------------------")
    print(f"Project: {project_root}")
    print(f"Mode: {state.project_mode} | Profile: {state.graph_profile} | Trace: {state.trace_direction}/{state.trace_depth}/all={state.trace_all_paths}")
    print()


def _confirm(summary: str) -> bool:
    print(summary)
    resp = input("Proceed? [y/N]: ").strip().lower()
    return resp == "y"


def _snapshot_menu(project_root: Path, state: AppState) -> None:
    if _confirm("Run snapshot (scan project)?"):
        run_scan(project_root)
    input("Press Enter to continue...")


def _graph_menu(project_root: Path, state: AppState) -> None:
    print("Graph actions:")
    print("1) Build/Rebuild graph")
    print("2) Show graph report")
    choice = input("Select (1-2): ").strip()
    if choice == "1":
        if _confirm("Build graph using current config?"):
            build_graph(project_root, state)
    elif choice == "2":
        if _confirm("Show graph report (reuse if fresh)?"):
            show_report(project_root, state)
    input("Press Enter to continue...")


def _analyze_menu(project_root: Path, state: AppState) -> None:
    print("Analyze:")
    print("1) Ghost detectors (shallow)")
    print("2) Structural (graph metrics)")
    choice = input("Select (1-2): ").strip()
    if choice == "1":
        if _confirm("Run ghost detectors (no deep graph)?"):
            ghost_fast(project_root)
    elif choice == "2":
        if _confirm("Analyze structural metrics from graph?"):
            ghost_structural(project_root, state)
    input("Press Enter to continue...")


def _explore_menu(project_root: Path, state: AppState) -> None:
    target = input("Trace target (path or symbol): ").strip()
    if not target:
        input("No target. Press Enter...")
        return
    summary = f"Trace {target} dir={state.trace_direction} depth={state.trace_depth} all={state.trace_all_paths}"
    if _confirm(summary):
        run_trace(project_root, target, state)
    input("Press Enter to continue...")


def _settings_menu(project_root: Path, state: AppState) -> AppState:
    print("Settings:")
    mode = input(f"Mode [js_ts/python/mixed] ({state.project_mode}): ").strip() or state.project_mode
    profile = input(f"Graph profile [pragmatic/strict] ({state.graph_profile}): ").strip() or state.graph_profile
    direction = input(f"Trace direction [inbound/outbound/both] ({state.trace_direction}): ").strip() or state.trace_direction
    depth = input(f"Trace depth ({state.trace_depth}): ").strip()
    all_paths = input(f"Trace all paths? [y/N] ({'y' if state.trace_all_paths else 'n'}): ").strip().lower()
    new_state = AppState(
        project_mode=mode,
        graph_profile=profile,
        trace_direction=direction,
        trace_depth=int(depth) if depth else state.trace_depth,
        trace_all_paths=all_paths == "y" if all_paths else state.trace_all_paths,
    )
    save_state(project_root, new_state)
    return new_state
