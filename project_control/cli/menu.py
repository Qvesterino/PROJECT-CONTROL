"""Menu-first interactive CLI."""

from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from project_control.ui.state import AppState, load_state, save_state, add_to_history, add_to_favorites, remove_from_favorites
from project_control.ui.onboarding import should_show_onboarding, show_onboarding, show_help_menu
from project_control.ui.wizard import should_run_wizard, run_wizard
from project_control.services.scan_service import run_interactive_scan
from project_control.services.graph_service import build_graph, show_report
from project_control.services.analyze_service import ghost_fast, ghost_structural
from project_control.services.explore_service import run_trace
from project_control.core.artifact_service import run_artifact_hygiene
from project_control.core.audit_retention_service import run_audit_retention
from project_control.services.report_service import (
    view_ghost_report, view_graph_report, view_checklist, view_writers_report,
    view_ui_verification_report, view_vfx_contract_report, view_patron_path_report,
    view_ecosystem_health_report, display_report_list, list_all_reports
)
from project_control.services.ui_verification_service import (
    get_default_ui_verification_config_path,
    list_ui_verification_profiles,
    run_ui_verification_profile,
)
from project_control.services.patron_path_service import run_patron_path_audit
from project_control.services.ecosystem_health_service import run_ecosystem_health
from project_control.services.vfx_contract_service import run_vfx_contract_audit
from project_control.core.error_handler import ErrorHandler, ErrorContext
from project_control.core.pre_flight import health_check
from project_control.core.validator import (
    validate_snapshot,
    validate_graph,
)
from project_control.core.backup import BackupManager, BackupContext
from project_control.utils.terminal import (
    print_success, print_warning, print_error, print_info,
    print_divider, print_menu_item, print_quick_action,
    print_notification,
    print_pc_splash_compact, print_status_bar, print_separator,
    print_prompt, print_exit_message, print_section_title,
    Status, Colors, Violet
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
    if should_show_onboarding(project_root):
        show_onboarding(project_root)
    
    if should_run_wizard(project_root):
        wizard_config = run_wizard(project_root)
        if wizard_config:
            print_info("Wizard completed! Your settings have been saved.")
    
    state = load_state(project_root)

    # Show splash on first render
    from project_control.utils.terminal import print_pc_splash
    clear_screen()
    print_pc_splash(width=54)
    import time
    time.sleep(0.3)

    while True:
        clear_screen()
        _header(project_root, state)
        
        # ── Quick Actions ──
        print()
        print_section_title("Quick Actions")
        print()
        print_quick_action("1", "Full Analysis", "Scan → Find Issues → Dependencies")
        print_quick_action("2", "Quick Health Check", "Validate everything")
        print_quick_action("3", "Quick Reports", "View all findings")
        
        # ── Main Tools ──
        print()
        print_section_title("Main Tools")
        print()
        print_menu_item("4", "Scan Project", "Index all files")
        print_menu_item("5", "Find Issues", "Dead code, orphans, duplicates")
        print_menu_item("6", "Dependencies", "Trace imports & modules")
        
        # ── Advanced ──
        print()
        print_section_title("Advanced")
        print()
        print_menu_item("S", "Settings", "Configuration")
        print_menu_item("H", "Help & Docs", "Getting started")
        print_menu_item("0", "Exit", "")
        print()
        print(f"  {Violet.TEXT_MUTED}Press ? for help{Colors.RESET}")
        print()

        choice = print_prompt()

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
                print_exit_message()
                return
            else:
                input("Invalid selection. Press Enter...")
        except SystemExit:
            raise
        except Exception as e:
            ErrorHandler.handle(e, "Menu operation")
            input("\nPress Enter to continue...")


def _header(project_root: Path, state: AppState) -> None:
    mode_label = MODE_LABELS.get(state.project_mode, state.project_mode)
    
    width = 54
    
    # ── Compact branded header bar ──
    print_pc_splash_compact(width)
    
    # ── Status bar with live project data ──
    snap_status = _snapshot_status(project_root)
    graph_status = _graph_status(project_root)
    snap_colored = _color_status(snap_status)
    graph_colored = _color_status(graph_status)
    
    entries = [
        ("Project", project_root.name, Violet.TEXT),
        ("Mode", mode_label, Violet.TEXT),
        ("Snapshot", snap_colored, ""),
        ("Graph", graph_colored, ""),
    ]
    print_status_bar(entries, width=width)
    
    # ── Smart notifications ──
    notifications = _get_notifications(project_root, state)
    if notifications:
        print()
        for note in notifications:
            print_notification(note, "info")

    print()


def _color_status(status: str) -> str:
    """Colorize a status string based on its content."""
    if "OK" in status and "INVALID" not in status and "!" not in status:
        return f"{Colors.GREEN}{status}{Colors.RESET}"
    elif "MISSING" in status or "ERROR" in status or "CORRUPTED" in status:
        return f"{Colors.RED}{status}{Colors.RESET}"
    elif "INVALID" in status or "[!]" in status:
        return f"{Colors.YELLOW}{status}{Colors.RESET}"
    return f"{Violet.TEXT}{status}{Colors.RESET}"


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

def _health_menu_header() -> None:
    width = 52
    print()
    print(f"  {Violet.SURFACE}╔{'═' * width}╗{Colors.RESET}")
    print(f"  {Violet.SURFACE}║{Colors.RESET}  {Violet.BRIGHT}{Colors.BOLD}PROJECT HEALTH CHECK{Colors.RESET}{' ' * (width - 21)}{Violet.SURFACE}║{Colors.RESET}")
    print(f"  {Violet.SURFACE}╚{'═' * width}╝{Colors.RESET}")
    print()


def _health_menu(project_root: Path) -> None:
    """Display project health check."""
    _health_menu_header()
    
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

def _submenu_header(title: str, width: int = 50) -> None:
    print()
    print(f"  {Violet.SURFACE}╔{'═' * width}╗{Colors.RESET}")
    print(f"  {Violet.SURFACE}║{Colors.RESET}  {Violet.BRIGHT}{Colors.BOLD}{title}{Colors.RESET}{' ' * (width - len(title) - 2)}{Violet.SURFACE}║{Colors.RESET}")
    print(f"  {Violet.SURFACE}╚{'═' * width}╝{Colors.RESET}")
    print()


def _submenu_prompt(text: str = "Select") -> str:
    return input(f"  {Violet.ACCENT}▸{Colors.RESET} {Violet.TEXT_SOFT}{text}{Colors.RESET} ({Violet.TEXT_MUTED}0={Colors.RESET}{Violet.TEXT_SOFT}back{Colors.RESET}): ").strip()


def _snapshot_menu(project_root: Path, state: AppState) -> None:
    """Snapshot menu with error handling."""
    print()
    if _confirm("Scan project files?"):
        print_info("Initializing PROJECT CONTROL if needed, then scanning project files...")
        result = run_interactive_scan(project_root)
        if result.success:
            initialization = result.data.get("initialization")
            if initialization and getattr(initialization, "initialized_now", False):
                print_info("PROJECT CONTROL was initialized for this project.")
            print_success("Snapshot created successfully!")
        else:
            print_error(result.message)
    input("\nPress Enter to return...")


def _graph_menu(project_root: Path, state: AppState) -> None:
    """Graph menu with error handling."""
    _submenu_header("Graph")
    print_menu_item("1", "Build / Rebuild graph")
    print_menu_item("2", "Show graph report")
    print()
    choice = _submenu_prompt()
    
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
    _submenu_header("Analyze")
    print_menu_item("1", "Ghost detectors", "Shallow analysis")
    print_menu_item("2", "Structural metrics", "From graph")
    print()
    choice = _submenu_prompt()
    
    if choice == "1":
        with ErrorContext("Running ghost analysis"):
            ghost_fast(project_root)
    elif choice == "2":
        with ErrorContext("Running structural analysis"):
            ghost_structural(project_root, state)
    
    input("\nPress Enter to return...")


def _explore_menu(project_root: Path, state: AppState) -> AppState:
    """Explore menu with error handling and favorites."""
    _submenu_header("Trace Dependencies")
    dir_label = DIRECTION_LABELS.get(state.trace_direction, state.trace_direction)
    print(f"  {Violet.LIGHT}Direction:{Colors.RESET} {dir_label}  {Violet.LIGHT}Depth:{Colors.RESET} {state.trace_depth}  {Violet.LIGHT}All paths:{Colors.RESET} {state.trace_all_paths}")

    if state.favorites:
        print()
        print(f"  {Violet.TEXT_MUTED}Favorites:{Colors.RESET}")
        for i, fav in enumerate(state.favorites, 1):
            print(f"    {Violet.BRIGHT}[{i}]{Colors.RESET} {fav}")
        print(f"    {Violet.BRIGHT}[f]{Colors.RESET} Add current target to favorites")

    print()
    target = _submenu_prompt(f"Target ({Violet.TEXT_MUTED}path, symbol, or [1-{len(state.favorites)}]{Colors.RESET}{Violet.TEXT_SOFT} for favorite{Colors.RESET})")

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

        _submenu_header("Configuration")
        print(f"  {Violet.BRIGHT}{Colors.BOLD}Basic{Colors.RESET}")
        print(f"  {Violet.ELEVATED}{'─' * 46}{Colors.RESET}")
        print()
        print_menu_item("1", f"Project Type:  [{Violet.BRIGHT}{mode_label}{Colors.RESET}]")
        print_menu_item("2", f"Strictness:    [{Violet.BRIGHT}{profile_label}{Colors.RESET}]")
        print_menu_item("3", f"Output Format: [{Violet.BRIGHT}Tree files{Colors.RESET} {Violet.GLOW}★{Colors.RESET}]")
        print()
        print(f"  {Violet.BRIGHT}{Colors.BOLD}Advanced{Colors.RESET}")
        print(f"  {Violet.ELEVATED}{'─' * 46}{Colors.RESET}")
        print()
        print_menu_item("4", "Trace Options", "direction, depth, all paths")
        print()
        print(f"  {Violet.ACCENT}?{Colors.RESET}  Help — {Violet.TEXT_MUTED}What do these mean?{Colors.RESET}")
        print(f"  {Violet.ACCENT}0{Colors.RESET}  Back to main menu {Violet.TEXT_MUTED}(saves automatically){Colors.RESET}")
        print()
        choice = _submenu_prompt("1-4, ?")

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
    _submenu_header("Project Type")
    print(f"  {Violet.TEXT_SOFT}What kind of project is this?{Colors.RESET}")
    print()
    print_menu_item("1", "JavaScript/TypeScript", "JS, TS, JSX, TSX files")
    print_menu_item("2", "Python", ".py files")
    print_menu_item("3", "Mixed", "Both JS/TS and Python")
    print()
    print(f"  {Violet.TEXT_MUTED}Most projects are auto-detected. Choose this{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}only if auto-detection is wrong.{Colors.RESET}")
    print()
    
    choice = _submenu_prompt("1-3")
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
            ui_verification_headless=state.ui_verification_headless,
            ui_theme_preset=state.ui_theme_preset,
            last_ui_verification_profile=state.last_ui_verification_profile,
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
    _submenu_header("Strictness Level")
    print(f"  {Violet.TEXT_SOFT}How strict should the analysis be?{Colors.RESET}")
    print()
    print(f"  {Violet.ACCENT}1{Colors.RESET}  {Colors.BOLD}Pragmatic{Colors.RESET} {Violet.GLOW}(Recommended){Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Balanced approach{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Some false positives allowed{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Good for everyday use{Colors.RESET}")
    print()
    print(f"  {Violet.ACCENT}2{Colors.RESET}  {Colors.BOLD}Strict{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}More rigorous analysis{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Fewer false positives{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}More noise, but more accurate{Colors.RESET}")
    print()
    
    choice = _submenu_prompt("1-2")
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
            ui_verification_headless=state.ui_verification_headless,
            ui_theme_preset=state.ui_theme_preset,
            last_ui_verification_profile=state.last_ui_verification_profile,
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
    _submenu_header("Output Format")
    print(f"  {Violet.GLOW}★{Colors.RESET} {Colors.BOLD}Recommended:{Colors.RESET} {Violet.LIGHT}ASCII Tree Files{Colors.RESET}")
    print()
    print(f"  {Violet.LIGHT}What you get:{Colors.RESET}")
    print(f"    {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}ASCII Tree Files{Colors.RESET} {Violet.GLOW}★{Colors.RESET}")
    print(f"      {Violet.TEXT_MUTED}Visual structure, easy to read{Colors.RESET}")
    print(f"      {Violet.TEXT_MUTED}Perfect for human review{Colors.RESET}")
    print()
    print(f"    {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Markdown Reports{Colors.RESET}")
    print(f"      {Violet.TEXT_MUTED}Detailed analysis with explanations{Colors.RESET}")
    print()
    print(f"    {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}JSON Files{Colors.RESET}")
    print(f"      {Violet.TEXT_MUTED}For automation and tools{Colors.RESET}")
    print()
    print(f"  {Violet.TEXT_MUTED}Location: .project-control/exports/{Colors.RESET}")
    print()
    print(f"  {Violet.BRIGHT}◇{Colors.RESET} Tree files are human-readable and show file relationships clearly.")
    
    input("\nPress Enter...")


def _trace_options_menu(project_root: Path, state: AppState) -> AppState:
    """Advanced trace options menu."""
    while True:
        dir_label = DIRECTION_LABELS.get(state.trace_direction, state.trace_direction)
        
        _submenu_header("Trace Options (Advanced)")
        print(f"  {Violet.BRIGHT}1{Colors.RESET}  {Colors.BOLD}Direction:{Colors.RESET}  [{Violet.BRIGHT}{dir_label}{Colors.RESET}]")
        print(f"     {Violet.TEXT_MUTED}Inbound  = Who depends on this?{Colors.RESET}")
        print(f"     {Violet.TEXT_MUTED}Outbound = What does this depend on?{Colors.RESET}")
        print(f"     {Violet.TEXT_MUTED}Both     = Both directions{Colors.RESET}")
        print()
        print(f"  {Violet.BRIGHT}2{Colors.RESET}  {Colors.BOLD}Depth:{Colors.RESET}     [{Violet.BRIGHT}{state.trace_depth}{Colors.RESET}]")
        print(f"     {Violet.TEXT_MUTED}How many levels to trace{Colors.RESET}")
        print()
        print(f"  {Violet.BRIGHT}3{Colors.RESET}  {Colors.BOLD}All Paths:{Colors.RESET} [{Violet.BRIGHT}{'Yes' if state.trace_all_paths else 'No'}{Colors.RESET}]")
        print(f"     {Violet.TEXT_MUTED}Show all paths or just one per target{Colors.RESET}")
        print()
        choice = _submenu_prompt("1-3")
        
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
    _submenu_header("Configuration Help")
    print(f"  {Violet.LIGHT}PROJECT TYPE{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Determines which language features to analyze.{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Auto-detected by default. Change only if wrong.{Colors.RESET}")
    print()
    print(f"  {Violet.LIGHT}STRICTNESS{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Controls how strict the analysis is.{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Pragmatic = Balanced, good for everyday use{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Strict    = More rigorous, more accurate{Colors.RESET}")
    print()
    print(f"  {Violet.LIGHT}OUTPUT FORMAT{Colors.RESET}")
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
    _submenu_header("Main Menu Help")
    
    print(f"  {Violet.BRIGHT}{Colors.BOLD}QUICK ACTIONS{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Fast workflows for common tasks.{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Full Analysis = Scan → Find Issues → Dependencies{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Health Check  = Validate everything{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Quick Reports  = View all findings{Colors.RESET}")
    print()
    print(f"  {Violet.BRIGHT}{Colors.BOLD}MAIN TOOLS{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Individual tools for specific tasks.{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Scan Project   = Index your files{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Find Issues    = Dead code, orphans, duplicates{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Dependencies   = Trace imports & modules{Colors.RESET}")
    print()
    print(f"  {Violet.BRIGHT}{Colors.BOLD}ADVANCED{Colors.RESET}")
    print(f"    {Violet.TEXT_MUTED}Settings and help for power users.{Colors.RESET}")
    print()
    print(f"  {Violet.GLOW}Tip:{Colors.RESET} {Violet.TEXT_SOFT}Use 'Full Analysis' for a complete overview!{Colors.RESET}")
    
    input("\nPress Enter...")


def _reports_menu(project_root: Path) -> None:
    """View all available reports."""
    _submenu_header("Quick Reports")
    
    control_dir = project_root / ".project-control"
    exports_dir = control_dir / "exports"
    
    reports = []
    
    if exports_dir.exists():
        artifact_report = exports_dir / "artifact_candidates.md"
        if artifact_report.exists():
            reports.append(("Artifact Hygiene Report", artifact_report))

        ghost_report = exports_dir / "ghost_candidates.md"
        if ghost_report.exists():
            reports.append(("Ghost Analysis", ghost_report))
        
        graph_report = exports_dir / "graph.report.md"
        if graph_report.exists():
            reports.append(("Graph Report", graph_report))
        
        checklist = exports_dir / "checklist.md"
        if checklist.exists():
            reports.append(("File Checklist", checklist))

        ui_verify_report = exports_dir / "ui_verification_report.md"
        if ui_verify_report.exists():
            reports.append(("UI Verification Report", ui_verify_report))

        vfx_report = exports_dir / "vfx_contract_audit_report.md"
        if vfx_report.exists():
            reports.append(("VFX Contract Audit", vfx_report))

        patron_report = exports_dir / "patron_path_contract_report.md"
        if patron_report.exists():
            reports.append(("Patron's Path Contract", patron_report))

        ecosystem_report = exports_dir / "ecosystem_health_report.md"
        if ecosystem_report.exists():
            reports.append(("Ecosystem Health Report", ecosystem_report))

        audit_retention_report = exports_dir / "audit_retention_candidates.md"
        if audit_retention_report.exists():
            reports.append(("Audit Retention Report", audit_retention_report))
        
        tree_files = list(exports_dir.glob("*_tree.txt"))
        if tree_files:
            reports.append((f"ASCII Trees ({len(tree_files)} files)", exports_dir))
    
    if not reports:
        print(f"  {Violet.TEXT_MUTED}No reports found yet.{Colors.RESET}")
        print(f"  {Violet.TEXT_MUTED}Run 'Full Analysis' or other tools to generate reports.{Colors.RESET}")
    else:
        print(f"  {Violet.TEXT_SOFT}Found {len(reports)} report(s):{Colors.RESET}\n")
        for i, (name, path) in enumerate(reports, 1):
            if path.is_file():
                size = path.stat().st_size / 1024
                print(f"  {Violet.BRIGHT}{i}{Colors.RESET}  {Colors.BOLD}{name}{Colors.RESET}")
                print(f"      {Violet.TEXT_MUTED}{path.name} ({size:.1f} KB){Colors.RESET}")
            else:
                print(f"  {Violet.BRIGHT}{i}{Colors.RESET}  {name}")
                print(f"      {Violet.TEXT_MUTED}Multiple files in {path.name}{Colors.RESET}")
    
    print(f"\n  {Violet.TEXT_MUTED}All reports are in: .project-control/exports/{Colors.RESET}")
    
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
            ui_verification_headless=state.ui_verification_headless,
            ui_theme_preset=state.ui_theme_preset,
            last_ui_verification_profile=state.last_ui_verification_profile,
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
            ui_verification_headless=state.ui_verification_headless,
            ui_theme_preset=state.ui_theme_preset,
            last_ui_verification_profile=state.last_ui_verification_profile,
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
            ui_verification_headless=state.ui_verification_headless,
            ui_theme_preset=state.ui_theme_preset,
            last_ui_verification_profile=state.last_ui_verification_profile,
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
            ui_verification_headless=state.ui_verification_headless,
            ui_theme_preset=state.ui_theme_preset,
            last_ui_verification_profile=state.last_ui_verification_profile,
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
        ui_verification_headless=state.ui_verification_headless,
        ui_theme_preset=state.ui_theme_preset,
        last_ui_verification_profile=state.last_ui_verification_profile,
    )
    save_state(project_root, state)
    print(f"  Trace all paths: {'Yes' if new_val else 'No'}")
    return state


def _tools_menu(project_root: Path) -> None:
    """Tools menu for backups, cache, and diagnostics."""
    while True:
        _submenu_header("Tools")
        print_menu_item("1", "List Backups", "show all available backups")
        print_menu_item("2", "Create Manual Backup", "create a named backup")
        print_menu_item("3", "Restore Backup", "restore from a backup")
        print_menu_item("4", "Delete Backup", "delete a specific backup")
        print_menu_item("5", "Cleanup Old Backups", "remove old backups (keep latest 5)")
        print_menu_item("6", "Clear Graph Cache", "remove .project-control/out/")
        print_menu_item("7", "Show Diagnostics", "display system information")
        print()
        choice = _submenu_prompt("0-7")

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
    _submenu_header("Available Backups")

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
    _submenu_header("Create Backup")

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
    _submenu_header("Restore Backup")

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
    _submenu_header("Delete Backup")

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
    _submenu_header("Cleanup Old Backups")

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
    _submenu_header("Clear Graph Cache")

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
    _submenu_header("Diagnostics")

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

    print_divider("━", 50)

    input("\nPress Enter to return...")


def _quick_actions_menu(project_root: Path, state: AppState) -> None:
    """Quick Actions menu for common operations."""
    while True:
        _submenu_header("Quick Actions")
        print_menu_item("1", "Full Analysis", "scan → ghost → graph → report")
        print_menu_item("2", "Health Check", "validate everything")
        print_menu_item("3", "Find Orphans", "quick orphan scan")
        print_menu_item("4", "Find Cycles", "quick cycle detection")
        print_menu_item("5", "Dependency Audit", "analyze dependency graph")
        print_menu_item("6", "VFX Audit", "audit FX contract compliance")
        print_menu_item("7", "UI Verify", "run configurable browser verification")
        print_menu_item("8", "Artifact Hygiene", "find temporary screenshots and debug assets")
        print_menu_item("9", "Audit Retention", "find stale generated audits and reports")
        print_menu_item("10", "Patron Path Audit", "smoke-test downstream contract")
        print_menu_item("11", "Ecosystem Health", "validate Nebula and downstream readiness")
        print_menu_item("12", "Favorites", "manage favorite trace targets")
        print_menu_item("13", "History", "view recent actions")
        print()
        choice = _submenu_prompt("0-13")

        if choice == "0":
            return
        elif choice == "1":
            _quick_full_analysis(project_root, state)
        elif choice == "10":
            _quick_patron_path_audit(project_root)
        elif choice == "11":
            _quick_ecosystem_health(project_root)
        elif choice == "12":
            _quick_health_check(project_root)
        elif choice == "13":
            _quick_find_orphans(project_root)
        elif choice == "4":
            _quick_find_cycles(project_root, state)
        elif choice == "5":
            _quick_dependency_audit(project_root, state)
        elif choice == "6":
            _quick_vfx_audit(project_root)
        elif choice == "7":
            state = _quick_ui_verify(project_root, state)
        elif choice == "8":
            _quick_artifact_hygiene(project_root)
        elif choice == "9":
            _quick_audit_retention(project_root)
        elif choice == "10":
            state = _quick_favorites_menu(project_root, state)
        elif choice == "11":
            _quick_history_menu(project_root, state)
        else:
            input("Invalid selection. Press Enter...")


def _quick_full_analysis(project_root: Path, state: AppState) -> None:
    """Quick full analysis: scan → ghost → graph → report."""
    _submenu_header("Full Analysis")
    print(f"  {Violet.TEXT_SOFT}This will run:{Colors.RESET}")
    print(f"    {Violet.ACCENT}1.{Colors.RESET} Scan project files")
    print(f"    {Violet.ACCENT}2.{Colors.RESET} Run ghost analysis")
    print(f"    {Violet.ACCENT}3.{Colors.RESET} Build dependency graph")
    print(f"    {Violet.ACCENT}4.{Colors.RESET} Show report")

    if not _confirm("\nProceed with full analysis?"):
        return

    print("\nStep 1/4: Initializing PROJECT CONTROL (if needed) and scanning project files...")
    result = run_interactive_scan(project_root)
    if result.success:
        initialization = result.data.get("initialization")
        if initialization and getattr(initialization, "initialized_now", False):
            print_info("PROJECT CONTROL was initialized for this project.")
        print_success("Scan complete")
    else:
        print_error(result.message)
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

    print()
    print_separator("thick", 50)
    print(f"  {Colors.GREEN}{Colors.BOLD}[OK]{Colors.RESET} Full analysis complete!")
    print_separator("thick", 50)

    input("\nPress Enter to return...")


def _quick_health_check(project_root: Path) -> None:
    """Quick health check."""
    _health_menu(project_root)


def _quick_find_orphans(project_root: Path) -> None:
    """Quick orphan scan."""
    _submenu_header("Find Orphans")

    try:
        with ErrorContext("Finding orphans"):
            ghost_fast(project_root)
    except Exception as e:
        ErrorHandler.handle(e, "Finding orphans")

    input("\nPress Enter to return...")


def _quick_find_cycles(project_root: Path, state: AppState) -> None:
    """Quick cycle detection."""
    _submenu_header("Find Cycles")

    try:
        with ErrorContext("Finding cycles"):
            ghost_structural(project_root, state)
    except Exception as e:
        ErrorHandler.handle(e, "Finding cycles")

    input("\nPress Enter to return...")


def _quick_dependency_audit(project_root: Path, state: AppState) -> None:
    """Dependency audit - analyze dependency graph."""
    _submenu_header("Dependency Audit")

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

    print()
    print_divider("━", 50)
    print_success("Dependency audit complete!")
    print_divider("━", 50)

    input("\nPress Enter to return...")


def _quick_vfx_audit(project_root: Path) -> None:
    """Quick VFX contract audit."""
    _submenu_header("VFX Contract Audit")

    try:
        with ErrorContext("Running VFX contract audit"):
            _result, markdown_path, json_path = run_vfx_contract_audit(project_root)
            print_success("VFX contract audit complete")
            print(f"Report saved: {markdown_path}")
            print(f"Data saved:   {json_path}")
            view_vfx_contract_report(project_root, show_content=True)
    except Exception as e:
        ErrorHandler.handle(e, "Running VFX contract audit")

    input("\nPress Enter to return...")


def _quick_patron_path_audit(project_root: Path) -> None:
    """Quick Patron's Path contract audit."""
    _submenu_header("Patron's Path Contract")

    try:
        with ErrorContext("Running Patron's Path audit"):
            _result, markdown_path, json_path = run_patron_path_audit(project_root)
            print_success("Patron's Path audit complete")
            print(f"Report saved: {markdown_path}")
            print(f"Data saved:   {json_path}")
            view_patron_path_report(project_root, show_content=True)
    except Exception as e:
        ErrorHandler.handle(e, "Running Patron's Path audit")

    input("\nPress Enter to return...")


def _quick_ecosystem_health(project_root: Path) -> None:
    """Quick ecosystem health check."""
    _submenu_header("Ecosystem Health")

    try:
        with ErrorContext("Running ecosystem health check"):
            result, markdown_path, json_path = run_ecosystem_health(project_root)
            print_success("Ecosystem health check complete")
            print(f"Overall status: {result['summary']['overallStatus']}")
            print(f"Report saved:   {markdown_path}")
            print(f"Data saved:     {json_path}")
            view_ecosystem_health_report(project_root, show_content=True)
    except Exception as e:
        ErrorHandler.handle(e, "Running ecosystem health check")

    input("\nPress Enter to return...")


def _quick_artifact_hygiene(project_root: Path) -> None:
    """Quick artifact hygiene workflow."""
    _submenu_header("Artifact Hygiene")

    args = argparse.Namespace(
        older_than=None,
        min_score=None,
        by_resolution=False,
        json=False,
        delete_list=False,
    )

    try:
        with ErrorContext("Running artifact hygiene"):
            artifact_data = run_artifact_hygiene(args, project_root)
            result = artifact_data["result"]
            summary = result.get("summary", {})
            paths = artifact_data["paths"]
            print_success("Artifact hygiene complete")
            print(f"Safe to delete now: {summary.get('safe_to_delete', 0)}")
            print(f"Reclaimable MB:     {summary.get('safe_to_delete_mb', 0)}")
            print(f"Duplicate groups:   {summary.get('duplicate_groups', 0)}")
            print(f"High confidence:    {summary.get('high_confidence_cleanup_candidates', 0)}")
            print(f"Markdown report:    {paths['markdown']}")
            print(f"JSON data:          {paths['json']}")
            print(f"Delete list:        {paths['delete_list']}")
    except Exception as e:
        ErrorHandler.handle(e, "Running artifact hygiene")

    input("\nPress Enter to return...")


def _quick_audit_retention(project_root: Path) -> None:
    """Quick audit retention workflow."""
    _submenu_header("Audit Retention")

    args = argparse.Namespace(
        older_than=None,
        min_score=None,
        keep_latest=None,
        by_family=False,
        json=False,
        delete_list=False,
    )

    try:
        with ErrorContext("Running audit retention"):
            retention_data = run_audit_retention(args, project_root)
            result = retention_data["result"]
            summary = result.get("summary", {})
            paths = retention_data["paths"]
            print_success("Audit retention complete")
            print(f"Safe to delete now: {summary.get('safe_to_delete', 0)}")
            print(f"Reclaimable MB:     {summary.get('safe_to_delete_mb', 0)}")
            print(f"Duplicate groups:   {summary.get('duplicate_groups', 0)}")
            print(f"High confidence:    {summary.get('high_confidence_cleanup_candidates', 0)}")
            print(f"Families detected:  {summary.get('families_detected', 0)}")
            print(f"Markdown report:    {paths['markdown']}")
            print(f"JSON data:          {paths['json']}")
            print(f"Delete list:        {paths['delete_list']}")
    except Exception as e:
        ErrorHandler.handle(e, "Running audit retention")

    input("\nPress Enter to return...")


def _quick_ui_verify(project_root: Path, state: AppState) -> AppState:
    """Quick UI verification using discovered project profiles."""
    _submenu_header("UI Verification")

    profiles = list_ui_verification_profiles(project_root)
    valid_profiles = [profile for profile in profiles if profile.is_valid]
    selected_profile_name: str | None = None

    if state.last_ui_verification_profile:
        remembered_profile = next(
            (
                profile
                for profile in valid_profiles
                if profile.name.lower() == state.last_ui_verification_profile.lower()
            ),
            None,
        )
        if remembered_profile is not None:
            selected_profile_name = remembered_profile.name
            print_info(f"Using remembered profile: {selected_profile_name}")
        elif len(valid_profiles) > 1:
            print_warning(
                f"Remembered profile '{state.last_ui_verification_profile}' is no longer available."
            )

    if selected_profile_name is None and len(valid_profiles) > 1:
        selected_profile_name = _pick_ui_verification_profile(valid_profiles)
        if selected_profile_name is None:
            return state
    elif selected_profile_name is None and len(valid_profiles) == 1:
        selected_profile_name = valid_profiles[0].name

    config_path = get_default_ui_verification_config_path(project_root)
    if not profiles:
        print_warning("UI verification profile not found.")
        print(f"Create: {config_path}")

        template_path = Path(__file__).resolve().parents[2] / "examples" / "new" / "ui_verification.flowra.yaml"
        if template_path.exists():
            print(f"Template: {template_path}")

        input("\nPress Enter to return...")
        return state

    if not valid_profiles:
        print_warning("No valid UI verification profiles found.")
        for profile in profiles:
            print(f"- {profile.name}: {profile.error or 'Invalid profile'}")
        input("\nPress Enter to return...")
        return state

    try:
        with ErrorContext("Running UI verification"):
            _report, resolved_config_path, markdown_path, json_path, html_path = run_ui_verification_profile(
                project_root,
                profile_name=selected_profile_name,
                headless=state.ui_verification_headless,
                include_html=True,
            )
            print_success("UI verification complete")
            print(f"Profile: {resolved_config_path}")
            print(f"Report:  {markdown_path}")
            print(f"Data:    {json_path}")
            if html_path is not None:
                print(f"HTML:    {html_path}")
            state.last_ui_verification_profile = selected_profile_name
            save_state(project_root, state)
            view_ui_verification_report(project_root, show_content=True)
    except Exception as e:
        ErrorHandler.handle(e, "Running UI verification")

    input("\nPress Enter to return...")
    return state


def _pick_ui_verification_profile(profiles: list) -> str | None:
    """Prompt the user to choose one of the discovered UI verification profiles."""

    print("\nAvailable UI verification profiles:")
    for index, profile in enumerate(profiles, 1):
        default_label = " [default]" if profile.is_default else ""
        print(f"  {index}) {profile.name}{default_label} - {profile.app_name}")

    choice = input("\nSelect profile (0=cancel): ").strip()
    if not choice or choice == "0":
        return None

    try:
        selected_index = int(choice) - 1
    except ValueError:
        print_error("Please enter a valid number")
        input("\nPress Enter to return...")
        return None

    if 0 <= selected_index < len(profiles):
        return profiles[selected_index].name

    print_error("Invalid selection")
    input("\nPress Enter to return...")
    return None


def _quick_favorites_menu(project_root: Path, state: AppState) -> AppState:
    """Manage favorite trace targets."""
    while True:
        _submenu_header("Favorites")

        if not state.favorites:
            print(f"  {Violet.TEXT_MUTED}No favorites saved yet.{Colors.RESET}")
        else:
            print(f"  {Violet.TEXT_SOFT}Favorites ({len(state.favorites)}):{Colors.RESET}")
            for i, fav in enumerate(state.favorites, 1):
                print(f"    {Violet.BRIGHT}{i}{Colors.RESET}  {fav}")

        print()
        print_menu_item("1", "Add current target to favorites")
        print_menu_item("2", "Trace a favorite")
        print_menu_item("3", "Remove a favorite")
        print()
        choice = _submenu_prompt("0-3")

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
    _submenu_header("Recent Actions")

    if not state.history:
        print(f"  {Violet.TEXT_MUTED}No recent actions recorded.{Colors.RESET}")
    else:
        print(f"  {Violet.TEXT_SOFT}Recent actions ({len(state.history)}):{Colors.RESET}")
        for i, action in enumerate(state.history, 1):
            print(f"    {Violet.BRIGHT}{i}{Colors.RESET}  {action}")

    print_divider("─", 50)

    input("\nPress Enter to return...")


def _confirm(summary: str) -> bool:
    print(f"  {Violet.TEXT_SOFT}{summary}{Colors.RESET}")
    resp = input(f"  {Violet.ACCENT}▸{Colors.RESET} Proceed? {Violet.TEXT_MUTED}[y/N]{Colors.RESET}: ").strip().lower()
    return resp == "y"


# ── Presets Menu ─────────────────────────────────────────────────────────

def _presets_menu(project_root: Path) -> None:
    """Project presets management menu."""
    from project_control.config.presets import PresetManager

    manager = PresetManager(project_root)

    while True:
        clear_screen()
        _submenu_header("Project Presets")

        current = manager.get_current_preset_name()
        if current:
            print(f"  {Violet.LIGHT}Current preset:{Colors.RESET} {Violet.BRIGHT}{current}{Colors.RESET}")
        else:
            print(f"  {Violet.TEXT_MUTED}Current configuration: Custom{Colors.RESET}")

        print()
        print_menu_item("1", "List Presets", "Show all available presets")
        print_menu_item("2", "Apply Preset", "Apply a preset to project")
        print_menu_item("3", "Save Custom", "Save current config as custom preset")
        print_menu_item("4", "Delete Custom", "Delete a custom preset")
        print()
        choice = _submenu_prompt("1-4, B")

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
    _submenu_header("Available Presets")

    presets = manager.list_presets()
    for preset in presets:
        cat = Violet.BRIGHT + "builtin" + Colors.RESET if preset["category"] == "builtin" else Violet.LIGHT + "custom" + Colors.RESET
        print(f"  {Violet.ACCENT}◆{Colors.RESET}  {Colors.BOLD}{preset['name']}{Colors.RESET}  [{cat}]")
        print(f"      {Violet.TEXT_MUTED}{preset['description']}{Colors.RESET}")

    input("\nPress Enter to return...")


def _preset_apply_submenu(manager: PresetManager) -> None:
    """Apply a preset."""
    clear_screen()
    _submenu_header("Apply Preset")

    presets = manager.list_presets()
    print(f"  {Violet.TEXT_SOFT}Available presets:{Colors.RESET}\n")
    for i, preset in enumerate(presets, 1):
        print(f"  {Violet.BRIGHT}{i}{Colors.RESET}  {Colors.BOLD}{preset['name']}{Colors.RESET}")
        print(f"      {Violet.TEXT_MUTED}{preset['description']}{Colors.RESET}")

    choice = _submenu_prompt("preset number")
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
    _submenu_header("Save Custom Preset")

    name = input(f"\n  {Violet.ACCENT}▸{Colors.RESET} Preset name: ").strip()
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
    _submenu_header("Delete Custom Preset")

    presets = [p for p in manager.list_presets() if p["category"] == "custom"]

    if not presets:
        print_info("No custom presets found.")
        input("\nPress Enter to return...")
        return

    print(f"  {Violet.TEXT_SOFT}Custom presets:{Colors.RESET}\n")
    for i, preset in enumerate(presets, 1):
        print(f"  {Violet.BRIGHT}{i}{Colors.RESET}  {Colors.BOLD}{preset['name']}{Colors.RESET}")
        print(f"      {Violet.TEXT_MUTED}{preset['description']}{Colors.RESET}")

    choice = _submenu_prompt("preset to delete")
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
        _submenu_header("Export / Import State")

        print_menu_item("1", "Export State", "Export current settings to file")
        print_menu_item("2", "Import State", "Import settings from file")
        print()
        choice = _submenu_prompt("1-2, B")

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
    _submenu_header("Export State")

    print(f"  {Violet.TEXT_SOFT}Export options:{Colors.RESET}\n")
    print_menu_item("1", "Export with metadata", "includes project-specific info")
    print_menu_item("2", "Export without metadata", "portable, git-friendly")

    choice = _submenu_prompt("1-2")
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
    _submenu_header("Import State")

    import_path_str = input(f"\n  {Violet.ACCENT}▸{Colors.RESET} Path to import file: ").strip()
    if not import_path_str:
        print_error("Path is required")
        input("\nPress Enter to return...")
        return

    import_path = Path(import_path_str)
    if not import_path.exists():
        print_error(f"File not found: {import_path}")
        input("\nPress Enter to return...")
        return

    print(f"\n  {Violet.TEXT_SOFT}Import mode:{Colors.RESET}")
    print(f"    {Violet.BRIGHT}1{Colors.RESET}  Replace  {Violet.TEXT_MUTED}— Replace all settings{Colors.RESET}")
    print(f"    {Violet.BRIGHT}2{Colors.RESET}  Merge    {Violet.TEXT_MUTED}— Merge with existing settings{Colors.RESET}")

    mode_choice = _submenu_prompt("1-2")
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

        rel_path = explorer.get_current_path().relative_to(project_root)
        _submenu_header(f"File Explorer — {rel_path}")

        # Show directory listing
        output = explorer.render_file_list()
        _safe_print(output)

        print(f"  {Violet.LIGHT}Actions:{Colors.RESET}")
        print(f"    {Violet.ACCENT}[path]{Colors.RESET}  {Violet.TEXT_MUTED}—{Colors.RESET} Change to directory {Violet.TEXT_MUTED}(e.g., 'src', '..'){Colors.RESET}")
        print(f"    {Violet.ACCENT}D [path]{Colors.RESET} {Violet.TEXT_MUTED}—{Colors.RESET} Show file/directory details")
        print(f"    {Violet.ACCENT}S [term]{Colors.RESET} {Violet.TEXT_MUTED}—{Colors.RESET} Search files")
        print(f"    {Violet.ACCENT}U{Colors.RESET}       {Violet.TEXT_MUTED}—{Colors.RESET} Go up one level")
        print(f"    {Violet.ACCENT}R{Colors.RESET}       {Violet.TEXT_MUTED}—{Colors.RESET} Refresh")
        print(f"    {Violet.ACCENT}B{Colors.RESET}       {Violet.TEXT_MUTED}—{Colors.RESET} Back to main menu")

        choice = _submenu_prompt("command")

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
                _submenu_header(f"Search: {term}")
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
        stdout_encoding = sys.stdout.encoding or "utf-8"
        if sys.platform == "win32":
            safe_text = text.encode(stdout_encoding, errors="replace").decode(stdout_encoding)
            print(safe_text)
        else:
            try:
                print(text.encode("utf-8", errors="replace").decode("utf-8"))
            except Exception:
                print(text.encode("ascii", errors="replace").decode("ascii"))
