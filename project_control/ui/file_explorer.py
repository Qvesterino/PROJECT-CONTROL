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
