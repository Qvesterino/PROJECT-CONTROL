"""Onboarding module for new users."""

from __future__ import annotations

import sys
from pathlib import Path
from project_control.utils.terminal import (
    print_success, print_warning, print_info, print_header, Colors
)
from project_control.ui.state import AppState, load_state, save_state


def show_onboarding(project_root: Path) -> None:
    """Show onboarding message for new users."""
    clear_screen()
    
    print()
    print_header("Welcome to PROJECT CONTROL! 🎉")
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
    
    print_info("MAIN FEATURES")
    print()
    print("  • Scan      — Index all project files")
    print("  • Ghost     — Find orphans, duplicates, and dead code")
    print("  • Graph     — Build and analyze dependency graphs")
    print("  • Trace     — Follow import paths between modules")
    print("  • Dead      — Find unused files with low usage")
    print("  • Unused    — Detect unused systems/modules")
    print("  • Search    — Smart code search across your project")
    print("  • Explore   — Interactive file browser")
    print()
    
    print_info("GETTING HELP")
    print()
    print("  Run 'pc --help' to see all available commands")
    print("  Run 'pc ui' for interactive menu mode")
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
        favorites=state.favorites,
        history=state.history,
        onboarding_seen=True,
    )
    save_state(project_root, state)


def show_help_menu(project_root: Path) -> None:
    """Show help menu with common questions."""
    clear_screen()
    
    print()
    print_header("HELP & DOCUMENTATION")
    print()
    
    print_info("QUICK QUESTIONS")
    print()
    print("1) What does PROJECT CONTROL do?")
    print("   → It analyzes your codebase to find dead code,")
    print("     build dependency graphs, and understand structure.")
    print()
    
    print("2) How do I start?")
    print("   → Run these commands in order:")
    print("     1. pc scan")
    print("     2. pc ghost")
    print("     3. pc graph build")
    print()
    
    print("3) What are 'orphans'?")
    print("   → Files that exist in your project but are not")
    print("     imported by any other file. They might be dead code.")
    print()
    
    print("4) What is the dependency graph?")
    print("   → A map showing which files import which other files.")
    print("     Helps you understand your codebase structure.")
    print()
    
    print("5) How do I trace dependencies?")
    print("   → Run 'pc graph trace <file>' to see what imports")
    print("     that file and what that file imports.")
    print()
    
    print_info("COMMANDS")
    print()
    print("  pc --help        — Show all available commands")
    print("  pc scan          — Index project files")
    print("  pc ghost         — Find orphans and dead code")
    print("  pc graph build   — Build dependency graph")
    print("  pc graph trace   — Trace file dependencies")
    print("  pc dead          — Find unused files")
    print("  pc search <term> — Search in code")
    print("  pc explore       — Interactive file browser")
    print("  pc ui            — Interactive menu mode")
    print()
    
    print_info("CONFIGURATION")
    print()
    print("  • Project type is auto-detected (JS/TS/Python)")
    print("  • Settings saved in .project-control/config.json")
    print("  • Customize patterns in .project-control/patterns.yaml")
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