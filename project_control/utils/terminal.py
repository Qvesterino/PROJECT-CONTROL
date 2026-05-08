"""Color terminal output utilities for PROJECT_CONTROL.

Cross-platform color support with graceful fallback for terminals
that don't support ANSI escape codes.

Violet/purple aesthetic theme for a professional, modern look.
"""

from __future__ import annotations

import sys

from project_control.utils.progress import ANSI


# ── Violet Color Palette ─────────────────────────────────────────────────

class Violet:
    """Violet color palette for the PROJECT_CONTROL design system.

    Four violet shades + white = clean, minimal, readable aesthetic.
    """

    # Core violet palette
    DEEP = "\033[38;2;15;6;26m" if ANSI.supports_ansi() else ""       # #0F061A
    DARK = "\033[38;2;28;10;46m" if ANSI.supports_ansi() else ""      # #1C0A2E
    MEDIUM = "\033[38;2;46;21;84m" if ANSI.supports_ansi() else ""    # #2E1554
    SURFACE = "\033[38;2;61;31;110m" if ANSI.supports_ansi() else ""  # #3D1F6E
    ACCENT = "\033[38;2;124;58;237m" if ANSI.supports_ansi() else ""  # #7C3AED
    BRIGHT = "\033[38;2;168;85;247m" if ANSI.supports_ansi() else ""  # #A855F7
    LIGHT = "\033[38;2;192;132;252m" if ANSI.supports_ansi() else ""  # #C084FC
    MUTED = "\033[38;2;109;40;217m" if ANSI.supports_ansi() else ""   # #6D28D9

    # Background variants
    BG_DEEP = "\033[48;2;15;6;26m" if ANSI.supports_ansi() else ""
    BG_DARK = "\033[48;2;28;10;46m" if ANSI.supports_ansi() else ""
    BG_MEDIUM = "\033[48;2;46;21;84m" if ANSI.supports_ansi() else ""
    BG_ACCENT = "\033[48;2;124;58;237m" if ANSI.supports_ansi() else ""

    # White variants
    WHITE = "\033[38;2;255;255;255m" if ANSI.supports_ansi() else ""
    WHITE_SOFT = "\033[38;2;245;240;255m" if ANSI.supports_ansi() else ""  # #F5F0FF
    TEXT = "\033[38;2;248;244;255m" if ANSI.supports_ansi() else ""        # #F8F4FF
    TEXT_SOFT = "\033[38;2;212;197;249m" if ANSI.supports_ansi() else ""   # #D4C5F9
    TEXT_MUTED = "\033[38;2;154;132;201m" if ANSI.supports_ansi() else ""  # #9A84C9


# ── Color Constants (keep for backwards compatibility) ──────────────────

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

    # Violet palette (convenience access)
    VIOLET_DEEP = Violet.DEEP
    VIOLET_DARK = Violet.DARK
    VIOLET_MEDIUM = Violet.MEDIUM
    VIOLET_SURFACE = Violet.SURFACE
    VIOLET_ACCENT = Violet.ACCENT
    VIOLET_BRIGHT = Violet.BRIGHT
    VIOLET_LIGHT = Violet.LIGHT
    VIOLET_MUTED = Violet.MUTED
    WHITE_SOFT = Violet.WHITE_SOFT
    TEXT_SOFT = Violet.TEXT_SOFT
    TEXT_MUTED = Violet.TEXT_MUTED


# ── Styled Print Functions ───────────────────────────────────────────────

def print_success(msg: str, prefix: str = "OK") -> None:
    print(f"{Colors.GREEN}[{prefix}]{Colors.RESET} {msg}")


def print_warning(msg: str, prefix: str = "WARN") -> None:
    print(f"{Colors.YELLOW}[{prefix}]{Colors.RESET} {msg}")


def print_error(msg: str, prefix: str = "ERROR") -> None:
    print(f"{Colors.RED}[{prefix}]{Colors.RESET} {msg}", file=sys.stderr)


def print_info(msg: str, prefix: str = "INFO") -> None:
    print(f"{Violet.BRIGHT}◇{Colors.RESET} {Colors.BOLD}{msg}{Colors.RESET}")


def print_debug(msg: str, prefix: str = "DEBUG") -> None:
    print(f"{Colors.DIM}{Colors.BLACK}[{prefix}]{Colors.RESET} {msg}")


def print_step(msg: str, prefix: str = "▸") -> None:
    print(f"  {Violet.LIGHT}{prefix}{Colors.RESET} {msg}")


def print_header(msg: str, width: int = 60) -> None:
    line = Violet.MUTED + "━" * width + Colors.RESET
    print()
    print(line)
    print(f"  {Violet.BRIGHT}{Colors.BOLD}{msg}{Colors.RESET}")
    print(line)
    print()


def print_section(msg: str, char: str = "─", width: int = 60) -> None:
    divider = Violet.TEXT_MUTED + char * width + Colors.RESET
    print()
    print(divider)
    print(f"  {Violet.LIGHT}{msg}{Colors.RESET}")
    print(divider)
    print()


def print_divider(char: str = "─", width: int = 60) -> None:
    print(Violet.TEXT_MUTED + char * width + Colors.RESET)


def print_label(label: str, value: str) -> None:
    print(f"  {Violet.LIGHT}{label}:{Colors.RESET} {value}")


def print_badge(text: str) -> None:
    print(f"  {Violet.WHITE_SOFT}{Violet.BG_ACCENT} {text} {Colors.RESET}")


def print_table(headers: list[str], rows: list[list[str]]) -> None:
    if not headers or not rows:
        return

    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))

    header_row = " │ ".join(
        f"{Colors.BOLD}{Violet.BRIGHT}{str(headers[i]).ljust(col_widths[i])}{Colors.RESET}"
        for i in range(len(headers))
    )
    divider = Violet.TEXT_MUTED + "─" + "─┼─".join("─" * w for w in col_widths) + Colors.RESET + Violet.TEXT_MUTED + "─" + Colors.RESET

    print(f"  {Violet.MUTED}┌{'─' * (sum(col_widths) + 3 * (len(col_widths) - 1) + 2)}┐{Colors.RESET}")
    print(f"  {Violet.MUTED}│{Colors.RESET} {header_row} {Violet.MUTED}│{Colors.RESET}")
    print(f"  {Violet.MUTED}│{Colors.RESET}{divider}{Violet.MUTED}│{Colors.RESET}")

    for row in rows:
        cells = []
        for i, cell in enumerate(row):
            if i < len(col_widths):
                cells.append(str(cell).ljust(col_widths[i]))
        print(f"  {Violet.MUTED}│{Colors.RESET} {' │ '.join(cells)} {Violet.MUTED}│{Colors.RESET}")

    print(f"  {Violet.MUTED}└{'─' * (sum(col_widths) + 3 * (len(col_widths) - 1) + 2)}┘{Colors.RESET}")


def print_menu_item(key: str, label: str, description: str = "") -> None:
    desc = f" {Violet.TEXT_MUTED}{description}{Colors.RESET}" if description else ""
    print(f"  {Violet.BRIGHT}{key}{Colors.RESET}  {label}{desc}")


def print_quick_action(key: str, label: str, description: str) -> None:
    print(f"  {Violet.ACCENT}{key}{Colors.RESET}  {Colors.BOLD}{label}{Colors.RESET}")
    print(f"     {Violet.TEXT_MUTED}{description}{Colors.RESET}")


# ── Status Indicators ───────────────────────────────────────────────────

class Status:
    """Status indicator with color."""

    OK = f"{Colors.GREEN}OK{Colors.RESET}"
    FAIL = f"{Colors.RED}FAIL{Colors.RESET}"
    WARN = f"{Colors.YELLOW}WARN{Colors.RESET}"
    INFO = f"{Violet.BRIGHT}INFO{Colors.RESET}"
    SKIP = f"{Colors.DIM}SKIP{Colors.RESET}"

    @staticmethod
    def ok(msg: str = "OK") -> str:
        return f"{Colors.GREEN}[{msg}]{Colors.RESET}"

    @staticmethod
    def fail(msg: str = "FAIL") -> str:
        return f"{Colors.RED}[{msg}]{Colors.RESET}"

    @staticmethod
    def warn(msg: str = "WARN") -> str:
        return f"{Colors.YELLOW}[{msg}]{Colors.RESET}"

    @staticmethod
    def info(msg: str = "INFO") -> str:
        return f"{Violet.BRIGHT}[{msg}]{Colors.RESET}"


# ── Helper Functions ───────────────────────────────────────────────────

def colorize(text: str, color: str, bold: bool = False) -> str:
    if bold:
        return f"{Colors.BOLD}{color}{text}{Colors.RESET}"
    return f"{color}{text}{Colors.RESET}"


def strip_ansi(text: str) -> str:
    import re
    ansi_escape = re.compile(r'\033\[[0-9;]*m')
    return ansi_escape.sub('', text)


# ── Context Managers ───────────────────────────────────────────────────

class ColorOutput:
    """
    Context manager that temporarily disables color output.
    """

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self.original_support = None

    def __enter__(self):
        self.original_support = ANSI.supports_ansi
        if not self.enabled:
            ANSI.supports_ansi = lambda: False
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.original_support:
            ANSI.supports_ansi = self.original_support
        return False
