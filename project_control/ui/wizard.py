"""Wizard Mode for interactive first-time setup."""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from project_control.ui.state import AppState, load_state, save_state
from project_control.utils.terminal import (
    print_success, print_warning, print_info, print_header, Colors,
    print_brand_header, print_step, Violet
)


@dataclass
class WizardStep:
    """A single step in the wizard."""
    
    step_number: int
    total_steps: int
    title: str
    description: str
    options: List[Dict[str, str]]
    default_option: int = 0
    
    def render(self) -> str:
        """Render the wizard step as a formatted string."""
        lines = []
        
        # Header with double-line border (premium feel)
        lines.append("╔" + "═" * 51 + "╗")
        lines.append(f"║  Welcome to PROJECT CONTROL!{' ' * 24}║")
        lines.append("╟" + "─" * 51 + "╢")
        lines.append("║                                              ║")
        
        # Step info
        lines.append(f"║  Step {self.step_number}/{self.total_steps}: {self.title:<30}║")
        lines.append("║                                              ║")
        lines.append("╟" + "─" * 51 + "╢")
        lines.append("║                                              ║")
        
        # Description
        for line in self._wrap_text(self.description, 48):
            lines.append(f"║  {line:<48}║")
        lines.append("║                                              ║")
        
        # Options with refined selector
        for i, option in enumerate(self.options, 1):
            if i - 1 == self.default_option:
                marker = "▸"
            else:
                marker = " "
            lines.append(f"║  {marker} {i}) {option['label']:<35}║")
        
        lines.append("║                                              ║")
        
        # Footer
        lines.append("╟" + "─" * 51 + "╢")
        lines.append("║  [1-{}] Select                       ║".format(len(self.options)))
        lines.append("║  [S] Skip (use defaults)            ║")
        lines.append("║  [Q] Quit                           ║")
        lines.append("║                                              ║")
        lines.append("╚" + "═" * 51 + "╝")
        
        return "\n".join(lines)
    
    def _wrap_text(self, text: str, width: int) -> List[str]:
        """Wrap text to fit within specified width."""
        words = text.split()
        lines = []
        current_line = ""
        
        for word in words:
            if not current_line:
                current_line = word
            elif len(current_line) + len(word) + 1 <= width:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines


@dataclass
class WizardConfig:
    """Configuration collected during wizard."""
    project_type: str = "js_ts"  # js_ts | python | mixed
    strictness: str = "pragmatic"  # pragmatic | strict
    output_format: str = "tree"  # tree | both | reports (tree is recommended)
    run_first_scan: bool = True


class Wizard:
    """Interactive wizard for first-time setup."""
    
    def __init__(self, project_root: Path):
        """Initialize the wizard.
        
        Args:
            project_root: Path to the project root directory
        """
        self.project_root = project_root
        self.config = WizardConfig()
        self.current_step = 0
        self.steps = self._create_steps()
    
    def _create_steps(self) -> List[WizardStep]:
        """Create wizard steps."""
        return [
            WizardStep(
                step_number=1,
                total_steps=4,
                title="Project Type",
                description="What kind of project is this? This helps us choose the right analysis tools.",
                options=[
                    {"label": "JavaScript/TypeScript", "value": "js_ts"},
                    {"label": "Python", "value": "python"},
                    {"label": "Mixed (JS + Python)", "value": "mixed"},
                ],
                default_option=0
            ),
            WizardStep(
                step_number=2,
                total_steps=4,
                title="Analysis Strictness",
                description="How strict should the analysis be? Pragmatic is recommended for most projects.",
                options=[
                    {"label": "Pragmatic (recommended)", "value": "pragmatic"},
                    {"label": "Strict (more thorough)", "value": "strict"},
                ],
                default_option=0
            ),
            WizardStep(
                step_number=3,
                total_steps=4,
                title="Output Format",
                description="What format do you prefer for results? Tree files are human-readable and easy to understand.",
                options=[
                    {"label": "Tree files only (ASCII) ⭐ recommended", "value": "tree"},
                    {"label": "Both reports and trees", "value": "both"},
                    {"label": "Reports only (Markdown)", "value": "reports"},
                ],
                default_option=0
            ),
            WizardStep(
                step_number=4,
                total_steps=4,
                title="First Scan",
                description="Would you like to run your first analysis now? This will index your project files.",
                options=[
                    {"label": "Yes, scan now", "value": "yes"},
                    {"label": "No, scan later", "value": "no"},
                ],
                default_option=0
            ),
        ]
    
    def run(self) -> WizardConfig:
        """Run the wizard and return the collected configuration.
        
        Returns:
            WizardConfig with user's choices
        """
        self._clear_screen()
        self._show_welcome()
        input("\nPress Enter to continue or 'Q' to quit...")
        
        for step in self.steps:
            self._clear_screen()
            print(step.render())
            
            choice = self._get_user_input(step)
            
            if choice == "q":
                print_warning("\nWizard cancelled. Using default configuration.")
                return self.config
            elif choice == "s":
                print_info("Using default for this step.")
                continue
            
            # Apply user's choice
            option_index = int(choice) - 1
            selected_value = step.options[option_index]["value"]
            self._apply_choice(step.step_number, selected_value)
        
        # Save configuration
        self._save_configuration()
        
        # Show completion
        self._show_completion()
        
        return self.config
    
    def _show_welcome(self) -> None:
        """Show welcome screen."""
        print()
        print_brand_header("Welcome to PROJECT CONTROL!", "Architectural Analysis Engine")
        print()
        print(f"  {Violet.TEXT_SOFT}PROJECT CONTROL helps you understand your codebase structure{Colors.RESET}")
        print(f"  {Violet.TEXT_MUTED}and find dead code, orphans, and dependencies.{Colors.RESET}")
        print()
        print_info("We'll walk you through a few quick setup steps:")
        print()
        print_step("1", "Choose your project type")
        print_step("2", "Select analysis strictness")
        print_step("3", "Pick your preferred output format")
        print_step("4", "Run your first scan")
        print()
        print_warning("You can skip any step by pressing 'S'")
        print(f"  {Violet.TEXT_MUTED}You can quit the wizard by pressing 'Q'{Colors.RESET}")
    
    def _show_completion(self) -> None:
        """Show completion screen."""
        self._clear_screen()
        print()
        print_success("Setup Complete!")
        print()
        print_info("Your configuration:")
        print()
        print(f"  {Violet.LIGHT}Project Type:{Colors.RESET}   {self._format_project_type(self.config.project_type)}")
        print(f"  {Violet.LIGHT}Strictness:{Colors.RESET}     {self.config.strictness.capitalize()}")
        print(f"  {Violet.LIGHT}Output Format:{Colors.RESET}  {self._format_output_format(self.config.output_format)}")
        print(f"  {Violet.LIGHT}First Scan:{Colors.RESET}     {'Yes' if self.config.run_first_scan else 'No'}")
        print()
        
        if self.config.run_first_scan:
            print_info("NEXT STEPS:")
            print()
            print(f"  {Violet.TEXT_MUTED}Run these commands to get started:{Colors.RESET}")
            print()
            print_step("1", "pc scan        — Index your project files")
            print_step("2", "pc ghost       — Find issues")
            print_step("3", "pc graph build — Build dependency graph")
            print()
            print_success("Ready to analyze!")
        else:
            print_info("READY TO GO!")
            print()
            print(f"  {Violet.TEXT_MUTED}Your settings are saved. When you're ready:{Colors.RESET}")
            print()
            print_step("1", "pc scan        — Index your project files")
            print_step("2", "pc ghost       — Find issues")
            print_step("3", "pc ghost --tree — View ASCII results")
            print()
            print_success("Configuration saved!")
        
        input("\nPress Enter to continue...")
    
    def _get_user_input(self, step: WizardStep) -> str:
        """Get and validate user input.
        
        Args:
            step: Current wizard step
            
        Returns:
            Validated user input (number, 's', or 'q')
        """
        while True:
            try:
                choice = input("  Selection: ").strip().lower()
                
                if choice == "q":
                    return "q"
                elif choice == "s":
                    return "s"
                elif choice.isdigit() and 1 <= int(choice) <= len(step.options):
                    return choice
                else:
                    print_warning(f"Please enter 1-{len(step.options)}, 'S', or 'Q'")
            except (EOFError, KeyboardInterrupt):
                print("\n")
                return "q"
    
    def _apply_choice(self, step_number: int, value: str) -> None:
        """Apply user's choice to configuration.
        
        Args:
            step_number: Step number (1-4)
            value: Selected value
        """
        if step_number == 1:
            self.config.project_type = value
        elif step_number == 2:
            self.config.strictness = value
        elif step_number == 3:
            self.config.output_format = value
        elif step_number == 4:
            self.config.run_first_scan = (value == "yes")
    
    def _save_configuration(self) -> None:
        """Save wizard configuration to app state."""
        state = load_state(self.project_root)
        
        # Update state with wizard config
        new_state = AppState(
            project_mode=self.config.project_type,
            graph_profile=self.config.strictness,
            trace_direction=state.trace_direction,
            trace_depth=state.trace_depth,
            trace_all_paths=state.trace_all_paths,
            ui_verification_headless=state.ui_verification_headless,
            favorites=state.favorites,
            history=state.history,
            onboarding_seen=True,  # Mark onboarding as complete
            last_ui_verification_profile=state.last_ui_verification_profile,
        )
        
        save_state(self.project_root, new_state)
        print_info("Configuration saved!")
    
    def _format_project_type(self, project_type: str) -> str:
        """Format project type for display."""
        mapping = {
            "js_ts": "JavaScript/TypeScript",
            "python": "Python",
            "mixed": "Mixed (JS + Python)",
        }
        return mapping.get(project_type, project_type)
    
    def _format_output_format(self, output_format: str) -> str:
        """Format output format for display."""
        mapping = {
            "both": "Reports + Trees",
            "reports": "Reports only",
            "tree": "Tree files only",
        }
        return mapping.get(output_format, output_format)
    
    def _clear_screen(self) -> None:
        """Clear terminal screen in a cross-platform way."""
        import subprocess
        try:
            if sys.platform == "win32":
                subprocess.run(["cls"], shell=True, check=False)
            else:
                subprocess.run(["clear"], shell=True, check=False)
        except Exception:
            pass  # Silently fail - screen clearing is not critical


def should_run_wizard(project_root: Path, force: bool = False) -> bool:
    """Check if wizard should be run.
    
    Args:
        project_root: Path to project root
        force: Force wizard to run even if already completed
        
    Returns:
        True if wizard should run, False otherwise
    """
    if force:
        return True
    
    state = load_state(project_root)
    return not state.onboarding_seen


def run_wizard(project_root: Path, force: bool = False) -> Optional[WizardConfig]:
    """Run the wizard if appropriate.
    
    Args:
        project_root: Path to project root
        force: Force wizard to run even if already completed
        
    Returns:
        WizardConfig if wizard was run, None otherwise
    """
    if not should_run_wizard(project_root, force):
        return None
    
    wizard = Wizard(project_root)
    return wizard.run()


def mark_wizard_completed(project_root: Path) -> None:
    """Persist the wizard completion marker."""
    state = load_state(project_root)
    save_state(
        project_root,
        AppState(
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
        ),
    )


def clear_wizard_mark(project_root: Path) -> None:
    """Clear the wizard completion marker."""
    state = load_state(project_root)
    save_state(
        project_root,
        AppState(
            project_mode=state.project_mode,
            graph_profile=state.graph_profile,
            trace_direction=state.trace_direction,
            trace_depth=state.trace_depth,
            trace_all_paths=state.trace_all_paths,
            ui_verification_headless=state.ui_verification_headless,
            favorites=state.favorites,
            history=state.history,
            onboarding_seen=False,
            last_ui_verification_profile=state.last_ui_verification_profile,
        ),
    )
