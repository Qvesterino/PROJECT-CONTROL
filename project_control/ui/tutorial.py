"""Interactive Tutorial System for PROJECT_CONTROL.

Provides step-by-step walkthroughs that guide users through actual workflows
with explanations and interactive execution.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional

from project_control.utils.terminal import (
    print_success, print_warning, print_info, print_header, Colors,
    print_error
)


@dataclass
class TutorialStep:
    """A single step in an interactive tutorial."""
    
    step_number: int
    total_steps: int
    title: str
    explanation: str
    action_type: str  # "command", "menu", "info", "input"
    action_data: Optional[Dict] = None
    expected_result: str = ""
    
    def render(self) -> str:
        """Render the tutorial step as a formatted string."""
        lines = []
        
        # Header with step info
        lines.append("┌" + "─" * 60 + "┐")
        lines.append(f"│  📚 Tutorial: Step {self.step_number}/{self.total_steps}{' ' * (34 - len(str(self.step_number)))}│")
        lines.append("├" + "─" * 60 + "┤")
        lines.append("│                                              │")
        
        # Title
        title_lines = self._wrap_text(self.title, 58)
        lines.append(f"│  {title_lines[0]:<58}│")
        if len(title_lines) > 1:
            for line in title_lines[1:]:
                lines.append(f"│  {line:<58}│")
        lines.append("│                                              │")
        
        # Explanation
        lines.append("├" + "─" * 60 + "┤")
        lines.append("│  What you'll do:                            │")
        lines.append("│                                              │")
        for line in self._wrap_text(self.explanation, 56, indent=4):
            lines.append(f"│{line:<62}│")
        lines.append("│                                              │")
        
        # Action
        lines.append("├" + "─" * 60 + "┤")
        if self.action_type == "command":
            cmd = self.action_data.get("command", "")
            lines.append("│  Run this command:                           │")
            lines.append("│                                              │")
            lines.append(f"│  {Colors.CYAN}${Colors.RESET} {cmd}{' ' * (54 - len(cmd))}│")
            lines.append("│                                              │")
        elif self.action_type == "menu":
            menu_items = self.action_data.get("menu_items", [])
            lines.append("│  In the menu, select:                        │")
            lines.append("│                                              │")
            for item in menu_items:
                lines.append(f"│  → {item:<52}│")
            lines.append("│                                              │")
        elif self.action_type == "input":
            prompt = self.action_data.get("prompt", "")
            lines.append("│  Enter this when prompted:                   │")
            lines.append("│                                              │")
            lines.append(f"│  {Colors.CYAN}{prompt}{Colors.RESET}{' ' * (54 - len(prompt))}│")
            lines.append("│                                              │")
        
        # Expected result
        if self.expected_result:
            lines.append("├" + "─" * 60 + "┤")
            lines.append("│  What to expect:                             │")
            lines.append("│                                              │")
            for line in self._wrap_text(self.expected_result, 56, indent=4):
                lines.append(f"│{line:<62}│")
            lines.append("│                                              │")
        
        # Footer
        lines.append("├" + "─" * 60 + "┤")
        lines.append("│  [D] Do it now    [S] Skip step    [Q] Quit     │")
        lines.append("│                                              │")
        lines.append("└" + "─" * 60 + "┘")
        
        return "\n".join(lines)
    
    def _wrap_text(self, text: str, width: int, indent: int = 0) -> List[str]:
        """Wrap text to fit within specified width."""
        words = text.split()
        lines = []
        current_line = ""
        indent_str = " " * indent
        
        for word in words:
            if not current_line:
                current_line = indent_str + word
            elif len(current_line) + len(word) + 1 <= width + indent:
                current_line += " " + word
            else:
                lines.append(current_line)
                current_line = indent_str + word
        
        if current_line:
            lines.append(current_line)
        
        return lines


@dataclass
class Tutorial:
    """A complete interactive tutorial."""
    
    name: str
    description: str
    duration: str  # "5 minutes", "3 minutes", etc.
    difficulty: str  # "Beginner", "Intermediate", "Advanced"
    steps: List[TutorialStep]
    
    def run(self, project_root: Path) -> bool:
        """Run the tutorial.
        
        Args:
            project_root: Path to project root
            
        Returns:
            True if tutorial was completed, False if quit
        """
        self._clear_screen()
        self._show_intro()
        
        input("\n" + " " * 20 + "Press Enter to start or 'Q' to quit...")
        
        for step in self.steps:
            self._clear_screen()
            print(step.render())
            
            choice = self._get_user_input()
            
            if choice == "q":
                self._clear_screen()
                print_warning("Tutorial quit.")
                print_info("You can restart anytime from Help & Docs → Tutorial")
                input("\nPress Enter to return...")
                return False
            elif choice == "s":
                self._clear_screen()
                print_info(f"Step {step.step_number} skipped.")
                input("\nPress Enter to continue...")
                continue
            elif choice == "d":
                # User wants to do it - guide them
                self._clear_screen()
                print_header(f"Step {step.step_number}: {step.title}")
                print()
                print_info("Follow these instructions:")
                print()
                self._show_step_instructions(step)
                input("\n\nPress Enter when you're done...")
                
                # Show expected result
                if step.expected_result:
                    self._clear_screen()
                    print_header(f"Step {step.step_number}: {step.title}")
                    print()
                    print_info("Expected result:")
                    print()
                    print(f"  {step.expected_result}")
                    print()
                    input("\nPress Enter to continue...")
        
        # Tutorial completed
        self._show_completion()
        return True
    
    def _show_intro(self) -> None:
        """Show tutorial introduction."""
        print()
        print_header(f"📚 TUTORIAL: {self.name}")
        print()
        print(f"  Difficulty:  {self.difficulty}")
        print(f"  Duration:    {self.duration}")
        print()
        print(f"  {self.description}")
        print()
        print_info("This tutorial will guide you through each step with:")
        print()
        print("  • Clear explanations of what you're doing")
        print("  • Step-by-step instructions")
        print("  • Expected results")
        print("  • Ability to skip steps if needed")
        print()
        print_warning("You can quit anytime by pressing 'Q'")
        print()
    
    def _show_step_instructions(self, step: TutorialStep) -> None:
        """Show detailed instructions for a step."""
        print(f"\n{step.explanation}\n")
        
        if step.action_type == "command":
            cmd = step.action_data.get("command", "")
            print(f"{Colors.CYAN}Run this command:{Colors.RESET}")
            print(f"  {cmd}")
            print()
        elif step.action_type == "menu":
            print(f"{Colors.CYAN}In the menu:{Colors.RESET}")
            for item in step.action_data.get("menu_items", []):
                print(f"  • {item}")
            print()
        elif step.action_type == "input":
            prompt = self.action_data.get("prompt", "")
            print(f"{Colors.CYAN}Enter this when prompted:{Colors.RESET}")
            print(f"  {prompt}")
            print()
    
    def _show_completion(self) -> None:
        """Show tutorial completion screen."""
        self._clear_screen()
        print()
        print_success("✅ Tutorial Completed!")
        print()
        print_info(f"You've learned: {self.name}")
        print()
        print("What you can do now:")
        print()
        print("  • Try running the workflow on your own")
        print("  • Explore other tutorials")
        print("  • Check the documentation for more details")
        print()
        print_success("Great job! 🎉")
        print()
        input("Press Enter to return...")
    
    def _get_user_input(self) -> str:
        """Get and validate user input."""
        while True:
            try:
                choice = input("  Your choice [D/S/Q]: ").strip().lower()
                
                if choice in ["d", "s", "q"]:
                    return choice
                else:
                    print_warning("Please enter 'D', 'S', or 'Q'")
            except (EOFError, KeyboardInterrupt):
                print("\n")
                return "q"
    
    def _clear_screen(self) -> None:
        """Clear terminal screen."""
        import subprocess
        try:
            if sys.platform == "win32":
                subprocess.run(["cls"], shell=True, check=False)
            else:
                subprocess.run(["clear"], shell=True, check=False)
        except Exception:
            pass


# ── Tutorial Library ─────────────────────────────────────────────────────

def get_basic_workflow_tutorial() -> Tutorial:
    """Get the basic workflow tutorial."""
    return Tutorial(
        name="Basic Workflow",
        description="Learn the essential PROJECT_CONTROL workflow: scan your project, find issues, and analyze dependencies.",
        duration="5 minutes",
        difficulty="Beginner",
        steps=[
            TutorialStep(
                step_number=1,
                total_steps=4,
                title="Scan Your Project",
                explanation="First, we need to index all files in your project. This creates a snapshot that captures the current state.",
                action_type="command",
                action_data={"command": "pc scan"},
                expected_result="You'll see a message like 'Scanning...' followed by the number of files indexed. A .project-control/ directory will be created."
            ),
            TutorialStep(
                step_number=2,
                total_steps=4,
                title="Find Issues with Ghost Analysis",
                explanation="Now we'll run ghost analysis to find orphans (unused files), legacy code, duplicates, and other issues.",
                action_type="command",
                action_data={"command": "pc ghost"},
                expected_result="Ghost analysis will run and show counts for orphans, legacy files, sessions, duplicates, and semantic outliers. Results are saved to .project-control/exports/ghost_candidates.md"
            ),
            TutorialStep(
                step_number=3,
                total_steps=4,
                title="Build Dependency Graph",
                explanation="Let's build a dependency graph to understand how files depend on each other.",
                action_type="command",
                action_data={"command": "pc graph build"},
                expected_result="The graph will be built showing import relationships. You'll see the number of nodes (files) and edges (imports). Graph data is saved in .project-control/out/"
            ),
            TutorialStep(
                step_number=4,
                total_steps=4,
                title="View the Report",
                explanation="Finally, let's view the analysis report to see what we found.",
                action_type="command",
                action_data={"command": "pc graph report"},
                expected_result="A detailed report will be displayed showing graph metrics, orphan candidates, cycles, and more. The full report is in .project-control/out/graph.report.md"
            )
        ]
    )


def find_orphans_tutorial() -> Tutorial:
    """Get the find orphans tutorial."""
    return Tutorial(
        name="Find and Remove Orphans",
        description="Learn how to find unused files (orphans) and safely remove them to clean up your codebase.",
        duration="3 minutes",
        difficulty="Beginner",
        steps=[
            TutorialStep(
                step_number=1,
                total_steps=4,
                title="Run Ghost Analysis",
                explanation="We'll start by running ghost analysis to find all orphans in your project.",
                action_type="command",
                action_data={"command": "pc ghost"},
                expected_result="Ghost analysis will complete and show you how many orphans were found."
            ),
            TutorialStep(
                step_number=2,
                total_steps=4,
                title="View Orphan Report",
                explanation="Open the ghost report to see the list of orphans with their paths and reasons.",
                action_type="info",
                action_data={
                    "file_path": ".project-control/exports/ghost_candidates.md"
                },
                expected_result="You'll see a Markdown file listing all orphans with file paths, severity levels, and reasons why they were flagged."
            ),
            TutorialStep(
                step_number=3,
                total_steps=4,
                title="Review Orphans Carefully",
                explanation="Before deleting, review each orphan to make sure it's truly unused. Some might be dynamically imported or used in ways static analysis can't detect.",
                action_type="info",
                action_data={
                    "tip": "Check if files are imported dynamically, used in tests, or referenced in configuration files."
                },
                expected_result="You'll have a list of orphans you're confident are safe to delete."
            ),
            TutorialStep(
                step_number=4,
                total_steps=4,
                title="Delete Orphans",
                explanation="Delete the orphan files you've reviewed and confirmed are unused.",
                action_type="command",
                action_data={"command": "# Delete the orphan files manually or use your file manager"},
                expected_result="Your codebase is now cleaner! Run 'pc ghost' again to verify the orphans are gone."
            )
        ]
    )


def trace_dependencies_tutorial() -> Tutorial:
    """Get the trace dependencies tutorial."""
    return Tutorial(
        name="Trace File Dependencies",
        description="Learn how to trace which files depend on a specific file, and what that file depends on.",
        duration="4 minutes",
        difficulty="Intermediate",
        steps=[
            TutorialStep(
                step_number=1,
                total_steps=3,
                title="Build the Graph First",
                explanation="Before we can trace dependencies, we need to have a dependency graph built.",
                action_type="command",
                action_data={"command": "pc graph build"},
                expected_result="The graph will be built. If it's already built and up-to-date, it will use the cached version."
            ),
            TutorialStep(
                step_number=2,
                total_steps=3,
                title="Trace a Specific File",
                explanation="Choose a file you want to analyze and trace its dependencies. Replace 'src/utils.js' with your file path.",
                action_type="command",
                action_data={"command": "pc graph trace src/utils.js"},
                expected_result="You'll see both inbound dependencies (what depends on this file) and outbound dependencies (what this file depends on)."
            ),
            TutorialStep(
                step_number=3,
                total_steps=3,
                title="Trace in One Direction",
                explanation="You can also trace only inbound or only outbound dependencies.",
                action_type="command",
                action_data={"command": "pc graph trace src/utils.js --direction inbound"},
                expected_result="You'll see only the files that depend on src/utils.js. This is useful for understanding the impact of changing a file."
            )
        ]
    )


def interactive_menu_tutorial() -> Tutorial:
    """Get the interactive menu tutorial."""
    return Tutorial(
        name="Interactive Menu Guide",
        description="Learn how to use the interactive menu (pc ui) to perform all tasks without remembering commands.",
        duration="4 minutes",
        difficulty="Beginner",
        steps=[
            TutorialStep(
                step_number=1,
                total_steps=4,
                title="Launch the Menu",
                explanation="Start the interactive menu system.",
                action_type="command",
                action_data={"command": "pc ui"},
                expected_result="You'll see the main menu with Quick Actions, Main Tools, and Advanced sections."
            ),
            TutorialStep(
                step_number=2,
                total_steps=4,
                title="Use Quick Actions",
                explanation="The Quick Actions section at the top provides fast access to common workflows.",
                action_type="menu",
                action_data={
                    "menu_items": [
                        "Select '1' for Full Analysis",
                        "This will scan, find issues, and build dependencies automatically"
                    ]
                },
                expected_result="The full analysis workflow will run step by step with progress indicators."
            ),
            TutorialStep(
                step_number=3,
                total_steps=4,
                title="Find Issues",
                explanation="Use the Find Issues menu to run specific analyses.",
                action_type="menu",
                action_data={
                    "menu_items": [
                        "Select '5' for Find Issues",
                        "Then select '1' for Ghost detectors or '2' for Structural metrics"
                    ]
                },
                expected_result="Your chosen analysis will run and show results."
            ),
            TutorialStep(
                step_number=4,
                total_steps=4,
                title="Access Help",
                explanation="Press '?' in any menu to see context-sensitive help explaining what each option does.",
                action_type="menu",
                action_data={
                    "menu_items": [
                        "Press '?' at the main menu",
                        "Read the explanations for Quick Actions, Main Tools, and Advanced"
                    ]
                },
                expected_result="You'll see detailed explanations of each menu option."
            )
        ]
    )


# ── Tutorial Manager ────────────────────────────────────────────────────

class TutorialManager:
    """Manages available tutorials and provides tutorial selection."""
    
    def __init__(self, project_root: Path):
        """Initialize tutorial manager.
        
        Args:
            project_root: Path to project root
        """
        self.project_root = project_root
        self.tutorials = self._load_tutorials()
    
    def _load_tutorials(self) -> List[Tutorial]:
        """Load all available tutorials."""
        return [
            get_basic_workflow_tutorial(),
            find_orphans_tutorial(),
            trace_dependencies_tutorial(),
            interactive_menu_tutorial(),
        ]
    
    def list_tutorials(self) -> List[Dict]:
        """Get list of all tutorials with metadata."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "duration": t.duration,
                "difficulty": t.difficulty,
                "steps": len(t.steps)
            }
            for t in self.tutorials
        ]
    
    def get_tutorial(self, name: str) -> Optional[Tutorial]:
        """Get tutorial by name.
        
        Args:
            name: Tutorial name
            
        Returns:
            Tutorial if found, None otherwise
        """
        for tutorial in self.tutorials:
            if tutorial.name.lower() == name.lower():
                return tutorial
        return None
    
    def run_tutorial_menu(self) -> None:
        """Run the tutorial selection menu."""
        while True:
            self._clear_screen()
            print()
            print_header("📚 INTERACTIVE TUTORIALS")
            print()
            
            tutorials = self.list_tutorials()
            
            for i, tutorial in enumerate(tutorials, 1):
                difficulty_color = {
                    "Beginner": Colors.GREEN,
                    "Intermediate": Colors.YELLOW,
                    "Advanced": Colors.RED
                }.get(tutorial["difficulty"], "")
                
                print(f"{i}) {tutorial['name']}")
                print(f"   {tutorial['description']}")
                print(f"   Difficulty: {difficulty_color}{tutorial['difficulty']}{Colors.RESET} | Duration: {tutorial['duration']} | Steps: {tutorial['steps']}")
                print()
            
            print("0) Back to main menu")
            
            choice = input("\nSelect tutorial (1-{}, or 0): ".format(len(tutorials))).strip()
            
            if choice == "0":
                return
            elif choice.isdigit() and 1 <= int(choice) <= len(tutorials):
                index = int(choice) - 1
                tutorial = self.tutorials[index]
                tutorial.run(self.project_root)
            else:
                print_warning("Invalid selection. Press Enter...")
                input()
    
    def _clear_screen(self) -> None:
        """Clear terminal screen."""
        import subprocess
        try:
            if sys.platform == "win32":
                subprocess.run(["cls"], shell=True, check=False)
            else:
                subprocess.run(["clear"], shell=True, check=False)
        except Exception:
            pass