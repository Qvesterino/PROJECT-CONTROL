"""Rich table formatting for terminal output."""

from __future__ import annotations

from typing import Any, List, Optional


class Table:
    """Rich table formatter with Unicode box-drawing characters."""

    # Box-drawing characters
    TOP_LEFT = "┌"
    TOP_RIGHT = "┐"
    BOTTOM_LEFT = "└"
    BOTTOM_RIGHT = "┘"
    HORIZONTAL = "─"
    VERTICAL = "│"
    TOP_TEE = "┬"
    BOTTOM_TEE = "┴"
    LEFT_TEE = "├"
    RIGHT_TEE = "┤"
    CROSS = "┼"

    def __init__(self, headers: List[str]):
        """Initialize table with headers.

        Args:
            headers: List of column headers
        """
        self.headers = headers
        self.rows: List[List[str]] = []
        self.column_widths: List[int] = [len(h) for h in headers]

    def add_row(self, row: List[Any]) -> None:
        """Add a row to the table.

        Args:
            row: List of values (will be converted to strings)
        """
        str_row = [str(cell) for cell in row]
        self.rows.append(str_row)

        # Update column widths
        for i, cell in enumerate(str_row):
            if i < len(self.column_widths):
                self.column_widths[i] = max(self.column_widths[i], len(cell))

    def render(self, title: Optional[str] = None, max_width: int = 120) -> str:
        """Render table as a string.

        Args:
            title: Optional title to display at the top
            max_width: Maximum width of the table (for responsive rendering)

        Returns:
            Rendered table as string
        """
        if not self.headers and not self.rows:
            return ""

        # Calculate actual column widths with max_width constraint
        total_min_width = sum(self.column_widths) + (len(self.column_widths) - 1) * 3
        if total_min_width > max_width:
            # Scale down columns proportionally
            scale = max_width / total_min_width
            self.column_widths = [max(1, int(w * scale)) for w in self.column_widths]

        lines: List[str] = []

        # Add title if provided
        if title:
            lines.append(f" {title} ")
            title_width = len(title) + 2
            line_width = sum(self.column_widths) + (len(self.column_widths) - 1) * 3
            if title_width < line_width:
                title_line = "─" * ((line_width - title_width) // 2)
                lines[0] = f"{title_line}{lines[0]}{title_line}"
            lines.append("")

        # Build separator line
        def build_separator(left: str, middle: str, right: str) -> str:
            parts = [left]
            for i, width in enumerate(self.column_widths):
                parts.append(self.HORIZONTAL * (width + 2))
                if i < len(self.column_widths) - 1:
                    parts.append(middle)
            parts.append(right)
            return "".join(parts)

        # Top border
        lines.append(build_separator(self.TOP_LEFT, self.TOP_TEE, self.TOP_RIGHT))

        # Header row
        header_cells = []
        for i, header in enumerate(self.headers):
            width = self.column_widths[i] if i < len(self.column_widths) else len(header)
            header_cells.append(f" {header.ljust(width)} ")
        lines.append(f"{self.VERTICAL}{''.join(header_cells)}{self.VERTICAL}")

        # Header separator
        lines.append(build_separator(self.LEFT_TEE, self.CROSS, self.RIGHT_TEE))

        # Data rows
        for row in self.rows:
            cells = []
            for i, cell in enumerate(row):
                width = self.column_widths[i] if i < len(self.column_widths) else len(cell)
                cells.append(f" {cell.ljust(width)} ")
            lines.append(f"{self.VERTICAL}{''.join(cells)}{self.VERTICAL}")

        # Bottom border
        lines.append(build_separator(self.BOTTOM_LEFT, self.BOTTOM_TEE, self.BOTTOM_RIGHT))

        return "\n".join(lines)

    def print(self, title: Optional[str] = None, max_width: int = 120) -> None:
        """Print table to stdout.

        Args:
            title: Optional title to display at the top
            max_width: Maximum width of the table
        """
        import sys
        try:
            # Try to print with UTF-8 encoding
            print(self.render(title, max_width))
        except UnicodeEncodeError:
            # Fallback to ASCII for Windows console
            text = self.render(title, max_width)
            if sys.platform == "win32":
                # Encode with 'replace' to replace problematic characters
                print(text.encode(sys.stdout.encoding, errors="replace").decode(sys.stdout.encoding))
            else:
                print(text.encode("ascii", errors="replace").decode("ascii"))


def create_table(headers: List[str], rows: List[List[Any]], title: Optional[str] = None) -> str:
    """Convenience function to create and render a table.

    Args:
        headers: List of column headers
        rows: List of rows (each row is a list of values)
        title: Optional title

    Returns:
        Rendered table as string
    """
    table = Table(headers)
    for row in rows:
        table.add_row(row)
    return table.render(title)


def print_table(headers: List[str], rows: List[List[Any]], title: Optional[str] = None) -> None:
    """Convenience function to create and print a table.

    Args:
        headers: List of column headers
        rows: List of rows (each row is a list of values)
        title: Optional title
    """
    table = Table(headers)
    for row in rows:
        table.add_row(row)
    table.print(title)
