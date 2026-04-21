"""Color terminal output utilities for PROJECT_CONTROL.

Cross-platform color support with graceful fallback for terminals
that don't support ANSI escape codes.
"""

from __future__ import annotations

import sys

# Import ANSI support from progress.py
from project_control.utils.progress import ANSI


# ── Color Constants ─────────────────────────────────────────────────────

class Colors:
    """
    ANSI color codes for terminal output.

    All colors are disabled automatically on terminals that don't support ANSI.
    """

    # Basic colors
    BLACK = "\033[30m" if ANSI.supports_ansi() else ""
    RED = "\033[31m" if ANSI.supports_ansi() else ""
    GREEN = "\033[32m" if ANSI.supports_ansi() else ""
    YELLOW = "\033[33m" if ANSI.supports_ansi() else ""
    BLUE = "\033[34m" if ANSI.supports_ansi() else ""
    MAGENTA = "\033[35m" if ANSI.supports_ansi() else ""
    CYAN = "\033[36m" if ANSI.supports_ansi() else ""
    WHITE = "\033[37m" if ANSI.supports_ansi() else ""

    # Bright colors (high intensity)
    BRIGHT_BLACK = "\033[90m" if ANSI.supports_ansi() else ""
    BRIGHT_RED = "\033[91m" if ANSI.supports_ansi() else ""
    BRIGHT_GREEN = "\033[92m" if ANSI.supports_ansi() else ""
    BRIGHT_YELLOW = "\033[93m" if ANSI.supports_ansi() else ""
    BRIGHT_BLUE = "\033[94m" if ANSI.supports_ansi() else ""
    BRIGHT_MAGENTA = "\033[95m" if ANSI.supports_ansi() else ""
    BRIGHT_CYAN = "\033[96m" if ANSI.supports_ansi() else ""
    BRIGHT_WHITE = "\033[97m" if ANSI.supports_ansi() else ""

    # Background colors
    BG_BLACK = "\033[40m" if ANSI.supports_ansi() else ""
    BG_RED = "\033[41m" if ANSI.supports_ansi() else ""
    BG_GREEN = "\033[42m" if ANSI.supports_ansi() else ""
    BG_YELLOW = "\033[43m" if ANSI.supports_ansi() else ""
    BG_BLUE = "\033[44m" if ANSI.supports_ansi() else ""
    BG_MAGENTA = "\033[45m" if ANSI.supports_ansi() else ""
    BG_CYAN = "\033[46m" if ANSI.supports_ansi() else ""
    BG_WHITE = "\033[47m" if ANSI.supports_ansi() else ""

    # Text styles
    BOLD = "\033[1m" if ANSI.supports_ansi() else ""
    DIM = "\033[2m" if ANSI.supports_ansi() else ""
    ITALIC = "\033[3m" if ANSI.supports_ansi() else ""
    UNDERLINE = "\033[4m" if ANSI.supports_ansi() else ""
    BLINK = "\033[5m" if ANSI.supports_ansi() else ""
    REVERSE = "\033[7m" if ANSI.supports_ansi() else ""
    STRIKETHROUGH = "\033[9m" if ANSI.supports_ansi() else ""

    # Reset
    RESET = "\033[0m" if ANSI.supports_ansi() else ""


# ── Styled Print Functions ───────────────────────────────────────────────

def print_success(msg: str, prefix: str = "OK") -> None:
    """
    Print a success message in green.

    Args:
        msg: Message to print
        prefix: Prefix before message (default: "OK")
    """
    print(f"{Colors.GREEN}[{prefix}]{Colors.RESET} {msg}")


def print_warning(msg: str, prefix: str = "WARN") -> None:
    """
    Print a warning message in yellow.

    Args:
        msg: Message to print
        prefix: Prefix before message (default: "WARN")
    """
    print(f"{Colors.YELLOW}[{prefix}]{Colors.RESET} {msg}")


def print_error(msg: str, prefix: str = "ERROR") -> None:
    """
    Print an error message in red.

    Args:
        msg: Message to print
        prefix: Prefix before message (default: "ERROR")
    """
    print(f"{Colors.RED}[{prefix}]{Colors.RESET} {msg}", file=sys.stderr)


def print_info(msg: str, prefix: str = "INFO") -> None:
    """
    Print an info message in cyan.

    Args:
        msg: Message to print
        prefix: Prefix before message (default: "INFO")
    """
    print(f"{Colors.CYAN}[{prefix}]{Colors.RESET} {msg}")


def print_debug(msg: str, prefix: str = "DEBUG") -> None:
    """
    Print a debug message in dim gray.

    Args:
        msg: Message to print
        prefix: Prefix before message (default: "DEBUG")
    """
    print(f"{Colors.DIM}{Colors.BLACK}[{prefix}]{Colors.RESET} {msg}")


def print_header(msg: str, width: int = 60) -> None:
    """
    Print a header with message centered in a line.

    Args:
        msg: Header message
        width: Total width of header line
    """
    line = "=" * width
    print(f"{Colors.CYAN}{line}{Colors.RESET}")
    print(f"{Colors.CYAN}  {msg}{Colors.RESET}")
    print(f"{Colors.CYAN}{line}{Colors.RESET}")


def print_section(msg: str, char: str = "-", width: int = 60) -> None:
    """
    Print a section divider with message.

    Args:
        msg: Section message
        char: Character to use for divider (default: "-")
        width: Total width of section line
    """
    divider = char * width
    print(f"\n{Colors.CYAN}{divider}{Colors.RESET}")
    print(f"{Colors.CYAN}{msg}{Colors.RESET}")
    print(f"{Colors.CYAN}{divider}{Colors.RESET}\n")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    """
    Print a simple formatted table.

    Args:
        headers: List of column headers
        rows: List of rows, each a list of string values
    """
    if not headers or not rows:
        return

    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    # Print header
    header_row = " | ".join(
        f"{Colors.BOLD}{Colors.CYAN}{str(headers[i]).ljust(col_widths[i])}{Colors.RESET}"
        for i in range(len(headers))
    )
    divider = "-+-".join("-" * w for w in col_widths)

    print(f"{Colors.BOLD}{Colors.CYAN}{header_row}{Colors.RESET}")
    print(f"{Colors.CYAN}{divider}{Colors.RESET}")

    # Print rows
    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cells.append(str(cell).ljust(col_widths[i]))
        print(" | ".join(cells))


# ── Status Indicators ───────────────────────────────────────────────────

class Status:
    """Status indicator with color."""

    OK = f"{Colors.GREEN}OK{Colors.RESET}"
    FAIL = f"{Colors.RED}FAIL{Colors.RESET}"
    WARN = f"{Colors.YELLOW}WARN{Colors.RESET}"
    INFO = f"{Colors.CYAN}INFO{Colors.RESET}"
    SKIP = f"{Colors.DIM}SKIP{Colors.RESET}"

    @staticmethod
    def ok(msg: str = "OK") -> str:
        """Return OK status with custom message."""
        return f"{Colors.GREEN}[{msg}]{Colors.RESET}"

    @staticmethod
    def fail(msg: str = "FAIL") -> str:
        """Return FAIL status with custom message."""
        return f"{Colors.RED}[{msg}]{Colors.RESET}"

    @staticmethod
    def warn(msg: str = "WARN") -> str:
        """Return WARN status with custom message."""
        return f"{Colors.YELLOW}[{msg}]{Colors.RESET}"

    @staticmethod
    def info(msg: str = "INFO") -> str:
        """Return INFO status with custom message."""
        return f"{Colors.CYAN}[{msg}]{Colors.RESET}"


# ── Helper Functions ───────────────────────────────────────────────────

def colorize(text: str, color: str, bold: bool = False) -> str:
    """
    Wrap text in ANSI color codes.

    Args:
        text: Text to colorize
        color: Color code from Colors class
        bold: Whether to make text bold

    Returns:
        Colorized text
    """
    if bold:
        return f"{Colors.BOLD}{color}{text}{Colors.RESET}"
    return f"{color}{text}{Colors.RESET}"


def strip_ansi(text: str) -> str:
    """
    Remove ANSI escape codes from text.

    Args:
        text: Text that may contain ANSI codes

    Returns:
        Text without ANSI codes
    """
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    return ansi_escape.sub('', text)


# ── Context Managers ───────────────────────────────────────────────────

class ColorOutput:
    """
    Context manager that temporarily disables color output.

    Useful for testing or when writing to files.

    Usage:
        with ColorOutput(enabled=False):
            print_success("This won't be colored")
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.original_support = None

    def __enter__(self):
        self.original_support = ANSI.supports_ansi
        # Temporarily override supports_ansi
        if not self.enabled:
            ANSI.supports_ansi = lambda: False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Restore original support check
        if self.original_support:
            ANSI.supports_ansi = self.original_support
        return False
