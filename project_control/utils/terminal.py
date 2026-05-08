"""Color terminal output utilities for PROJECT_CONTROL.

Cross-platform color support with graceful fallback for terminals
that don't support ANSI escape codes.

Violet/purple aesthetic theme — premium, AAA-grade design system.
Deep chromatic palette with refined hierarchy and typographic precision.
"""

from __future__ import annotations

import sys

from project_control.utils.progress import ANSI


# ── Violet Color Palette ─────────────────────────────────────────────────

class Violet:
    """Violet color palette for the PROJECT_CONTROL design system.

    Full chromatic spectrum from deep void to luminous frost.
    Organized by visual weight: void → deep → dark → mid → accent → glow.
    """

    # ── Void & Deep (backgrounds, borders) ──
    VOID = "\033[38;2;8;3;16m" if ANSI.supports_ansi() else ""         # #080310
    DEEP = "\033[38;2;15;6;26m" if ANSI.supports_ansi() else ""        # #0F061A
    DARK = "\033[38;2;28;10;46m" if ANSI.supports_ansi() else ""       # #1C0A2E
    MIDNIGHT = "\033[38;2;38;14;64m" if ANSI.supports_ansi() else ""   # #260E40

    # ── Core palette (content, UI) ──
    MEDIUM = "\033[38;2;46;21;84m" if ANSI.supports_ansi() else ""     # #2E1554
    SURFACE = "\033[38;2;61;31;110m" if ANSI.supports_ansi() else ""   # #3D1F6E
    ELEVATED = "\033[38;2;88;28;135m" if ANSI.supports_ansi() else ""  # #581C87
    MUTED = "\033[38;2;109;40;217m" if ANSI.supports_ansi() else ""    # #6D28D9

    # ── Accent & Highlights ──
    ACCENT = "\033[38;2;124;58;237m" if ANSI.supports_ansi() else ""   # #7C3AED
    BRIGHT = "\033[38;2;168;85;247m" if ANSI.supports_ansi() else ""    # #A855F7
    LIGHT = "\033[38;2;192;132;252m" if ANSI.supports_ansi() else ""   # #C084FC
    GLOW = "\033[38;2;216;180;254m" if ANSI.supports_ansi() else ""    # #D8B4FE
    FROST = "\033[38;2;237;233;254m" if ANSI.supports_ansi() else ""   # #EDE9FE

    # ── Background variants ──
    BG_VOID = "\033[48;2;8;3;16m" if ANSI.supports_ansi() else ""
    BG_DEEP = "\033[48;2;15;6;26m" if ANSI.supports_ansi() else ""
    BG_DARK = "\033[48;2;28;10;46m" if ANSI.supports_ansi() else ""
    BG_MEDIUM = "\033[48;2;46;21;84m" if ANSI.supports_ansi() else ""
    BG_ACCENT = "\033[48;2;124;58;237m" if ANSI.supports_ansi() else ""
    BG_BRIGHT = "\033[48;2;168;85;247m" if ANSI.supports_ansi() else ""

    # ── White variants (text hierarchy) ──
    WHITE = "\033[38;2;255;255;255m" if ANSI.supports_ansi() else ""
    WHITE_SOFT = "\033[38;2;245;240;255m" if ANSI.supports_ansi() else ""  # #F5F0FF
    TEXT = "\033[38;2;248;244;255m" if ANSI.supports_ansi() else ""        # #F8F4FF
    TEXT_SOFT = "\033[38;2;212;197;249m" if ANSI.supports_ansi() else ""   # #D4C5F9
    TEXT_MUTED = "\033[38;2;154;132;201m" if ANSI.supports_ansi() else ""   # #9A84C9


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
    VIOLET_VOID = Violet.VOID
    VIOLET_DEEP = Violet.DEEP
    VIOLET_DARK = Violet.DARK
    VIOLET_MIDNIGHT = Violet.MIDNIGHT
    VIOLET_MEDIUM = Violet.MEDIUM
    VIOLET_SURFACE = Violet.SURFACE
    VIOLET_ELEVATED = Violet.ELEVATED
    VIOLET_ACCENT = Violet.ACCENT
    VIOLET_BRIGHT = Violet.BRIGHT
    VIOLET_LIGHT = Violet.LIGHT
    VIOLET_MUTED = Violet.MUTED
    VIOLET_GLOW = Violet.GLOW
    VIOLET_FROST = Violet.FROST
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


# ── Premium Display Functions ────────────────────────────────────────────

def print_brand_header(title: str, subtitle: str = "", width: int = 54) -> None:
    """Print a premium brand header with refined box and gradient border."""
    w = width
    print()
    print(f"  {Violet.ELEVATED}╔{'═' * w}╗{Colors.RESET}")
    print(f"  {Violet.ELEVATED}║{Colors.RESET}  {Violet.FROST}{Colors.BOLD}{title}{Colors.RESET}{' ' * (w - len(title) - 2)}{Violet.ELEVATED}║{Colors.RESET}")
    if subtitle:
        print(f"  {Violet.ELEVATED}║{Colors.RESET}  {Violet.TEXT_MUTED}{subtitle}{Colors.RESET}{' ' * (w - len(subtitle) - 2)}{Violet.ELEVATED}║{Colors.RESET}")
    print(f"  {Violet.ELEVATED}╚{'═' * w}╝{Colors.RESET}")
    print()


def print_submenu_header(title: str, width: int = 50) -> None:
    """Print a refined submenu header with elevated borders."""
    w = width
    print()
    print(f"  {Violet.SURFACE}╭{'─' * w}╮{Colors.RESET}")
    print(f"  {Violet.SURFACE}│{Colors.RESET}  {Violet.BRIGHT}{Colors.BOLD}{title}{Colors.RESET}{' ' * (w - len(title) - 2)}{Violet.SURFACE}│{Colors.RESET}")
    print(f"  {Violet.SURFACE}╰{'─' * w}╯{Colors.RESET}")
    print()


def print_metric(label: str, value: str, status: str = "") -> None:
    """Print a key-value metric with optional status indicator."""
    status_str = ""
    if status == "ok":
        status_str = f" {Colors.GREEN}●{Colors.RESET}"
    elif status == "warn":
        status_str = f" {Colors.YELLOW}●{Colors.RESET}"
    elif status == "error":
        status_str = f" {Colors.RED}●{Colors.RESET}"
    print(f"  {Violet.TEXT_MUTED}{label:.<28}{Colors.RESET} {Violet.TEXT}{value}{Colors.RESET}{status_str}")


def print_status_line(label: str, value: str, width: int = 54) -> None:
    """Print a status line with dotted leader alignment."""
    leader_width = width - len(label) - len(value) - 4
    if leader_width < 3:
        leader_width = 3
    leader = "·" * leader_width
    print(f"  {Violet.TEXT_MUTED}{label}{Colors.RESET} {Violet.MIDNIGHT}{leader}{Colors.RESET} {value}")


def print_key_value(key: str, value: str, key_width: int = 14) -> None:
    """Print a uniformly aligned key-value pair."""
    padded = key.ljust(key_width)
    print(f"  {Violet.LIGHT}{padded}{Colors.RESET} {value}")


def print_notification(msg: str, level: str = "info") -> None:
    """Print a notification with contextual icon."""
    icons = {"info": "⊙", "warn": "⚡", "error": "✕", "success": "✓"}
    icon = icons.get(level, "⊙")
    level_colors = {"info": Violet.TEXT_SOFT, "warn": Colors.YELLOW, "error": Colors.RED, "success": Colors.GREEN}
    color = level_colors.get(level, Violet.TEXT_SOFT)
    print(f"  {color}{icon}{Colors.RESET} {Violet.TEXT_SOFT}{msg}{Colors.RESET}")


def print_progress_step(step: int, total: int, msg: str) -> None:
    """Print a numbered progress step with refined formatting."""
    step_color = Violet.ACCENT if step < total else Colors.GREEN
    print(f"  {step_color}{step}/{total}{Colors.RESET} {Violet.TEXT}{msg}{Colors.RESET}")


# ── ASCII Art Logo ─────────────────────────────────────────────────────

PC_LOGO = r"""
                                                             
                                                             
   ██████╗ ██████╗ ███████╗   ██████╗██████╗ ███████╗██████╗ 
  ██╔════╝██╔═══██╗██╔════╝  ██╔════╝██╔══██╗██╔════╝██╔══██╗
  ██║     ██║   ██║█████╗    ██║     ██████╔╝█████╗  ██║  ██║
  ██║     ██║   ██║██╔══╝    ██║     ██╔══██╗██╔══╝  ██║  ██║
  ╚██████╗╚██████╔╝███████╗  ╚██████╗██║  ██║███████╗██████╔╝
   ╚═════╝ ╚═════╝ ╚══════╝   ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ 
                                                             
"""

PC_LOGOCompact = [
    " ██████╗██████╗ ███████╗██████╗ ",
    "██╔════╝██╔══██╗██╔════╝██╔══██╗",
    "██║     ██████╔╝█████╗  ██║  ██║",
    "██║     ██╔══██╗██╔══╝  ██║  ██║",
    "╚██████╗██║  ██║███████╗██████╔╝",
    " ╚═════╝╚═╝  ╚═╝╚══════╝╚═════╝ ",
]


def print_pc_splash(width: int = 54) -> None:
    """Print the PROJECT CONTROL branded splash screen."""
    print()
    for line in PC_LOGOCompact:
        padding = max(0, (width - len(strip_ansi(line))) // 2)
        print(f"{' ' * padding}{Violet.BRIGHT}{Colors.BOLD}{line}{Colors.RESET}")
    print()
    print(f"  {Violet.TEXT_MUTED}{'━' * width}{Colors.RESET}")
    tagline = "Architectural Analysis Engine"
    tag_padding = max(0, (width - len(tagline)) // 2)
    print(f"{' ' * tag_padding}{Violet.GLOW}{tagline}{Colors.RESET}")
    print()


def print_pc_splash_compact(width: int = 54) -> None:
    """Print a compact branded header (for menus that redraw often)."""
    print()
    print(f"  {Violet.ELEVATED}╔{'═' * width}╗{Colors.RESET}")
    title_line = f"  {Violet.FROST}{Colors.BOLD}PROJECT CONTROL{Colors.RESET}"
    tag = f"{Violet.GLOW} // Architectural Analysis{Colors.RESET}"
    content = f"  {Violet.ELEVATED}║{Colors.RESET}{title_line}{tag}{' ' * (width - 46)}{Violet.ELEVATED}║{Colors.RESET}"
    print(content)
    print(f"  {Violet.ELEVATED}╚{'═' * width}╝{Colors.RESET}")
    print()


def print_status_bar(entries: list[tuple[str, str, str]], width: int = 58) -> None:
    """Print a compact status bar with dot-separated entries.

    Args:
        entries: List of (label, value, status_color) tuples
        width: Total bar width
    """
    parts = []
    for label, value, status_color in entries:
        parts.append(f"{Violet.TEXT_MUTED}{label}{Colors.RESET} {status_color}{value}{Colors.RESET}")
    bar = f" {Violet.MIDNIGHT}·{Colors.RESET} ".join(parts)
    print(f"  {bar}")
    print(f"  {Violet.MIDNIGHT}{'─' * width}{Colors.RESET}")


def print_action_grid(actions: list[tuple[str, str, str]], cols: int = 2, width: int = 56) -> None:
    """Print actions in a grid layout with keys highlighted.

    Args:
        actions: List of (key, label, description) tuples
        cols: Number of columns
        width: Total width
    """
    col_width = width // cols
    row_entries = []
    for i, (key, label, desc) in enumerate(actions):
        entry = f"{Violet.ACCENT}{key}{Colors.RESET} {Violet.TEXT}{label}{Colors.RESET}"
        if desc:
            remaining = col_width - len(key) - len(label) - 3
            if remaining > 10:
                entry += f" {Violet.TEXT_MUTED}{desc[:remaining]}{Colors.RESET}"
        row_entries.append(entry)
        if len(row_entries) == cols or i == len(actions) - 1:
            while len(row_entries) < cols:
                row_entries.append("")
            print(f"  {' ' * (col_width + 1) * 0}{row_entries[0]}")
            if cols > 1 and len(row_entries) > 1:
                print(f"  {row_entries[1] if len(row_entries) > 1 else ''}")
            row_entries = []


def print_separator(style: str = "thin", width: int = 56) -> None:
    """Print a separator line.

    Args:
        style: 'thin' (─), 'thick' (━), 'double' (═), or 'dots' (·)
        width: Line width
    """
    chars = {"thin": "─", "thick": "━", "double": "═", "dots": "·"}
    colors = {"thin": Violet.MIDNIGHT, "thick": Violet.ELEVATED, "double": Violet.SURFACE, "dots": Violet.TEXT_MUTED}
    char = chars.get(style, "─")
    color = colors.get(style, Violet.TEXT_MUTED)
    print(f"  {color}{char * width}{Colors.RESET}")


def print_prompt() -> str:
    """Print the main prompt and return user input."""
    return input(f"  {Violet.ACCENT}▸{Colors.RESET} ").strip().lower()


def print_exit_message() -> None:
    """Print a refined exit message."""
    print()
    print(f"  {Violet.TEXT_MUTED}{'─' * 40}{Colors.RESET}")
    print(f"  {Violet.GLOW}Until next time.{Colors.RESET}")
    print()


def print_section_title(title: str, width: int = 56) -> None:
    """Print a section title with accent marker."""
    print(f"  {Violet.ACCENT}●{Colors.RESET} {Violet.BRIGHT}{Colors.BOLD}{title}{Colors.RESET}")
    print(f"  {Violet.ELEVATED}{'━' * (width - 4)}{Colors.RESET}")


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
