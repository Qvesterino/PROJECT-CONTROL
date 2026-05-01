"""Menu-first interactive CLI."""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from project_control.ui.state import AppState, load_state, save_state, add_to_history, add_to_favorites, remove_from_favorites
from project_control.ui.onboarding import should_show_onboarding, show_onboarding, show_help_menu
from project_control.services.scan_service import run_scan
from project_control.services.graph_service import build_graph, show_report
from project_control.services.analyze_service import ghost_fast, ghost_structural
from project_control.services.explore_service import run_trace
from project_control.services.report_service import (
    view_ghost_report, view_graph_report, view_checklist, view_writers_report,
    display_report_list, list_all_reports
)
from project_control.core.error_handler import ErrorHandler, ErrorContext
from project_control.core.pre_flight import health_check
from project_control.core.validator import (
    validate_snapshot,
    validate_graph,
)
from project_control.core.backup import BackupManager, BackupContext
from project_control.utils.terminal import (
    print_success, print_warning, print_error, print_info,
    print_header, Status, Colors
)

logger = logging.getLogger(__name__)


def clear_screen() -> None:
    """Clear terminal screen in a cross-platform way."""
    try:
        if sys.platform == "win32":
            subprocess.run(["cls"], shell=True, check=False)
        else:
            subprocess.run(["clear"], shell=True, check=False)
    except Exception:
        # Silently fail - screen clearing is not critical
        pass


# ── Labels ──────────────────────────────────────────────────────────

MODE_LABELS = {"js_ts": "JS/TS", "python": "Python", "mixed": "Mixed"}
PROFILE_LABELS = {"pragmatic": "Pragmatic", "strict": "Strict"}
DIRECTION_LABELS = {"inbound": "Inbound", "outbound": "Outbound", "both": "Both"}


# ── Status helpers ──────────────────────────────────────────────────

def _snapshot_status(project_root: Path) -> str:
    """Get snapshot status with validation."""
    path = project_root / ".project-control" / "snapshot.json"
    if not path.exists():
        return "MISSING"
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = validate_snapshot(data, path)
        
        if not result.is_valid:
            return "INVALID"
        
        count = data.get("file_count", "?")
        status = f"OK ({count} files)"
        
        if result.has_warnings():
            status += " [!]"
        
        return status
    except json.JSONDecodeError:
        return "CORRUPTED"
    except Exception as e:
        logger.error(f"Error checking snapshot status: {e}")
        return "ERROR"


def _graph_status(project_root: Path) -> str:
    """Get graph status with validation."""
    path = project_root / ".project-control" / "out" / "graph.snapshot.json"
    if not path.exists():
        return "MISSING"
    
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        result = validate_graph(data, path)
        
        if not result.is_valid:
            return "INVALID"
        
        status = "OK"
        
        if result.has_warnings():
            status += " [!]"
        
        return status
    except json.JSONDecodeError:
        return "CORRUPTED"
    except Exception as e:
        logger.error(f"Error checking graph status: {e}")
        return "ERROR"


# ── Main loop ───────────────────────────────────────────────────────

def run_menu(project_root: Path) -> None:
    """Main menu loop with error handling."""
    # Show onboarding for new users
    if should_show_onboarding(project_root):
        show_onboarding(project_root)
    
    # Show wizard for first-time users
    if should_run_wizard(project_root):
        wizard_config = run_wizard(project_root)
        if wizard_config:
            print_info("Wizard completed! Your settings have been saved.")
    
    state = load_state(project_root)

    while True:
        clear_screen()
        _header(project_root, state)
        
        # Quick Actions section (moved to top for better UX)
        print("\n[Quick Actions]")
        print("  1) Full Analysis      — Scan → Find Issues → Dependencies")
        print("  2) Quick Health Check — Validate everything")
        print("  3) Quick Reports      — View all findings")
        
        # Main Tools section
        print("\n[Main Tools]")
        print("  4) Scan Project       — Index all files")
        print("  5) Find Issues        — Dead code, orphans, duplicates")
        print("  6) Dependencies       — Trace imports & modules")
        
        # Advanced section
        print("\n[Advanced]")
        print("  S) Settings           — Configuration")
        print("  H) Help & Docs        — Getting started")
        print("  0) Exit")

        choice = input("\nSelect (1-6, S, H, 0, or ? for help): ").strip().lower()

        try:
            if choice == "1":
                _quick_full_analysis(project_root, state)
            elif choice == "2":
                _quick_health_check(project_root)
            elif choice == "3":
                _reports_menu(project_root)
            elif choice == "4":
                _snapshot_menu(project_root, state)
            elif choice == "5":
                _analyze_menu(project_root, state)
            elif choice == "6":
                state = _explore_menu(project_root, state)
            elif choice == "s":
                state = _settings_menu(project_root, state)
            elif choice == "h":
                show_help_menu(project_root)
            elif choice == "?":
                _main_menu_help()
            elif choice == "0":
                save_state(project_root, state)
                print("Goodbye.")
                return
            else:
                input("Invalid selection. Press Enter...")
        except SystemExit:
            # Re-raise to exit cleanly
            raise
        except Exception as e:
            ErrorHandler.handle(e, "Menu operation")
            input("\nPress Enter to continue...")


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

    # Smart notifications
    notifications = _get_notifications(project_root, state)
    if notifications:
        print("\nNotifications:")
        for note in notifications:
            print(f"  [!] {note}")
        print()

    print()


def _get_notifications(project_root: Path, state: AppState) -> list[str]:
    """Get smart notifications based on project state."""
    notifications = []

    # Check if snapshot is missing or old
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    if not snapshot_path.exists():
        notifications.append("No snapshot found. Run 'Snapshot' to scan project.")
    else:
        # Check snapshot age
        import time
        mtime = snapshot_path.stat().st_mtime
        age_hours = (time.time() - mtime) / 3600
        if age_hours > 24:
            notifications.append(f"Snapshot is {int(age_hours)}h old. Rescan recommended.")

    # Check graph status
    graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"
    if not graph_path.exists():
        notifications.append("No graph built. Run 'Graph → Build' to analyze dependencies.")

    # Check if ripgrep is available
    import shutil
    if not shutil.which("rg"):
        notifications.append("Ripgrep not found. Some features limited.")

    # Check for recent history items
    if state.history:
        last_action = state.history[0] if state.history else None
        if last_action:
            notifications.append(f"Last action: {last_action}")

    return notifications


# ── Health Menu ───────────────────────────────────────────────────────

def _health_menu(project_root: Path) -> None:
    """Display project health check."""
    print("\n" + "="*60)
    print("  PROJECT HEALTH CHECK")
    print("="*60)
    
    with ErrorContext("Running health check"):
        report = health_check(project_root)
        
        # Overall status
        if report.is_healthy():
            status_symbol = Status.OK
        elif report.has_warnings():
            status_symbol = Status.WARN
        else:
            status_symbol = Status.FAIL
        status_color = report.overall_status.upper()
        print(f"\nOverall Status: {status_symbol} {status_color}")
        print()
        
        # Show checks
        print("Checks:")
        for check in report.checks:
            symbol = Status.OK if check.is_healthy else Status.FAIL
            print(f"  {symbol} {check.name}: {check.message}")
            if check.details:
                print(f"    Details: {check.details}")
        
        # Show errors and warnings
        if report.errors:
            print("\nErrors:")
            for error in report.errors:
                print(f"  {Status.FAIL} {error}")
        
        if report.warnings:
            print("\nWarnings:")
            for warning in report.warnings:
                print(f"  {Status.WARN} {warning}")
        
        # Show suggestions
        if report.suggestions:
            print("\nSuggestions:")
            for suggestion in report.suggestions:
                print(f"  {suggestion}")
        
        print("\n" + "="*60)
    
    input("\nPress Enter to return...")


# ── Sub-menus ───────────────────────────────────────────────────────

def _snapshot_menu(project_root: Path, state: AppState) -> None:
    """Snapshot menu with error handling."""
    print()
    if _confirm("Scan project files?"):
        with ErrorContext("Scanning project"):
            run_scan(project_root)
            print_success("Snapshot created successfully!")
    input("\nPress Enter to return...")


def _graph_menu(project_root: Path, state: AppState) -> None:
    """Graph menu with error handling."""
    print("\nGraph:")
    print("1) Build / Rebuild graph")
    print("2) Show graph report")
    print("0) Back")
    choice = input("\nSelect (0-2): ").strip()
    
    if choice == "1":
        if _confirm("Build graph with current config?"):
            with ErrorContext("Building graph"):
                with BackupContext(project_root, "before_graph_build", auto_cleanup=True):
                    build_graph(project_root, state)
                print_success("Graph built successfully!")
    elif choice == "2":
        with ErrorContext("Showing graph report"):
            show_report(project_root, state)
    
    input("\nPress Enter to return...")


def _analyze_menu(project_root: Path, state: AppState) -> None:
    """Analyze menu with error handling."""
    print("\nAnalyze:")
    print("1) Ghost detectors (shallow)")
    print("2) Structural metrics (from graph)")
    print("0) Back")
    choice = input("\nSelect (0-2): ").strip()
    
    if choice == "1":
        with ErrorContext("Running ghost analysis"):
            ghost_fast(project_root)
    elif choice == "2":
        with ErrorContext("Running structural analysis"):
            ghost_structural(project_root, state)
    
    input("\nPress Enter to return...")


def _explore_menu(project_root: Path, state: AppState) -> AppState:
    """Explore menu with error handling and favorites."""
    print("\nTrace:")
    dir_label = DIRECTION_LABELS.get(state.trace_direction, state.trace_direction)
    print(f"  Current: direction={dir_label}, depth={state.trace_depth}, all={state.trace_all_paths}")

    # Show favorites if available
    if state.favorites:
        print(f"\nFavorites ({len(state.favorites)}):")
        for i, fav in enumerate(state.favorites, 1):
            print(f"  [{i}] {fav}")
        print(f"  [f] Add current target to favorites")

    print()
    target = input("Target (path, symbol, [1-{0}] for favorite, 0=back): ".format(len(state.favorites))).strip()

    if not target or target == "0":
        return state

    # Check if selecting a favorite
    if state.favorites and target.isdigit():
        fav_index = int(target) - 1
        if 0 <= fav_index < len(state.favorites):
            target = state.favorites[fav_index]
            print(f"Using favorite: {target}\n")

    # Check if adding to favorites
    if target.lower() == "f":
        new_target = input("Enter target to save as favorite: ").strip()
        if new_target:
            state = add_to_favorites(state, new_target)
            save_state(project_root, state)
            print_success(f"Added to favorites: {new_target}")
        input("\nPress Enter to return...")
        return state

    with ErrorContext("Tracing dependencies"):
        run_trace(project_root, target, state)
        state = add_to_history(state, f"Trace: {target}")
        save_state(project_root, state)

    input("\nPress Enter to return...")
    return state


# ── Settings ────────────────────────────────────────────────────────

def _settings_menu(project_root: Path, state: AppState) -> AppState:
    while True:
        mode_label = MODE_LABELS.get(state.project_mode, state.project_mode)
        profile_label = PROFILE_LABELS.get(state.graph_profile, state.graph_profile)

        print("\n[Configuration]")
        print("="*60)
        print("\nBasic:")
        print(f"  1) Project Type:  [{mode_label}]")
        print(f"  2) Strictness:    [{profile_label}]")
        print(f"  3) Output Format: [Tree files ⭐ recommended]")
        print("\nAdvanced:")
        print(f"  4) Trace Options  — direction, depth, all paths")
        print("\n[?] Help — What do these mean?")
        print("[0] Back to main menu (saves automatically)")
  +++++++ REPLACE
        
        choice = input("\nSelect (1-4, ?, 0): ").strip()

        if choice == "1":
            state = _change_mode_simple(project_root, state)
        elif choice == "2":
            state = _change_profile_simple(project_root, state)
        elif choice == "3":
            _output_format_info(project_root)
        elif choice == "4":
            state = _trace_options_menu(project_root, state)
        elif choice == "?":
            _settings_help()
        elif choice == "0":
            return state
        else:
            input("Invalid selection. Press Enter...")


def _change_mode_simple(project_root: Path, state: AppState) -> AppState:
    """Simplified mode selection for new settings menu."""
    print("\n[Project Type]")
    print("="*60)
    print("What kind of project is this?")
    print()
    print("1) JavaScript/TypeScript  — JS, TS, JSX, TSX files")
    print("2) Python                — .py files")
    print("3) Mixed                 — Both JS/TS and Python")
    print()
    print("Most projects are auto-detected. Choose this only if")
    print("auto-detection is wrong.")
    print()
    
    choice = input("Select (1-3, or 0 to cancel): ").strip()
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
        print_success(f"Project type set to {label}")
    elif choice == "0":
        print_info("Cancelled")
    else:
        print_warning("Invalid selection")
    
    input("\nPress Enter...")
    return state


def _change_profile_simple(project_root: Path, state: AppState) -> AppState:
    """Simplified profile selection for new settings menu."""
    print("\n[Strictness Level]")
    print("="*60)
    print("How strict should the analysis be?")
    print()
    print("1) Pragmatic (Recommended)")
    print("   - Balanced approach")
    print("   - Some false positives allowed")
    print("   - Good for everyday use")
    print()
    print("2) Strict")
    print("   - More rigorous analysis")
    print("   - Fewer false positives")
    print("   - More noise, but more accurate")
    print()
    
    choice = input("Select (1-2, or 0 to cancel): ").strip()
    mapping = {"1": "pragmatic", "2": "strict"}
    
    if choice in mapping:
        new_profile = mapping[choice]
        label = PROFILE_LABELS[new_profile]
        state = AppState(
            project_mode=state.project_mode,
            graph_profile=new_profile,
            trace_direction=state.trace_direction,
            trace_depth=state.trace_depth,
            trace_all_paths=state.trace_all_paths,
        )
        save_state(project_root, state)
        print_success(f"Strictness set to {label}")
    elif choice == "0":
        print_info("Cancelled")
    else:
        print_warning("Invalid selection")
    
    input("\nPress Enter...")
    return state


def _output_format_info(project_root: Path) -> None:
    """Show output format information."""
    print("\n[Output Format]")
    print("="*60)
    print("Recommended: ASCII Tree Files ⭐")
    print()
    print("What you get:")
    print("  • ASCII Tree Files ⭐ — Visual structure, easy to read (recommended)")
    print("                         Perfect for human review and understanding")
    print()
    print("  • Markdown Reports     — Detailed analysis with explanations")
    print("  • JSON Files          — For automation and tools")
    print()
    print("Location: .project-control/exports/")
    print()
    print_info("Tree files are human-readable and show file relationships clearly.")
    print("They're the best choice for most users!")
    
    input("\nPress Enter...")
  +++++++ REPLACE


def _trace_options_menu(project_root: Path, state: AppState) -> AppState:
    """Advanced trace options menu."""
    while True:
        dir_label = DIRECTION_LABELS.get(state.trace_direction, state.trace_direction)
        
        print("\n[Trace Options (Advanced)]")
        print("="*60)
        print(f"1) Direction:  [{dir_label}]")
        print(f"   Inbound  = Who depends on this?")
        print(f"   Outbound = What does this depend on?")
        print(f"   Both     = Both directions")
        print()
        print(f"2) Depth:     [{state.trace_depth}]")
        print("   How many levels to trace")
        print()
        print(f"3) All Paths: [{'Yes' if state.trace_all_paths else 'No'}]")
        print("   Show all paths or just one per target")
        print()
        print("[0] Back to settings")
        
        choice = input("\nSelect (1-3, or 0): ").strip()
        
        if choice == "1":
            state = _change_direction(project_root, state)
            input("\nPress Enter...")
        elif choice == "2":
            state = _change_depth(project_root, state)
            input("\nPress Enter...")
        elif choice == "3":
            state = _toggle_all_paths(project_root, state)
            input("\nPress Enter...")
        elif choice == "0":
            return state
        else:
            input("Invalid selection. Press Enter...")


def _settings_help() -> None:
    """Show help for settings menu."""
    print("\n[?] Configuration Help")
    print("="*60)
    print()
    print("[PROJECT TYPE]")
    print("   Determines which language features to analyze.")
    print("   Auto-detected by default. Change only if wrong.")
    print()
    print("[STRICTNESS]")
    print("   Controls how strict the analysis is.")
    print("   Pragmatic = Balanced, good for everyday use")
    print("   Strict     = More rigorous, more accurate")
    print()
    print("[OUTPUT FORMAT]")
    print("   What kind of reports to generate.")
    print("   Currently generates all formats automatically.")
    print()
    print("[TRACE OPTIONS]")
    print("   Advanced settings for dependency tracing.")
    print("   Direction, depth, and path options.")
    print()
    print("All settings are saved automatically.")
    
    input("\nPress Enter...")


def _main_menu_help() -> None:
    """Show help for main menu."""
    print("\n[?] Main Menu Help")
    print("="*60)
    print()
    print("[QUICK ACTIONS]")
    print("   Fast workflows for common tasks.")
    print("   Full Analysis = Scan → Find Issues → Dependencies")
    print("   Health Check = Validate everything")
    print("   Quick Reports = View all findings")
    print()
    print("[MAIN TOOLS]")
    print("   Individual tools for specific tasks.")
    print("   Scan Project = Index your files")
    print("   Find Issues  = Dead code, orphans, duplicates")
    print("   Dependencies = Trace imports & modules")
    print()
    print("[ADVANCED]")
    print("   Settings and help for power users.")
    print("   Settings  = Configuration options")
    print("   Help      = Documentation and tutorials")
    print()
    print("[TIP] Use 'Full Analysis' for a complete overview!")
    
    input("\nPress Enter...")


def _reports_menu(project_root: Path) -> None:
    """View all available reports."""
    print("\n[Quick Reports]")
    print("="*60)
    
    # Check what reports exist
    control_dir = project_root / ".project-control"
    exports_dir = control_dir / "exports"
    
    reports = []
    
    if exports_dir.exists():
        # Check for various reports
        ghost_report = exports_dir / "ghost_candidates.md"
        if ghost_report.exists():
            reports.append(("Ghost Analysis", ghost_report))
        
        graph_report = exports_dir / "graph.report.md"
        if graph_report.exists():
            reports.append(("Graph Report", graph_report))
        
        checklist = exports_dir / "checklist.md"
        if checklist.exists():
            reports.append(("File Checklist", checklist))
        
        # Check for tree files
        tree_files = list(exports_dir.glob("*_tree.txt"))
        if tree_files:
            reports.append((f"ASCII Trees ({len(tree_files)} files)", exports_dir))
    
    if not reports:
        print("\nNo reports found yet.")
        print("Run 'Full Analysis' or 'Find Issues' to generate reports.")
    else:
        print(f"\nFound {len(reports)} report(s):\n")
        for i, (name, path) in enumerate(reports, 1):
            if path.is_file():
                size = path.stat().st_size / 1024
                print(f"{i}) {name}")
                print(f"   {path.name} ({size:.1f} KB)")
            else:
                print(f"{i}) {name}")
                print(f"   Multiple files in {path.name}")
    
    print("\nAll reports are in: .project-control/exports/")
    
    input("\nPress Enter to return...")


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
    return state


def _tools_menu(project_root: Path) -> None:
    """Tools menu for backups, cache, and diagnostics."""
    while True:
        print("\nTools:")
        print("1) List Backups         — show all available backups")
        print("2) Create Manual Backup — create a named backup")
        print("3) Restore Backup       — restore from a backup")
        print("4) Delete Backup        — delete a specific backup")
        print("5) Cleanup Old Backups  — remove old backups (keep latest 5)")
        print("6) Clear Graph Cache    — remove .project-control/out/")
        print("7) Show Diagnostics     — display system information")
        print("0) Back")

        choice = input("\nSelect (0-7): ").strip()

        if choice == "0":
            return
        elif choice == "1":
            _list_backups_menu(project_root)
        elif choice == "2":
            _create_backup_menu(project_root)
        elif choice == "3":
            _restore_backup_menu(project_root)
        elif choice == "4":
            _delete_backup_menu(project_root)
        elif choice == "5":
            _cleanup_backups_menu(project_root)
        elif choice == "6":
            _clear_cache_menu(project_root)
        elif choice == "7":
            _show_diagnostics_menu(project_root)
        else:
            input("Invalid selection. Press Enter...")


def _list_backups_menu(project_root: Path) -> None:
    """List all available backups."""
    print("\n" + "="*60)
    print("  AVAILABLE BACKUPS")
    print("="*60)

    try:
        manager = BackupManager(project_root)
        backups = manager.list_backups()

        if not backups:
            print("\nNo backups found.")
        else:
            print(f"\nFound {len(backups)} backup(s):\n")
            for i, backup in enumerate(backups, 1):
                size_mb = backup.size_bytes / (1024 * 1024)
                time_str = backup.timestamp.replace("T", " ").split(".")[0]
                print(f"{i}) {backup.name}")
                print(f"   Created: {time_str}")
                print(f"   Size:    {size_mb:.2f} MB")
                if backup.description:
                    print(f"   Note:    {backup.description}")
                print()

    except Exception as e:
        ErrorHandler.handle(e, "Listing backups")

    input("\nPress Enter to return...")


def _create_backup_menu(project_root: Path) -> None:
    """Create a manual backup with custom name."""
    print("\n" + "="*60)
    print("  CREATE BACKUP")
    print("="*60)

    name = input("\nBackup name (leave empty for timestamp): ").strip()
    description = input("Description (optional): ").strip() or None

    try:
        manager = BackupManager(project_root)
        backup = manager.create_backup(name=name or None, description=description)
        print_success(f"Backup created: {backup.name}")
        print(f"  Path: {backup.path}")
        print(f"  Size: {backup.size_bytes / (1024 * 1024):.2f} MB")
    except Exception as e:
        ErrorHandler.handle(e, "Creating backup")

    input("\nPress Enter to return...")


def _restore_backup_menu(project_root: Path) -> None:
    """Restore from a backup."""
    print("\n" + "="*60)
    print("  RESTORE BACKUP")
    print("="*60)

    try:
        manager = BackupManager(project_root)
        backups = manager.list_backups()

        if not backups:
            print("\nNo backups available to restore.")
            input("\nPress Enter to return...")
            return

        print(f"\nAvailable backups ({len(backups)}):\n")
        for i, backup in enumerate(backups, 1):
            time_str = backup.timestamp.replace("T", " ").split(".")[0]
            print(f"{i}) {backup.name} ({time_str})")

        choice = input("\nSelect backup to restore (0=cancel): ").strip()
        if not choice or choice == "0":
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                manager.restore_backup(backups[index], confirm=True)
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid selection.")

    except Exception as e:
        ErrorHandler.handle(e, "Restoring backup")

    input("\nPress Enter to return...")


def _delete_backup_menu(project_root: Path) -> None:
    """Delete a specific backup."""
    print("\n" + "="*60)
    print("  DELETE BACKUP")
    print("="*60)

    try:
        manager = BackupManager(project_root)
        backups = manager.list_backups()

        if not backups:
            print("\nNo backups available to delete.")
            input("\nPress Enter to return...")
            return

        print(f"\nAvailable backups ({len(backups)}):\n")
        for i, backup in enumerate(backups, 1):
            time_str = backup.timestamp.replace("T", " ").split(".")[0]
            print(f"{i}) {backup.name} ({time_str})")

        choice = input("\nSelect backup to delete (0=cancel): ").strip()
        if not choice or choice == "0":
            return

        try:
            index = int(choice) - 1
            if 0 <= index < len(backups):
                backup = backups[index]
                confirm = input(f"\n{Status.WARN} Delete backup '{backup.name}'? (y/N): {Colors.RESET}").strip().lower()
                if confirm == "y":
                    manager.delete_backup(backup)
                    print_success(f"Backup deleted: {backup.name}")
                else:
                    print("Deletion cancelled.")
            else:
                print("Invalid selection.")
        except ValueError:
            print("Invalid selection.")

    except Exception as e:
        ErrorHandler.handle(e, "Deleting backup")

    input("\nPress Enter to return...")


def _cleanup_backups_menu(project_root: Path) -> None:
    """Cleanup old backups, keeping only the most recent ones."""
    print("\n" + "="*60)
    print("  CLEANUP OLD BACKUPS")
    print("="*60)

    keep = input("\nHow many recent backups to keep? (default: 5): ").strip()
    try:
        keep = int(keep) if keep else 5
        if keep < 1:
            print("Must keep at least 1 backup.")
            input("\nPress Enter to return...")
            return
    except ValueError:
        print("Invalid number.")
        input("\nPress Enter to return...")
        return

    try:
        manager = BackupManager(project_root)
        deleted = manager.cleanup_old_backups(keep=keep)
        print_success(f"Cleanup complete: {deleted} old backup(s) deleted.")
    except Exception as e:
        ErrorHandler.handle(e, "Cleaning up backups")

    input("\nPress Enter to return...")


def _clear_cache_menu(project_root: Path) -> None:
    """Clear the graph cache directory."""
    print("\n" + "="*60)
    print("  CLEAR GRAPH CACHE")
    print("="*60)

    cache_dir = project_root / ".project-control" / "out"
    if not cache_dir.exists():
        print("\nNo cache directory found.")
        input("\nPress Enter to return...")
        return

    print(f"\nCache directory: {cache_dir}")

    # Show cache size
    import os
    total_size = 0
    for root, dirs, files in os.walk(cache_dir):
        for file in files:
            file_path = os.path.join(root, file)
            total_size += os.path.getsize(file_path)

    size_mb = total_size / (1024 * 1024)
    print(f"Current size: {size_mb:.2f} MB")

    confirm = input(f"\n{Status.WARN} Delete all cached data? (y/N): {Colors.RESET}").strip().lower()
    if confirm != "y":
        print("Operation cancelled.")
        input("\nPress Enter to return...")
        return

    # Create backup before clearing
    try:
        with BackupContext(project_root, "before_cache_clear", auto_cleanup=False):
            import shutil
            shutil.rmtree(cache_dir)
            cache_dir.mkdir(parents=True, exist_ok=True)
            print_success("Cache cleared successfully.")
    except Exception as e:
        ErrorHandler.handle(e, "Clearing cache")

    input("\nPress Enter to return...")


def _show_diagnostics_menu(project_root: Path) -> None:
    """Show system and project diagnostics."""
    print("\n" + "="*60)
    print("  DIAGNOSTICS")
    print("="*60)

    import sys
    import platform
    from pathlib import Path

    print(f"\nSystem:")
    print(f"  Platform:  {platform.system()} {platform.release()}")
    print(f"  Python:    {sys.version.split()[0]}")
    print(f"  Working:   {Path.cwd()}")

    print(f"\nProject:")
    print(f"  Root:      {project_root}")
    print(f"  Config:    {project_root / '.project-control'}")

    control_dir = project_root / ".project-control"
    if control_dir.exists():
        print(f"  Status:    {Status.OK} Exists")

        # Check files
        snapshot = control_dir / "snapshot.json"
        graph_out = control_dir / "out" / "graph.snapshot.json"

        print(f"\nFiles:")
        print(f"  Snapshot:  {Status.OK if snapshot.exists() else Status.FAIL} {snapshot.name}")
        print(f"  Graph:     {Status.OK if graph_out.exists() else Status.FAIL} {graph_out.name}")

        # Check backups
        backup_dir = control_dir / "backups"
        if backup_dir.exists():
            backup_count = len([d for d in backup_dir.iterdir() if d.is_dir()])
            print(f"  Backups:   {backup_count} found")
        else:
            print(f"  Backups:   0 found")
    else:
        print(f"  Status:    {Status.FAIL} Not initialized")

    # Check external dependencies
    print(f"\nDependencies:")
    import shutil

    ripgrep = shutil.which("rg")
    print(f"  Ripgrep:   {Status.OK if ripgrep else Status.FAIL} {ripgrep if ripgrep else 'Not found'}")

    # Check ollama (optional)
    ollama = shutil.which("ollama")
    print(f"  Ollama:    {Status.OK if ollama else Status.WARN}  {ollama if ollama else 'Not found (optional)'}")

    print("\n" + "="*60)

    input("\nPress Enter to return...")


def _quick_actions_menu(project_root: Path, state: AppState) -> None:
    """Quick Actions menu for common operations."""
    while True:
        print("\n" + "="*60)
        print("  QUICK ACTIONS")
        print("="*60)
        print("\n1) Full Analysis      — scan → ghost → graph → report")
        print("2) Health Check       — validate everything")
        print("3) Find Orphans       — quick orphan scan")
        print("4) Find Cycles        — quick cycle detection")
        print("5) Dependency Audit   — analyze dependency graph")
        print("6) Favorites          — manage favorite trace targets")
        print("7) History            — view recent actions")
        print("0) Back")

        choice = input("\nSelect (0-7): ").strip()

        if choice == "0":
            return
        elif choice == "1":
            _quick_full_analysis(project_root, state)
        elif choice == "2":
            _quick_health_check(project_root)
        elif choice == "3":
            _quick_find_orphans(project_root)
        elif choice == "4":
            _quick_find_cycles(project_root, state)
        elif choice == "5":
            _quick_dependency_audit(project_root, state)
        elif choice == "6":
            state = _quick_favorites_menu(project_root, state)
        elif choice == "7":
            _quick_history_menu(project_root, state)
        else:
            input("Invalid selection. Press Enter...")


def _quick_full_analysis(project_root: Path, state: AppState) -> None:
    """Quick full analysis: scan → ghost → graph → report."""
    print("\n" + "="*60)
    print("  FULL ANALYSIS")
    print("="*60)
    print("\nThis will run:")
    print("  1. Scan project files")
    print("  2. Run ghost analysis")
    print("  3. Build dependency graph")
    print("  4. Show report")

    if not _confirm("\nProceed with full analysis?"):
        return

    print("\nStep 1/4: Scanning project files...")
    try:
        with ErrorContext("Scanning project"):
            run_scan(project_root)
            print_success("Scan complete")
    except Exception as e:
        ErrorHandler.handle(e, "Scanning project")
        input("\nPress Enter to return...")
        return

    print("\nStep 2/4: Running ghost analysis...")
    try:
        with ErrorContext("Running ghost analysis"):
            ghost_fast(project_root)
            print_success("Ghost analysis complete")
    except Exception as e:
        ErrorHandler.handle(e, "Running ghost analysis")
        input("\nPress Enter to return...")
        return

    print("\nStep 3/4: Building dependency graph...")
    try:
        with ErrorContext("Building graph"):
            with BackupContext(project_root, "full_analysis_graph_build"):
                build_graph(project_root, state)
            print_success("Graph built")
    except Exception as e:
        ErrorHandler.handle(e, "Building graph")
        input("\nPress Enter to return...")
        return

    print("\nStep 4/4: Showing report...")
    try:
        with ErrorContext("Showing report"):
            show_report(project_root, state)
    except Exception as e:
        ErrorHandler.handle(e, "Showing report")

    print("\n" + "="*60)
    print_success("Full analysis complete!")
    print("="*60)

    input("\nPress Enter to return...")


def _quick_health_check(project_root: Path) -> None:
    """Quick health check."""
    _health_menu(project_root)


def _quick_find_orphans(project_root: Path) -> None:
    """Quick orphan scan."""
    print("\n" + "="*60)
    print("  FIND ORPHANS")
    print("="*60)

    try:
        with ErrorContext("Finding orphans"):
            ghost_fast(project_root)
    except Exception as e:
        ErrorHandler.handle(e, "Finding orphans")

    input("\nPress Enter to return...")


def _quick_find_cycles(project_root: Path, state: AppState) -> None:
    """Quick cycle detection."""
    print("\n" + "="*60)
    print("  FIND CYCLES")
    print("="*60)

    try:
        with ErrorContext("Finding cycles"):
            ghost_structural(project_root, state)
    except Exception as e:
        ErrorHandler.handle(e, "Finding cycles")

    input("\nPress Enter to return...")


def _quick_dependency_audit(project_root: Path, state: AppState) -> None:
    """Dependency audit - analyze dependency graph."""
    print("\n" + "="*60)
    print("  DEPENDENCY AUDIT")
    print("="*60)

    graph_path = project_root / ".project-control" / "out" / "graph.snapshot.json"
    if not graph_path.exists():
        print_warning("Graph not found. Building...")
        try:
            with ErrorContext("Building graph"):
                with BackupContext(project_root, "dependency_audit"):
                    build_graph(project_root, state)
        except Exception as e:
            ErrorHandler.handle(e, "Building graph")
            input("\nPress Enter to return...")
            return

    try:
        with ErrorContext("Running dependency audit"):
            ghost_structural(project_root, state)
            show_report(project_root, state)
    except Exception as e:
        ErrorHandler.handle(e, "Running dependency audit")

    print("\n" + "="*60)
    print_success("Dependency audit complete!")
    print("="*60)

    input("\nPress Enter to return...")


def _quick_favorites_menu(project_root: Path, state: AppState) -> AppState:
    """Manage favorite trace targets."""
    while True:
        print("\n" + "="*60)
        print("  FAVORITES")
        print("="*60)

        if not state.favorites:
            print("\nNo favorites saved yet.")
        else:
            print(f"\nFavorites ({len(state.favorites)}):")
            for i, fav in enumerate(state.favorites, 1):
                print(f"  {i}) {fav}")

        print("\n1) Add current target to favorites")
        print("2) Trace a favorite")
        print("3) Remove a favorite")
        print("0) Back")

        choice = input("\nSelect (0-3): ").strip()

        if choice == "0":
            return state
        elif choice == "1":
            target = input("\nEnter target path/symbol: ").strip()
            if target:
                state = add_to_favorites(state, target)
                save_state(project_root, state)
                print_success(f"Added to favorites: {target}")
                input("\nPress Enter...")
            else:
                print_warning("Target cannot be empty.")
                input("\nPress Enter...")
        elif choice == "2":
            if not state.favorites:
                print_warning("No favorites available.")
                input("\nPress Enter...")
                continue

            print(f"\nFavorites ({len(state.favorites)}):")
            for i, fav in enumerate(state.favorites, 1):
                print(f"  {i}) {fav}")

            fav_choice = input("\nSelect favorite to trace (0=cancel): ").strip()
            if not fav_choice or fav_choice == "0":
                continue

            try:
                index = int(fav_choice) - 1
                if 0 <= index < len(state.favorites):
                    target = state.favorites[index]
                    print(f"\nTracing: {target}")
                    try:
                        with ErrorContext("Tracing favorite"):
                            run_trace(project_root, target, state)
                            state = add_to_history(state, f"Trace: {target}")
                            save_state(project_root, state)
                    except Exception as e:
                        ErrorHandler.handle(e, "Tracing favorite")
                    input("\nPress Enter...")
                else:
                    print_warning("Invalid selection.")
                    input("\nPress Enter...")
            except ValueError:
                print_warning("Invalid selection.")
                input("\nPress Enter...")
        elif choice == "3":
            if not state.favorites:
                print_warning("No favorites available.")
                input("\nPress Enter...")
                continue

            print(f"\nFavorites ({len(state.favorites)}):")
            for i, fav in enumerate(state.favorites, 1):
                print(f"  {i}) {fav}")

            del_choice = input("\nSelect favorite to remove (0=cancel): ").strip()
            if not del_choice or del_choice == "0":
                continue

            try:
                index = int(del_choice) - 1
                if 0 <= index < len(state.favorites):
                    target = state.favorites[index]
                    state = remove_from_favorites(state, target)
                    save_state(project_root, state)
                    print_success(f"Removed from favorites: {target}")
                    input("\nPress Enter...")
                else:
                    print_warning("Invalid selection.")
                    input("\nPress Enter...")
            except ValueError:
                print_warning("Invalid selection.")
                input("\nPress Enter...")
        else:
            input("\nInvalid selection. Press Enter...")


def _quick_history_menu(project_root: Path, state: AppState) -> None:
    """View recent actions history."""
    print("\n" + "="*60)
    print("  RECENT ACTIONS")
    print("="*60)

    if not state.history:
        print("\nNo recent actions recorded.")
    else:
        print(f"\nRecent actions ({len(state.history)}):")
        for i, action in enumerate(state.history, 1):
            print(f"  {i}) {action}")

    print("\n" + "="*60)

    input("\nPress Enter to return...")


def _confirm(summary: str) -> bool:
    print(summary)
    resp = input("Proceed? [y/N]: ").strip().lower()
    return resp == "y"


# ── Presets Menu ─────────────────────────────────────────────────────────

def _presets_menu(project_root: Path) -> None:
    """Project presets management menu."""
    from project_control.config.presets import PresetManager

    manager = PresetManager(project_root)

    while True:
        clear_screen()
        print("\n" + "="*60)
        print("  PROJECT PRESETS")
        print("="*60)

        # Show current preset
        current = manager.get_current_preset_name()
        if current:
            print(f"\nCurrent preset: {current}")
        else:
            print("\nCurrent configuration: Custom")

        print("\nActions:")
        print("1) List Presets      — Show all available presets")
        print("2) Apply Preset       — Apply a preset to project")
        print("3) Save Custom        — Save current config as custom preset")
        print("4) Delete Custom      — Delete a custom preset")
        print("B) Back              — Return to main menu")

        choice = input("\nSelect (1-4, B): ").strip().lower()

        if choice == "1":
            _preset_list_submenu(manager)
        elif choice == "2":
            _preset_apply_submenu(manager)
        elif choice == "3":
            _preset_save_submenu(manager)
        elif choice == "4":
            _preset_delete_submenu(manager)
        elif choice == "b":
            return
        else:
            input("Invalid selection. Press Enter...")


def _preset_list_submenu(manager: PresetManager) -> None:
    """List all presets."""
    clear_screen()
    print("\n" + "="*60)
    print("  AVAILABLE PRESETS")
    print("="*60)

    presets = manager.list_presets()
    for preset in presets:
        category_mark = " [builtin]" if preset["category"] == "builtin" else " [custom]"
        print(f"\n  {preset['name']}{category_mark}")
        print(f"    {preset['description']}")

    input("\nPress Enter to return...")


def _preset_apply_submenu(manager: PresetManager) -> None:
    """Apply a preset."""
    clear_screen()
    print("\n" + "="*60)
    print("  APPLY PRESET")
    print("="*60)

    presets = manager.list_presets()
    print("\nAvailable presets:")
    for i, preset in enumerate(presets, 1):
        print(f"  {i}) {preset['name']} - {preset['description']}")

    choice = input("\nSelect preset (number): ").strip()
    try:
        index = int(choice) - 1
        if 0 <= index < len(presets):
            preset_name = presets[index]["name"]
            summary = f"This will apply the '{preset_name}' preset to your project."
            if _confirm(summary):
                if manager.apply_preset(preset_name, backup=True):
                    print_success(f"Preset '{preset_name}' applied successfully!")
                    print_info("Backup created in .project-control/backups/")
                else:
                    print_error(f"Failed to apply preset '{preset_name}'")
        else:
            print_error("Invalid selection")
    except ValueError:
        print_error("Please enter a valid number")

    input("\nPress Enter to return...")


def _preset_save_submenu(manager: PresetManager) -> None:
    """Save current config as custom preset."""
    clear_screen()
    print("\n" + "="*60)
    print("  SAVE CUSTOM PRESET")
    print("="*60)

    name = input("\nPreset name: ").strip()
    if not name:
        print_error("Preset name is required")
        input("\nPress Enter to return...")
        return

    description = input("Description (optional): ").strip()

    if manager.save_custom_preset(name, description or f"Custom preset: {name}"):
        print_success(f"Preset '{name}' saved successfully!")
    else:
        print_error(f"Failed to save preset '{name}'")

    input("\nPress Enter to return...")


def _preset_delete_submenu(manager: PresetManager) -> None:
    """Delete a custom preset."""
    clear_screen()
    print("\n" + "="*60)
    print("  DELETE CUSTOM PRESET")
    print("="*60)

    presets = [p for p in manager.list_presets() if p["category"] == "custom"]

    if not presets:
        print_info("No custom presets found.")
        input("\nPress Enter to return...")
        return

    print("\nCustom presets:")
    for i, preset in enumerate(presets, 1):
        print(f"  {i}) {preset['name']} - {preset['description']}")

    choice = input("\nSelect preset to delete (number): ").strip()
    try:
        index = int(choice) - 1
        if 0 <= index < len(presets):
            preset_name = presets[index]["name"]
            summary = f"This will delete the custom preset '{preset_name}'."
            if _confirm(summary):
                if manager.delete_custom_preset(preset_name):
                    print_success(f"Preset '{preset_name}' deleted successfully!")
                else:
                    print_error(f"Failed to delete preset '{preset_name}'")
        else:
            print_error("Invalid selection")
    except ValueError:
        print_error("Please enter a valid number")

    input("\nPress Enter to return...")


# ── Export/Import Menu ───────────────────────────────────────────────────

def _export_import_menu(project_root: Path) -> None:
    """Export/Import settings menu."""
    from project_control.persistence.state_manager import StateManager

    manager = StateManager(project_root)

    while True:
        clear_screen()
        print("\n" + "="*60)
        print("  EXPORT / IMPORT STATE")
        print("="*60)

        print("\nActions:")
        print("1) Export State       — Export current settings to file")
        print("2) Import State       — Import settings from file")
        print("B) Back              — Return to main menu")

        choice = input("\nSelect (1-2, B): ").strip().lower()

        if choice == "1":
            _export_state_submenu(manager)
        elif choice == "2":
            _import_state_submenu(manager)
        elif choice == "b":
            return
        else:
            input("Invalid selection. Press Enter...")


def _export_state_submenu(manager: StateManager) -> None:
    """Export state to file."""
    clear_screen()
    print("\n" + "="*60)
    print("  EXPORT STATE")
    print("="*60)

    print("\nExport options:")
    print("1) Export with metadata (includes project-specific info)")
    print("2) Export without metadata (portable, git-friendly)")

    choice = input("\nSelect (1-2): ").strip()
    include_metadata = choice != "2"

    custom_path = input("\nCustom path (leave empty for default): ").strip()
    export_path = Path(custom_path) if custom_path else None

    try:
        result_path = manager.export_state(export_path, include_metadata=include_metadata)
        print_success(f"State exported to: {result_path}")
    except Exception as e:
        print_error(f"Export failed: {e}")

    input("\nPress Enter to return...")


def _import_state_submenu(manager: StateManager) -> None:
    """Import state from file."""
    clear_screen()
    print("\n" + "="*60)
    print("  IMPORT STATE")
    print("="*60)

    import_path_str = input("\nPath to import file: ").strip()
    if not import_path_str:
        print_error("Path is required")
        input("\nPress Enter to return...")
        return

    import_path = Path(import_path_str)
    if not import_path.exists():
        print_error(f"File not found: {import_path}")
        input("\nPress Enter to return...")
        return

    print("\nImport mode:")
    print("1) Replace  — Replace all settings")
    print("2) Merge    — Merge with existing settings")

    mode_choice = input("\nSelect (1-2): ").strip()
    merge = mode_choice == "2"

    summary = f"This will {'merge' if merge else 'replace'} settings from {import_path.name}."
    if _confirm(summary):
        try:
            manager.import_state(import_path, merge=merge)
            print_success(f"State {'merged' if merge else 'imported'} successfully!")
        except Exception as e:
            print_error(f"Import failed: {e}")

    input("\nPress Enter to return...")


# ── File Explorer Menu ───────────────────────────────────────────────────

def _file_explorer_menu(project_root: Path) -> None:
    """Interactive file explorer menu."""
    from project_control.ui.file_explorer import FileExplorer

    explorer = FileExplorer(project_root)

    while True:
        clear_screen()

        # Show current path
        rel_path = explorer.get_current_path().relative_to(project_root)
        print("\n" + "="*60)
        print(f"  FILE EXPLORER - {rel_path}")
        print("="*60)

        # Show directory listing
        output = explorer.render_file_list()
        _safe_print(output)

        print("\nActions:")
        print("[path]  — Change to directory (e.g., 'src', '..')")
        print("D [path] — Show file/directory details")
        print("S [term] — Search files")
        print("U       — Go up one level")
        print("R       — Refresh")
        print("B) Back — Return to main menu")

        choice = input("\nCommand: ").strip()

        if choice.lower() == "b":
            return
        elif choice.lower() == "u":
            explorer.go_up()
        elif choice.lower() == "r":
            continue  # Just refresh
        elif choice.lower().startswith("s "):
            # Search
            term = choice[2:].strip()
            if term:
                results = explorer.search_files(term)
                clear_screen()
                print(f"\nSearch results for '{term}':")
                print("="*60)
                if results:
                    for r in results:
                        print(f"  {r.path} ({r.size} bytes)")
                else:
                    print("  No results found.")
                input("\nPress Enter to continue...")
        elif choice.lower().startswith("d "):
            # Details
            path = choice[2:].strip()
            if path:
                clear_screen()
                details = explorer.render_file_details(path)
                _safe_print(details)
                input("\nPress Enter to continue...")
        elif choice:
            # Try to change directory
            if explorer.change_directory(choice):
                pass  # Will refresh on next loop
            else:
                print_error(f"Cannot navigate to: {choice}")
                input("\nPress Enter to continue...")


def _safe_print(text: str) -> None:
    """Print text safely, handling Unicode encoding issues."""
    import sys
    try:
        print(text)
    except UnicodeEncodeError:
        if sys.platform == "win32":
            safe_text = text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding)
            print(safe_text)
        else:
            try:
                print(text.encode("utf-8", errors="replace").decode("utf-8"))
            except Exception:
                print(text.encode("ascii", errors="replace").decode("ascii"))
