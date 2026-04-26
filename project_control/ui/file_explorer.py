"""Interactive File Explorer with metadata and dependency info."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from project_control.utils.tables import Table


@dataclass
class FileInfo:
    """Information about a file."""

    path: str
    name: str
    is_dir: bool
    size: int
    modified: str
    extensions: List[str] = None

    def __post_init__(self):
        if self.extensions is None:
            self.extensions = []


@dataclass
class DependencyInfo:
    """Dependency information for a file."""

    inbound: List[str] = None  # Files that import this file
    outbound: List[str] = None  # Files that this file imports
    is_orphan: bool = False
    in_cycle: bool = False

    def __post_init__(self):
        if self.inbound is None:
            self.inbound = []
        if self.outbound is None:
            self.outbound = []


class FileExplorer:
    """Interactive file explorer with dependency info."""

    def __init__(
        self,
        project_root: Path,
        graph_data: Optional[Dict[str, Any]] = None,
        metrics_data: Optional[Dict[str, Any]] = None
    ):
        """Initialize file explorer.

        Args:
            project_root: Root path of the project
            graph_data: Optional pre-loaded graph data
            metrics_data: Optional pre-loaded metrics data
        """
        self.project_root = project_root
        self.current_path = project_root
        self.graph_data = graph_data or self._load_graph()
        self.metrics_data = metrics_data or self._load_metrics()
        self.path_to_id: Dict[str, int] = {}
        self.id_to_path: Dict[int, str] = {}

        if self.graph_data:
            self._build_node_mappings()

    def _load_graph(self) -> Optional[Dict[str, Any]]:
        """Load graph data from file."""
        graph_path = self.project_root / ".project-control" / "out" / "graph.snapshot.json"
        if not graph_path.exists():
            return None
        try:
            return json.loads(graph_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return None

    def _load_metrics(self) -> Optional[Dict[str, Any]]:
        """Load metrics data from file."""
        metrics_path = self.project_root / ".project-control" / "out" / "graph.metrics.json"
        if not metrics_path.exists():
            return None
        try:
            return json.loads(metrics_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            return None

    def _build_node_mappings(self) -> None:
        """Build path-to-id and id-to-path mappings from graph."""
        if not self.graph_data:
            return

        for node in self.graph_data.get("nodes", []):
            node_id = node["id"]
            node_path = node["path"]
            self.path_to_id[node_path] = node_id
            self.id_to_path[node_id] = node_path

    def list_directory(self, path: Optional[Path] = None) -> List[FileInfo]:
        """List files in a directory.

        Args:
            path: Path to list (default: current_path)

        Returns:
            List of FileInfo objects
        """
        target_path = path or self.current_path
        if not target_path.exists():
            return []

        files: List[FileInfo] = []

        # List directories first, then files
        try:
            entries = sorted(target_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return []

        for entry in entries:
            # Skip hidden files and .project-control
            if entry.name.startswith(".") and entry.name != ".project-control":
                continue

            try:
                stat = entry.stat()
                size = stat.st_size
                modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                exts = []
                if not entry.is_dir():
                    exts = [entry.suffix]

                files.append(FileInfo(
                    path=str(entry.relative_to(self.project_root)),
                    name=entry.name,
                    is_dir=entry.is_dir(),
                    size=size,
                    modified=modified,
                    extensions=exts
                ))
            except (OSError, PermissionError):
                continue

        return files

    def get_dependency_info(self, file_path: str) -> DependencyInfo:
        """Get dependency information for a file.

        Args:
            file_path: Path to the file (relative to project root)

        Returns:
            DependencyInfo object
        """
        info = DependencyInfo()

        if not self.graph_data:
            return info

        # Find node ID
        node_id = self.path_to_id.get(file_path)
        if node_id is None:
            return info

        # Get inbound (who imports this)
        for edge in self.graph_data.get("edges", []):
            if edge["target"] == node_id:
                source_path = self.id_to_path.get(edge["source"])
                if source_path:
                    info.inbound.append(source_path)
            elif edge["source"] == node_id:
                target_path = self.id_to_path.get(edge["target"])
                if target_path:
                    info.outbound.append(target_path)

        # Check if orphan
        if self.metrics_data:
            orphans = self.metrics_data.get("orphanCandidates", [])
            info.is_orphan = any(file_path in o for o in orphans) or file_path in orphans

            # Check if in cycle
            for cycle in self.metrics_data.get("cycles", []):
                if node_id in cycle:
                    info.in_cycle = True
                    break

        return info

    def render_file_list(self, path: Optional[Path] = None, max_width: int = 120) -> str:
        """Render file list as a table.

        Args:
            path: Path to list (default: current_path)
            max_width: Maximum width for table

        Returns:
            Rendered table as string
        """
        files = self.list_directory(path)

        if not files:
            return "No files found."

        table = Table(["Name", "Type", "Size", "Modified", "Status"])

        for file_info in files:
            # Determine type
            if file_info.is_dir:
                file_type = "DIR"
                size_str = "-"
            else:
                file_type = file_info.extensions[0] if file_info.extensions else "FILE"
                size_str = self._format_size(file_info.size)

            # Get status indicators
            status = []
            if not file_info.is_dir:
                dep_info = self.get_dependency_info(file_info.path)
                if dep_info.is_orphan:
                    status.append("ORPHAN")
                if dep_info.in_cycle:
                    status.append("CYCLE")
                if not dep_info.inbound and not dep_info.is_orphan:
                    status.append("NO-REFS")

            status_str = ", ".join(status) if status else "-"

            table.add_row([file_info.name, file_type, size_str, file_info.modified, status_str])

        return table.render(title=f"Directory: {(path or self.current_path).relative_to(self.project_root)}", max_width=max_width)

    def render_file_details(self, file_path: str) -> str:
        """Render detailed information about a file.

        Args:
            file_path: Path to the file (relative to project root)

        Returns:
            Detailed information as string
        """
        full_path = self.project_root / file_path
        if not full_path.exists():
            return f"File not found: {file_path}"

        # Basic info
        lines: List[str] = []
        lines.append("=" * 60)
        lines.append(f"FILE: {file_path}")
        lines.append("=" * 60)

        try:
            stat = full_path.stat()
            lines.append(f"Size:       {self._format_size(stat.st_size)}")
            lines.append(f"Modified:   {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append(f"Type:       {'Directory' if full_path.is_dir() else 'File'}")
        except (OSError, PermissionError):
            lines.append("Could not read file metadata")

        lines.append("")

        # Dependency info
        if not full_path.is_dir():
            dep_info = self.get_dependency_info(file_path)
            lines.append("DEPENDENCY INFO:")
            lines.append("-" * 60)
            lines.append(f"Orphan:     {'YES' if dep_info.is_orphan else 'NO'}")
            lines.append(f"In Cycle:   {'YES' if dep_info.in_cycle else 'NO'}")

            lines.append(f"\nInbound ({len(dep_info.inbound)}):  # Files that import this")
            if dep_info.inbound:
                for imp in dep_info.inbound[:10]:  # Show first 10
                    lines.append(f"  - {imp}")
                if len(dep_info.inbound) > 10:
                    lines.append(f"  ... and {len(dep_info.inbound) - 10} more")
            else:
                lines.append("  (none)")

            lines.append(f"\nOutbound ({len(dep_info.outbound)}): # Files that this imports")
            if dep_info.outbound:
                for imp in dep_info.outbound[:10]:  # Show first 10
                    lines.append(f"  - {imp}")
                if len(dep_info.outbound) > 10:
                    lines.append(f"  ... and {len(dep_info.outbound) - 10} more")
            else:
                lines.append("  (none)")

        return "\n".join(lines)

    def change_directory(self, path: str) -> bool:
        """Change current directory.

        Args:
            path: Relative or absolute path

        Returns:
            True if successful, False otherwise
        """
        target = self.current_path / path if not Path(path).is_absolute() else Path(path)

        if not target.exists():
            return False

        if not target.is_dir():
            return False

        # Ensure it's still within project root
        try:
            target.relative_to(self.project_root)
        except ValueError:
            return False

        self.current_path = target
        return True

    def go_up(self) -> bool:
        """Go up one directory level.

        Returns:
            True if successful, False if already at root
        """
        if self.current_path == self.project_root:
            return False

        self.current_path = self.current_path.parent
        return True

    def get_current_path(self) -> Path:
        """Get current directory path.

        Returns:
            Current path
        """
        return self.current_path

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format.

        Args:
            size: Size in bytes

        Returns:
            Formatted size string
        """
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"

    def search_files(self, pattern: str) -> List[FileInfo]:
        """Search for files matching a pattern.

        Args:
            pattern: Search pattern (simple substring match)

        Returns:
            List of matching FileInfo objects
        """
        results = []

        for root, dirs, files in os.walk(self.project_root):
            # Skip hidden directories
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            for filename in files:
                if pattern.lower() in filename.lower():
                    full_path = Path(root) / filename
                    rel_path = full_path.relative_to(self.project_root)

                    try:
                        stat = full_path.stat()
                        size = stat.st_size
                        modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")

                        exts = [full_path.suffix] if full_path.suffix else []

                        results.append(FileInfo(
                            path=str(rel_path),
                            name=filename,
                            is_dir=False,
                            size=size,
                            modified=modified,
                            extensions=exts
                        ))
                    except (OSError, PermissionError):
                        continue

        return results


# ── Interactive File Explorer with Keyboard Navigation ──────────────────────

try:
    from readchar import readkey, key
    READCHAR_AVAILABLE = True
except ImportError:
    READCHAR_AVAILABLE = False

try:
    from rich.console import Console
    from rich.table import Table as RichTable
    from rich.panel import Panel
    from rich.text import Text
    from rich.style import Style
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


class InteractiveFileExplorer:
    """Fully interactive file explorer with keyboard navigation."""

    def __init__(
        self,
        project_root: Path,
        graph_data: Optional[Dict[str, Any]] = None,
        metrics_data: Optional[Dict[str, Any]] = None,
        max_visible: int = 20
    ):
        """Initialize interactive file explorer.

        Args:
            project_root: Root path of the project
            graph_data: Optional pre-loaded graph data
            metrics_data: Optional pre-loaded metrics data
            max_visible: Maximum number of files to show at once
        """
        if not READCHAR_AVAILABLE or not RICH_AVAILABLE:
            raise ImportError(
                "InteractiveFileExplorer requires 'readchar' and 'rich' packages. "
                "Install them with: pip install readchar rich"
            )

        self.explorer = FileExplorer(project_root, graph_data, metrics_data)
        self.console = Console()
        self.max_visible = max_visible

        # Interactive state
        self.selected_index: int = 0  # Currently selected file index
        self.scroll_offset: int = 0  # Scroll position
        self.files: List[FileInfo] = []  # Current file list
        self.running: bool = True

        # Help text
        self.help_text = [
            "[bold]Navigation:[/bold]",
            "  ↑/↓ or j/k - Move selection",
            "  Enter       - Enter directory / View file details",
            "  Backspace   - Go up directory",
            "  Home/End    - Jump to top/bottom",
            "  Page Up/Down- Scroll one page",
            "  /           - Search files",
            "  q/ESC       - Quit",
            "",
            "[bold]Actions:[/bold]",
            "  d           - View file details",
            "  r           - Refresh current view",
            "  h           - Show this help",
        ]

        # Refresh file list
        self._refresh_file_list()

    def _refresh_file_list(self) -> None:
        """Refresh the file list from current directory."""
        self.files = self.explorer.list_directory()
        # Reset selection
        self.selected_index = 0
        self.scroll_offset = 0

    def run(self) -> None:
        """Run the interactive file explorer loop."""
        self._render()
        while self.running:
            try:
                ch = readkey()
                self._handle_input(ch)
                if self.running:
                    self._render()
            except KeyboardInterrupt:
                self.running = False
                print("\nExiting...")
            except EOFError:
                self.running = False

    def _handle_input(self, key_char: str) -> None:
        """Handle keyboard input.

        Args:
            key_char: The character read from stdin
        """
        # Arrow keys and vim-like navigation
        if key_char in (key.UP, 'k'):
            self._move_selection(-1)
        elif key_char in (key.DOWN, 'j'):
            self._move_selection(1)
        elif key_char == key.PAGE_UP:
            self._move_selection(-self.max_visible)
        elif key_char == key.PAGE_DOWN:
            self._move_selection(self.max_visible)
        elif key_char == key.HOME:
            self._jump_to_top()
        elif key_char == key.END:
            self._jump_to_bottom()
        # Enter to enter directory or view details
        elif key_char == key.ENTER:
            self._enter_selected()
        # Backspace to go up
        elif key_char == key.BACKSPACE:
            self._go_up()
        # Quit
        elif key_char in ('q', key.ESC):
            self.running = False
        # File details
        elif key_char == 'd':
            self._show_details()
        # Refresh
        elif key_char == 'r':
            self._refresh_file_list()
        # Help
        elif key_char == 'h':
            self._show_help()
        # Search
        elif key_char == '/':
            self._search_mode()

    def _move_selection(self, delta: int) -> None:
        """Move selection by delta.

        Args:
            delta: Amount to move (positive = down, negative = up)
        """
        new_index = max(0, min(len(self.files) - 1, self.selected_index + delta))

        # Update scroll offset if needed
        if new_index < self.scroll_offset:
            self.scroll_offset = new_index
        elif new_index >= self.scroll_offset + self.max_visible:
            self.scroll_offset = new_index - self.max_visible + 1

        self.selected_index = new_index

    def _jump_to_top(self) -> None:
        """Jump to first file."""
        self.selected_index = 0
        self.scroll_offset = 0

    def _jump_to_bottom(self) -> None:
        """Jump to last file."""
        self.selected_index = len(self.files) - 1
        if len(self.files) > self.max_visible:
            self.scroll_offset = len(self.files) - self.max_visible

    def _enter_selected(self) -> None:
        """Enter selected directory or view file details."""
        if not self.files:
            return

        selected_file = self.files[self.selected_index]

        if selected_file.is_dir:
            # Enter directory
            if self.explorer.change_directory(selected_file.name):
                self._refresh_file_list()
            else:
                self._show_message(f"Cannot enter directory: {selected_file.name}", "error")
        else:
            # Show file details
            self._show_file_details(selected_file)

    def _go_up(self) -> None:
        """Go up one directory level."""
        if self.explorer.go_up():
            self._refresh_file_list()
        else:
            self._show_message("Already at project root", "warning")

    def _show_details(self) -> None:
        """Show details for selected file."""
        if not self.files:
            return

        selected_file = self.files[self.selected_index]
        self._show_file_details(selected_file)

    def _show_file_details(self, file_info: FileInfo) -> None:
        """Show detailed information about a file.

        Args:
            file_info: File to show details for
        """
        if file_info.is_dir:
            details = f"\n[bold]Directory:[/bold] {file_info.name}\n"
            details += f"[dim]Path:[/dim] {file_info.path}\n"
            details += f"[dim]Modified:[/dim] {file_info.modified}\n"
        else:
            details = self.explorer.render_file_details(file_info.path)
            # Convert to Rich format
            details = self._convert_to_rich_format(details)

        # Clear screen and show details
        self.console.clear()
        panel = Panel(
            details,
            title=f"[bold blue]File Details[/bold blue]",
            border_style="blue",
            padding=(1, 2)
        )
        self.console.print(panel)
        self.console.print("\n[dim]Press any key to continue...[/dim]")

        readkey()  # Wait for any key

    def _show_help(self) -> None:
        """Show help screen."""
        self.console.clear()
        help_panel = Panel(
            "\n".join(self.help_text),
            title="[bold cyan]Keyboard Shortcuts[/bold cyan]",
            border_style="cyan",
            padding=(1, 2)
        )
        self.console.print(help_panel)
        self.console.print("\n[dim]Press any key to continue...[/dim]")
        readkey()

    def _search_mode(self) -> None:
        """Enter search mode."""
        self.console.print("\n[bold yellow]Search:[/bold yellow] ", end="")

        # Simple search using input
        try:
            search_term = input("")
            if search_term.strip():
                results = self.explorer.search_files(search_term)
                if results:
                    self._show_search_results(results, search_term)
                else:
                    self._show_message(f"No results for: {search_term}", "info")
        except (KeyboardInterrupt, EOFError):
            pass

    def _show_search_results(self, results: List[FileInfo], search_term: str) -> None:
        """Show search results.

        Args:
            results: List of matching files
            search_term: The search term used
        """
        self.console.clear()
        self.console.print(f"\n[bold]Search Results:[/bold] {search_term} ({len(results)} found)\n")

        table = RichTable(show_header=True, header_style="bold magenta")
        table.add_column("Name", style="cyan")
        table.add_column("Path", style="dim")
        table.add_column("Size", style="green")
        table.add_column("Modified", style="yellow")

        for file_info in results[:50]:  # Show max 50 results
            table.add_row(
                file_info.name,
                file_info.path,
                self.explorer._format_size(file_info.size),
                file_info.modified
            )

        self.console.print(table)
        self.console.print("\n[dim]Press any key to continue...[/dim]")
        readkey()

    def _show_message(self, message: str, msg_type: str = "info") -> None:
        """Show a temporary message.

        Args:
            message: Message to display
            msg_type: Type of message (info, warning, error)
        """
        colors = {
            "info": "blue",
            "warning": "yellow",
            "error": "red"
        }
        color = colors.get(msg_type, "white")

        # Render current screen with message overlay
        self._render()
        self.console.print(f"\n[{color}]{message}[/{color}]")
        self.console.print("[dim]Press any key to continue...[/dim]")
        readkey()

    def _convert_to_rich_format(self, text: str) -> str:
        """Convert plain text to Rich markup.

        Args:
            text: Plain text to convert

        Returns:
            Text with Rich markup
        """
        # Simple conversion - add some basic styling
        lines = text.split('\n')
        rich_lines = []

        for line in lines:
            if line.startswith('='):
                # Headers
                rich_lines.append(f"[bold cyan]{line}[/bold cyan]")
            elif line.startswith('-'):
                # Separators
                rich_lines.append(f"[dim]{line}[/dim]")
            elif 'YES' in line:
                rich_lines.append(line.replace('YES', '[green]YES[/green]').replace('NO', '[red]NO[/red]'))
            else:
                rich_lines.append(line)

        return '\n'.join(rich_lines)

    def _render(self) -> None:
        """Render the file explorer UI."""
        self.console.clear()

        # Header
        current_rel_path = self.explorer.get_current_path().relative_to(self.explorer.project_root)
        header_text = Text.assemble(
            ("FILE EXPLORER", "bold blue"),
            (" - ", "dim"),
            (str(current_rel_path), "cyan"),
        )
        header = Panel(
            header_text,
            style="blue",
            padding=(0, 1)
        )
        self.console.print(header)

        # File table
        table = RichTable(show_header=True, header_style="bold magenta")
        table.add_column("", width=3)  # Selection indicator
        table.add_column("Name", style="cyan")
        table.add_column("Type", width=8, justify="center")
        table.add_column("Size", width=10, justify="right")
        table.add_column("Modified", width=16)
        table.add_column("Status", width=15)

        # Calculate visible range
        visible_start = self.scroll_offset
        visible_end = min(len(self.files), visible_start + self.max_visible)

        # Add rows
        for i in range(visible_start, visible_end):
            file_info = self.files[i]
            is_selected = (i == self.selected_index)

            # Selection indicator
            if is_selected:
                indicator = Text("►", style="bold yellow")
                row_style = Style(bgcolor="yellow", color="black")
            else:
                indicator = Text(" ")
                row_style = None

            # File name styling
            if file_info.is_dir:
                name_style = "bold blue"
            else:
                name_style = "cyan"

            # Determine type
            if file_info.is_dir:
                file_type = Text("DIR", style="bold blue")
                size_str = Text("-")
            else:
                file_type = Text(file_info.extensions[0] if file_info.extensions else "FILE", style="dim")
                size_str = Text(self.explorer._format_size(file_info.size), style="green")

            # Get status indicators
            status_parts = []
            if not file_info.is_dir:
                dep_info = self.explorer.get_dependency_info(file_info.path)
                if dep_info.is_orphan:
                    status_parts.append(("ORPHAN", "bold red"))
                elif dep_info.in_cycle:
                    status_parts.append(("CYCLE", "bold yellow"))
                if not dep_info.inbound and not dep_info.is_orphan:
                    status_parts.append(("NO-REFS", "dim"))

            status_text = Text()
            for i, (text, style) in enumerate(status_parts):
                if i > 0:
                    status_text.append(", ", style="dim")
                status_text.append(text, style=style)

            if not status_parts:
                status_text = Text("-", style="dim")

            # Add row
            name = Text(file_info.name, style=name_style)
            modified = Text(file_info.modified, style="yellow")

            if row_style:
                table.add_row(
                    indicator,
                    name,
                    file_type,
                    size_str,
                    modified,
                    status_text,
                    style=row_style
                )
            else:
                table.add_row(
                    indicator,
                    name,
                    file_type,
                    size_str,
                    modified,
                    status_text
                )

        self.console.print(table)

        # Footer with info
        file_count = len(self.files)
        selected_text = f"Selected: {self.selected_index + 1}/{file_count}" if self.files else "No files"
        footer = Text.assemble(
            ("[h]elp  ", "dim"),
            ("[q]uit  ", "dim"),
            ("[/]search  ", "dim"),
            ("[Enter]open  ", "dim"),
            (f"  |  {selected_text}", "cyan"),
        )
        self.console.print(footer)
