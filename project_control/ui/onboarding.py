"""Onboarding module for new users."""

from __future__ import annotations

import sys
from pathlib import Path
from project_control.utils.terminal import (
    print_success, print_warning, print_info, print_header, Colors, Violet,
    print_brand_header, print_notification, print_step
)
from project_control.ui.state import AppState, load_state, save_state


def show_onboarding(project_root: Path) -> None:
    """Show onboarding message for new users."""
    clear_screen()
    
    print()
    print_brand_header("Welcome to PROJECT CONTROL!", "Architectural Analysis Engine")
    
    print(f"  {Violet.TEXT_SOFT}PROJECT CONTROL is your architectural analysis engine.{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}It helps you understand your codebase structure and find dead code.{Colors.RESET}")
    print()
    
    print_info("QUICK START")
    print()
    print(f"  {Violet.TEXT_MUTED}The easiest way to get started is to run a quick analysis:{Colors.RESET}")
    print()
    print_step("1", "Run 'pc scan' to index your project files")
    print_step("2", "Run 'pc ghost' to find orphans and dead code")
    print_step("3", "Run 'pc graph build' to analyze dependencies")
    print()
    print(f"  {Violet.TEXT_MUTED}In the GUI or TUI, the Run Scan action also initializes{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}PROJECT CONTROL automatically the first time you use it.{Colors.RESET}")
    print()
    
    print_info("MAIN FEATURES")
    print()
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Scan{Colors.RESET}      — Index all project files")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Ghost{Colors.RESET}     — Find orphans, duplicates, and dead code")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Graph{Colors.RESET}     — Build and analyze dependency graphs")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Trace{Colors.RESET}     — Follow import paths between modules")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Dead{Colors.RESET}      — Find unused files with low usage")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Unused{Colors.RESET}   — Detect unused systems/modules")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Search{Colors.RESET}    — Smart code search across your project")
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Colors.BOLD}Explore{Colors.RESET}   — Interactive file browser")
    print()
    
    print_info("GETTING HELP")
    print()
    print(f"  {Violet.TEXT_MUTED}Run 'pc --help' to see all available commands{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}Run 'pc tui' for the TUI text-based menu{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}From a source checkout on Windows: use '.\\pc.ps1 gui' or '.\\pc.cmd tui'{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}Check README.md for detailed documentation{Colors.RESET}")
    print()
    
    print_warning("Note: Your project type (JS/TS/Python) is auto-detected")
    print(f"      {Violet.TEXT_MUTED}You can change it in settings if needed.{Colors.RESET}")
    print()
    print_header("Welcome to PROJECT CONTROL!")
    print()
    
    print("PROJECT CONTROL is your architectural analysis engine.")
    print("It helps you understand your codebase structure and find dead code.")
    print()
    
    print_info("QUICK START")
    print()
    print("The easiest way to get started is to run a quick analysis:")
    print()
    print("  Step 1: Run 'pc scan' to index your project files")
    print("  Step 2: Run 'pc ghost' to find orphans and dead code")
    print("  Step 3: Run 'pc graph build' to analyze dependencies")
    print()
    print("  In the GUI or TUI, the Run Scan action also initializes")
    print("  PROJECT CONTROL automatically the first time you use it.")
    print()
    
    print_info("MAIN FEATURES")
    print()
    print("  * Scan      - Index all project files")
    print("  * Ghost     - Find orphans, duplicates, and dead code")
    print("  * Graph     - Build and analyze dependency graphs")
    print("  * Trace     - Follow import paths between modules")
    print("  * Dead      - Find unused files with low usage")
    print("  * Unused    - Detect unused systems/modules")
    print("  * Search    - Smart code search across your project")
    print("  * Explore   - Interactive file browser")
    print()
    
    print_info("GETTING HELP")
    print()
    print("  Run 'pc --help' to see all available commands")
    print("  Run 'pc tui' for the TUI text-based menu")
    print("  From a source checkout on Windows: use '.\\pc.ps1 gui' or '.\\pc.cmd tui'")
    print("  Check README.md for detailed documentation")
    print()
    
    print_warning("Note: Your project type (JS/TS/Python) is auto-detected")
    print("      You can change it in settings if needed.")
    print()
    
    input("Press Enter to continue...")
    
    # Mark onboarding as seen
    state = load_state(project_root)
    state = AppState(
        project_mode=state.project_mode,
        graph_profile=state.graph_profile,
        trace_direction=state.trace_direction,
        trace_depth=state.trace_depth,
        trace_all_paths=state.trace_all_paths,
        ui_verification_headless=state.ui_verification_headless,
        favorites=state.favorites,
        history=state.history,
        onboarding_seen=True,
        last_ui_verification_profile=state.last_ui_verification_profile,
    )
    save_state(project_root, state)


def show_help_menu(project_root: Path) -> None:
    """Show help menu with common questions."""
    clear_screen()
    
    print()
    print_brand_header("Help & Documentation")
    
    print_info("GETTING STARTED")
    print()
    print(f"  {Violet.ACCENT}1){Colors.RESET}  {Colors.BOLD}Interactive Tutorial{Colors.RESET}  {Violet.TEXT_MUTED}— Step-by-step walkthrough{Colors.RESET}")
    print(f"  {Violet.ACCENT}2){Colors.RESET}  {Colors.BOLD}Quick Questions{Colors.RESET}       {Violet.TEXT_MUTED}— Common questions answered{Colors.RESET}")
    print(f"  {Violet.ACCENT}3){Colors.RESET}  {Colors.BOLD}Command Reference{Colors.RESET}     {Violet.TEXT_MUTED}— All commands at a glance{Colors.RESET}")
    print()
    
    choice = input("\nSelect (1-3, or 0 to go back): ").strip()
    
    if choice == "1":
        from project_control.ui.tutorial import TutorialManager
        tutorial_manager = TutorialManager(project_root)
        tutorial_manager.run_tutorial_menu()
        return
    elif choice == "2":
        _show_quick_questions()
        return
    elif choice == "3":
        _show_command_reference()
        return
    elif choice == "0":
        return
    else:
        print_warning("Invalid selection.")
        input("\nPress Enter...")
        return


def _show_quick_questions() -> None:
    """Show common quick questions."""
    clear_screen()
    
    print()
    print_header("Quick Questions")
    print()
    
    print_info("QUICK QUESTIONS")
    print()
    print(f"  {Violet.BRIGHT}1){Colors.RESET} {Colors.BOLD}What does PROJECT CONTROL do?{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}It analyzes your codebase to find dead code,{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}build dependency graphs, and understand structure.{Colors.RESET}")
    print()
    
    print(f"  {Violet.BRIGHT}2){Colors.RESET} {Colors.BOLD}How do I start?{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Run these commands in order:{Colors.RESET}")
    print(f"     {Violet.ACCENT}1.{Colors.RESET} pc scan")
    print(f"     {Violet.ACCENT}2.{Colors.RESET} pc ghost")
    print(f"     {Violet.ACCENT}3.{Colors.RESET} pc graph build")
    print(f"     {Violet.TEXT_MUTED}In the GUI/TUI, Run Scan also handles first-time setup.{Colors.RESET}")
    print()
    
    print(f"  {Violet.BRIGHT}3){Colors.RESET} {Colors.BOLD}What are 'orphans'?{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Files that exist in your project but are not{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}imported by any other file. They might be dead code.{Colors.RESET}")
    print()
    
    print(f"  {Violet.BRIGHT}4){Colors.RESET} {Colors.BOLD}What is the dependency graph?{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}A map showing which files import which other files.{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Helps you understand your codebase structure.{Colors.RESET}")
    print()
    
    print(f"  {Violet.BRIGHT}5){Colors.RESET} {Colors.BOLD}How do I trace dependencies?{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}Run 'pc graph trace <file>' to see what imports{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}that file and what that file imports.{Colors.RESET}")
    print()
    
    input("\nPress Enter to return...")


def _show_command_reference() -> None:
    """Show command reference."""
    clear_screen()
    
    print()
    print_header("Command Reference")
    print()
    
    print_info("COMMANDS")
    print()
    print(f"  {Violet.ACCENT}pc --help{Colors.RESET}        {Violet.TEXT_MUTED}— Show all available commands{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc scan{Colors.RESET}          {Violet.TEXT_MUTED}— Index project files{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc ghost{Colors.RESET}         {Violet.TEXT_MUTED}— Find orphans and dead code{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc graph build{Colors.RESET}   {Violet.TEXT_MUTED}— Build dependency graph{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc graph trace{Colors.RESET}   {Violet.TEXT_MUTED}— Trace file dependencies{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc audit vfx{Colors.RESET}     {Violet.TEXT_MUTED}— Audit VFX contract compliance{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc artifacts{Colors.RESET}     {Violet.TEXT_MUTED}— Find temporary screenshots and debug assets{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc audits retention{Colors.RESET} {Violet.TEXT_MUTED}— Find stale generated audits and reports{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc tui verify{Colors.RESET}     {Violet.TEXT_MUTED}— Run browser-based UI verification{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc tui verify --list-profiles{Colors.RESET} {Violet.TEXT_MUTED}— List discovered UI verification profiles{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc tui verify --profile <name>{Colors.RESET} {Violet.TEXT_MUTED}— Run a specific UI verification profile{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc gui{Colors.RESET}           {Violet.TEXT_MUTED}— Launch desktop GUI mode{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc dead{Colors.RESET}          {Violet.TEXT_MUTED}— Find unused files{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc search <term>{Colors.RESET} {Violet.TEXT_MUTED}— Search in code{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc explore{Colors.RESET}       {Violet.TEXT_MUTED}— Interactive file browser{Colors.RESET}")
    print(f"  {Violet.ACCENT}pc tui{Colors.RESET}           {Violet.TEXT_MUTED}— Launch the TUI text-based menu{Colors.RESET}")
    print(f"  {Violet.ACCENT}.\\pc.ps1 gui{Colors.RESET}     {Violet.TEXT_MUTED}— Repo-local Windows GUI launcher{Colors.RESET}")
    print(f"  {Violet.ACCENT}.\\pc.cmd tui{Colors.RESET}     {Violet.TEXT_MUTED}— Repo-local Windows TUI launcher{Colors.RESET}")
    print()
    
    print_info("CONFIGURATION")
    print()
    print(f"  {Violet.TEXT_MUTED}• Project type is auto-detected (JS/TS/Python){Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}• Settings saved in .project-control/config.json{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}• Customize patterns in .project-control/patterns.yaml{Colors.RESET}")
    print(f"  {Violet.TEXT_MUTED}• UI verification profiles live in .project-control/ui-profiles/{Colors.RESET}")
    print()
    
    input("\nPress Enter to return...")


def clear_screen() -> None:
    """Clear terminal screen in a cross-platform way."""
    import subprocess
    try:
        if sys.platform == "win32":
            subprocess.run(["cls"], shell=True, check=False)
        else:
            subprocess.run(["clear"], shell=True, check=False)
    except Exception:
        pass  # Silently fail - screen clearing is not critical


def should_show_onboarding(project_root: Path) -> bool:
    """Check if onboarding should be shown."""
    state = load_state(project_root)
    return not state.onboarding_seen
