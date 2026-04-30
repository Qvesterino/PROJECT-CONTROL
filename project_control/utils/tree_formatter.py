"""ASCII tree formatter for file listings - like Windows tree command."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Tuple


class TreeFormatter:
    """Formats a list of file paths into an ASCII tree structure."""
    
    def __init__(self, root_label: str = "."):
        """Initialize tree formatter.
        
        Args:
            root_label: Label for the root directory (default: ".")
        """
        self.root_label = root_label
    
    def format(self, file_paths: List[str], show_counts: bool = False) -> str:
        """Format file paths into ASCII tree.
        
        Args:
            file_paths: List of file paths (as strings, using forward slashes)
            show_counts: If True, show counts of items in each directory
            
        Returns:
            ASCII tree formatted string
        """
        if not file_paths:
            return f"{self.root_label}\n    (empty)"
        
        # Build tree structure
        tree = self._build_tree(file_paths)
        
        # Render tree
        lines = [self.root_label]
        self._render_tree(tree, lines, prefix="", show_counts=show_counts)
        
        return "\n".join(lines)
    
    def _build_tree(self, file_paths: List[str]) -> Dict[str, Dict]:
        """Build nested directory structure from file paths.
        
        Args:
            file_paths: List of file paths
            
        Returns:
            Nested dictionary representing directory tree
        """
        tree: Dict[str, Dict] = {}
        
        for path in file_paths:
            # Normalize path: ensure forward slashes, split by /
            normalized = path.replace("\\", "/").strip("/")
            parts = normalized.split("/")
            
            current = tree
            for i, part in enumerate(parts):
                is_file = (i == len(parts) - 1)
                
                if part not in current:
                    current[part] = {} if not is_file else None
                
                if not is_file:
                    current = current[part]  # type: ignore
        
        return tree
    
    def _render_tree(
        self, 
        tree: Dict[str, Dict], 
        lines: List[str], 
        prefix: str, 
        show_counts: bool
    ) -> None:
        """Recursively render tree structure.
        
        Args:
            tree: Nested dictionary to render
            lines: List to append rendered lines to
            prefix: Prefix for current level (indentation and connectors)
            show_counts: If True, show counts of items in each directory
        """
        items = sorted(tree.keys())
        
        for i, item in enumerate(items):
            is_last = (i == len(items) - 1)
            value = tree[item]
            is_directory = value is not None
            
            # Choose connector
            connector = "\\---" if is_last else "+---"
            child_prefix = "    " if is_last else "|   "
            
            # Format current line
            line = f"{prefix}{connector} {item}"
            
            # Add counts if directory and requested
            if is_directory and show_counts:
                count = self._count_items(value)
                line += f" ({count} items)"
            
            lines.append(line)
            
            # Recurse into directories
            if is_directory:
                self._render_tree(value, lines, prefix + child_prefix, show_counts)
    
    def _count_items(self, subtree: Dict[str, Dict]) -> int:
        """Count total items (files + directories) in subtree."""
        count = 0
        for key, value in subtree.items():
            count += 1
            if value is not None:  # Is directory
                count += self._count_items(value)
        return count


def format_file_tree(
    file_paths: List[str],
    root_label: str = ".",
    show_counts: bool = False
) -> str:
    """Convenience function to format file paths as ASCII tree.
    
    Args:
        file_paths: List of file paths (as strings, using forward slashes)
        root_label: Label for the root directory (default: ".")
        show_counts: If True, show counts of items in each directory
        
    Returns:
        ASCII tree formatted string
        
    Example:
        >>> files = ["src/utils.py", "src/main.py", "tests/test_utils.py"]
        >>> print(format_file_tree(files))
        .
        +--- src
        |   |--- main.py
        |   \\--- utils.py
        \\--- tests
            \\--- test_utils.py
    """
    formatter = TreeFormatter(root_label=root_label)
    return formatter.format(file_paths, show_counts=show_counts)