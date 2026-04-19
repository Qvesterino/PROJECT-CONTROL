"""Menu-first interactive CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path

from project_control.ui.state import AppState, load_state, save_state
from project_control.services.scan_service import run_scan
from project_control.services.graph_service import build_graph, show_report
from project_control.services.analyze_service import ghost_fast, ghost_structural
from project_control.services.explore_service import run_trace


def clear_screen() -> None:
    os.system("cls" if os.name == "nt" else "clear")


# ── Labels ──────────────────────────────────────────────────────────

MODE_LABELS = {"js_ts": "JS/TS", "python": "Python", "mixed": "Mixed"}
PROFILE_LABELS = {"pragmatic": "Pragmatic", "strict": "Strict"}
DIRECTION_LABELS = {"inbound": "Inbound", "outbound": "Outbound", "both": "Both"}


# ── Status helpers ──────────────────────────────────────────────────

def _snapshot_status(project_root: Path) -> str:
    path = project_root / ".project-control" / "snapshot.json"
    if not path.exists():
        return "MISSING"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        count = data.get("file_count", "?")
        return f"OK ({count} files)"
    except Exception:
        return "ERROR"


def _graph_status(project_root: Path) -> str:
    path = project_root / ".project-control" / "out" / "graph.snapshot.json"
    if not path.exists():
        return "MISSING"
    return "OK"


# ── Main loop ───────────────────────────────────────────────────────

def run_menu(project_root: Path) -> None:
    state = load_state(project_root)
    while True:
        clear_screen()
        _header(project_root, state)
        print("1) Snapshot  — scan project files")
        print("2) Graph     — build & view dependency graph")
        print("3) Analyze   — ghost detectors & structural metrics")
        print("4) Explore   — trace symbol/file dependencies")
        print("5) Settings  — change mode, profile, trace options")
        print("0) Exit")
        choice = input("\nSelect (0-5): ").strip()
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
        elif choice == "0":
            save_state(project_root, state)
            print("Goodbye.")
            return
        else:
            input("Invalid selection. Press Enter...")


def _header(project_root: Path, state: AppState) -> None:
    mode_label = MODE_LABELS.get(state.project_mode, state.project_mode)
    print("=======================================")
    print("  PROJECT CONTROL")
    print("=======================================")
    print(f"  Project:  {project_root.name}")
    print(f"  Mode:     {mode_label}")
    print(f"  Snapshot: {_snapshot_status(project_root)}")
    print(f"  Graph:    {_graph_status(project_root)}")
    print("=======================================")
    print()


# ── Sub-menus ───────────────────────────────────────────────────────

def _snapshot_menu(project_root: Path, state: AppState) -> None:
    print()
    if _confirm("Scan project files?"):
        run_scan(project_root)
    input("\nPress Enter to return...")


def _graph_menu(project_root: Path, state: AppState) -> None:
    print("\nGraph:")
    print("1) Build / Rebuild graph")
    print("2) Show graph report")
    print("0) Back")
    choice = input("\nSelect (0-2): ").strip()
    if choice == "1":
        if _confirm("Build graph with current config?"):
            build_graph(project_root, state)
    elif choice == "2":
        show_report(project_root, state)
    input("\nPress Enter to return...")


def _analyze_menu(project_root: Path, state: AppState) -> None:
    print("\nAnalyze:")
    print("1) Ghost detectors (shallow)")
    print("2) Structural metrics (from graph)")
    print("0) Back")
    choice = input("\nSelect (0-2): ").strip()
    if choice == "1":
        ghost_fast(project_root)
    elif choice == "2":
        ghost_structural(project_root, state)
    input("\nPress Enter to return...")


def _explore_menu(project_root: Path, state: AppState) -> None:
    print("\nTrace:")
    dir_label = DIRECTION_LABELS.get(state.trace_direction, state.trace_direction)
    print(f"  Current: direction={dir_label}, depth={state.trace_depth}, all={state.trace_all_paths}")
    print()
    target = input("Target (path or symbol, 0=back): ").strip()
    if not target or target == "0":
        return
    run_trace(project_root, target, state)
    input("\nPress Enter to return...")


# ── Settings ────────────────────────────────────────────────────────

def _settings_menu(project_root: Path, state: AppState) -> AppState:
    while True:
        mode_label = MODE_LABELS.get(state.project_mode, state.project_mode)
        profile_label = PROFILE_LABELS.get(state.graph_profile, state.graph_profile)
        dir_label = DIRECTION_LABELS.get(state.trace_direction, state.trace_direction)

        print("\nSettings:")
        print(f"1) Mode:           {mode_label}")
        print(f"2) Graph profile:  {profile_label}")
        print(f"3) Trace direction: {dir_label}")
        print(f"4) Trace depth:    {state.trace_depth}")
        print(f"5) Trace all paths: {'Yes' if state.trace_all_paths else 'No'}")
        print("0) Back (saves automatically)")
        choice = input("\nSelect (0-5): ").strip()

        if choice == "1":
            state = _change_mode(project_root, state)
        elif choice == "2":
            state = _change_profile(project_root, state)
        elif choice == "3":
            state = _change_direction(project_root, state)
        elif choice == "4":
            state = _change_depth(project_root, state)
        elif choice == "5":
            state = _toggle_all_paths(project_root, state)
        elif choice == "0":
            return state


def _change_mode(project_root: Path, state: AppState) -> AppState:
    print("\nProject mode:")
    print("1) JS/TS")
    print("2) Python")
    print("3) Mixed")
    print("0) Cancel")
    choice = input("\nSelect (0-3): ").strip()
    mapping = {"1": "js_ts", "2": "python", "3": "mixed"}
    if choice in mapping:
        new_mode = mapping[choice]
        label = MODE_LABELS[new_mode]
        state = AppState(
            project_mode=new_mode,
            graph_profile=state.graph_profile,
            trace_direction=state.trace_direction,
            trace_depth=state.trace_depth,
            trace_all_paths=state.trace_all_paths,
        )
        save_state(project_root, state)
        print(f"  Mode set to {label}.")
    return state


def _change_profile(project_root: Path, state: AppState) -> AppState:
    print("\nGraph profile:")
    print("1) Pragmatic (lenient)")
    print("2) Strict (rigid)")
    print("0) Cancel")
    choice = input("\nSelect (0-2): ").strip()
    mapping = {"1": "pragmatic", "2": "strict"}
    if choice in mapping:
        state = AppState(
            project_mode=state.project_mode,
            graph_profile=mapping[choice],
            trace_direction=state.trace_direction,
            trace_depth=state.trace_depth,
            trace_all_paths=state.trace_all_paths,
        )
        save_state(project_root, state)
        print(f"  Profile set to {PROFILE_LABELS[mapping[choice]]}.")
    return state


def _change_direction(project_root: Path, state: AppState) -> AppState:
    print("\nTrace direction:")
    print("1) Inbound  (who depends on this?)")
    print("2) Outbound (what does this depend on?)")
    print("3) Both")
    print("0) Cancel")
    choice = input("\nSelect (0-3): ").strip()
    mapping = {"1": "inbound", "2": "outbound", "3": "both"}
    if choice in mapping:
        state = AppState(
            project_mode=state.project_mode,
            graph_profile=state.graph_profile,
            trace_direction=mapping[choice],
            trace_depth=state.trace_depth,
            trace_all_paths=state.trace_all_paths,
        )
        save_state(project_root, state)
        print(f"  Direction set to {DIRECTION_LABELS[mapping[choice]]}.")
    return state


def _change_depth(project_root: Path, state: AppState) -> AppState:
    raw = input(f"\nTrace depth (current: {state.trace_depth}): ").strip()
    if not raw:
        return state
    try:
        new_depth = int(raw)
        if new_depth < 1:
            print("  Depth must be >= 1.")
            return state
        state = AppState(
            project_mode=state.project_mode,
            graph_profile=state.graph_profile,
            trace_direction=state.trace_direction,
            trace_depth=new_depth,
            trace_all_paths=state.trace_all_paths,
        )
        save_state(project_root, state)
        print(f"  Depth set to {new_depth}.")
    except ValueError:
        print("  Invalid number.")
    return state


def _toggle_all_paths(project_root: Path, state: AppState) -> AppState:
    new_val = not state.trace_all_paths
    state = AppState(
        project_mode=state.project_mode,
        graph_profile=state.graph_profile,
        trace_direction=state.trace_direction,
        trace_depth=state.trace_depth,
        trace_all_paths=new_val,
    )
    save_state(project_root, state)
    print(f"  Trace all paths: {'Yes' if new_val else 'No'}")


def _confirm(summary: str) -> bool:
    print(summary)
    resp = input("Proceed? [y/N]: ").strip().lower()
    return resp == "y"
