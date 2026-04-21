"""Progress indicators and progress bars for PROJECT_CONTROL."""

from __future__ import annotations

import sys
import time
import threading
from dataclasses import dataclass
from typing import Optional, Callable


# ── Progress Bar Configuration ─────────────────────────────────────────────

PROGRESS_BAR_WIDTH = 40
SPINNER_CHARS = ["|", "/", "-", "\\"]
SPINNER_INTERVAL = 0.1


# ── ANSI Escape Codes (with fallback) ───────────────────────────────────────

class ANSI:
    """ANSI escape codes for terminal formatting."""

    # Cross-platform check
    @staticmethod
    def supports_ansi() -> bool:
        """Check if terminal supports ANSI codes."""
        # Windows 10+ supports ANSI
        if sys.platform == "win32":
            try:
                import ctypes
                kernel32 = ctypes.windll.kernel32
                # Enable ANSI support on Windows
                kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
                return True
            except Exception:
                return False
        # Unix-like systems typically support ANSI
        return True

    CLEAR_LINE = "\033[K" if supports_ansi() else ""
    RESET = "\033[0m" if supports_ansi() else ""
    BOLD = "\033[1m" if supports_ansi() else ""
    GREEN = "\033[32m" if supports_ansi() else ""
    YELLOW = "\033[33m" if supports_ansi() else ""
    CYAN = "\033[36m" if supports_ansi() else ""
    RED = "\033[31m" if supports_ansi() else ""


# ── Progress Bar Classes ───────────────────────────────────────────────────

@dataclass
class ProgressState:
    """Current progress state."""
    current: int = 0
    total: int = 0
    message: str = ""
    start_time: float = 0.0
    last_update: float = 0.0
    finished: bool = False


class ProgressBar:
    """
    Simple cross-platform progress bar.

    Usage:
        bar = ProgressBar(total=100, message="Scanning files")
        for i in range(100):
            # Do work
            bar.update(i + 1)
        bar.finish()
    """

    def __init__(self, total: int, message: str = "", show_eta: bool = True):
        """
        Initialize progress bar.

        Args:
            total: Total number of items
            message: Optional message to display
            show_eta: Whether to show estimated time remaining
        """
        self.state = ProgressState(
            total=total,
            message=message,
            start_time=time.time(),
            last_update=time.time(),
        )
        self.show_eta = show_eta
        self._width = PROGRESS_BAR_WIDTH
        self._spinner_idx = 0
        self._spinner_thread: Optional[threading.Thread] = None
        self._stop_spinner = False
        self._lock = threading.Lock()

    def update(self, current: int, message: Optional[str] = None) -> None:
        """
        Update progress.

        Args:
            current: Current progress value
            message: Optional new message to display
        """
        with self._lock:
            self.state.current = current
            if message is not None:
                self.state.message = message
            self.state.last_update = time.time()
            self._render()

    def increment(self, delta: int = 1) -> None:
        """Increment progress by delta."""
        self.update(self.state.current + delta)

    def set_message(self, message: str) -> None:
        """Update the message."""
        with self._lock:
            self.state.message = message
            self._render()

    def _render(self) -> None:
        """Render the progress bar."""
        if self.state.finished:
            return

        # Calculate percentage
        total = self.state.total
        current = self.state.current
        if total <= 0:
            percent = 0.0
        else:
            percent = min(100.0, (current / total) * 100.0)

        # Calculate bar width
        filled_width = int((percent / 100.0) * self._width)
        empty_width = self._width - filled_width

        # Build bar (ASCII-safe)
        bar = ANSI.GREEN + "=" * filled_width + ANSI.RESET
        if empty_width > 0:
            bar += ANSI.YELLOW + "-" * empty_width + ANSI.RESET

        # Calculate ETA
        eta_str = ""
        if self.show_eta and total > 0 and current > 0:
            elapsed = time.time() - self.state.start_time
            if elapsed > 0:
                rate = current / elapsed
                if rate > 0:
                    remaining = (total - current) / rate
                    eta_str = f" ETA: {self._format_time(remaining)}"

        # Build progress string (only update on same line)
        progress_str = (
            f"\r{ANSI.CLEAR_LINE}"
            f"{bar} {ANSI.CYAN}{percent:5.1f}%{ANSI.RESET}"
            f" ({current}/{total}){eta_str}"
        )

        # Render
        sys.stdout.write(progress_str)
        sys.stdout.flush()

    def _format_time(self, seconds: float) -> str:
        """Format time in seconds to human-readable string."""
        if seconds < 60:
            return f"{seconds:.0f}s"
        elif seconds < 3600:
            minutes = seconds / 60
            return f"{minutes:.0f}m"
        else:
            hours = seconds / 3600
            return f"{hours:.1f}h"

    def finish(self, message: Optional[str] = None) -> None:
        """
        Finish the progress bar.

        Args:
            message: Optional final message
        """
        with self._lock:
            self.state.finished = True
            self.state.current = self.state.total

            # Final render with 100%
            self._render()

            # Clear line and print final message
            sys.stdout.write(f"\r{ANSI.CLEAR_LINE}")
            if message:
                sys.stdout.write(f"{ANSI.GREEN}[OK]{ANSI.RESET} {message}\n")
            else:
                sys.stdout.write(f"{ANSI.GREEN}[OK]{ANSI.RESET} {self.state.message} completed\n")
            sys.stdout.flush()

    def __enter__(self):
        """Context manager support."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Finish progress bar on context exit."""
        if not self.state.finished:
            self.finish()


class Spinner:
    """
    Simple spinner for indeterminate progress.

    Usage:
        with Spinner("Processing..."):
            # Do work
            time.sleep(2)
    """

    def __init__(self, message: str = "Processing..."):
        """
        Initialize spinner.

        Args:
            message: Message to display
        """
        self.message = message
        self._stop = False
        self._thread: Optional[threading.Thread] = None
        self._idx = 0

    def _spin(self) -> None:
        """Spinner thread function."""
        while not self._stop:
            spinner_char = SPINNER_CHARS[self._idx % len(SPINNER_CHARS)]
            sys.stdout.write(
                f"\r{ANSI.CLEAR_LINE}"
                f"{ANSI.CYAN}{spinner_char}{ANSI.RESET} {self.message}"
            )
            sys.stdout.flush()
            time.sleep(SPINNER_INTERVAL)
            self._idx += 1

    def start(self) -> None:
        """Start the spinner."""
        self._stop = False
        self._thread = threading.Thread(target=self._spin, daemon=True)
        self._thread.start()

    def stop(self, message: Optional[str] = None) -> None:
        """
        Stop the spinner.

        Args:
            message: Optional final message
        """
        self._stop = True
        if self._thread:
            self._thread.join(timeout=0.2)

        # Clear spinner and show completion
        sys.stdout.write(f"\r{ANSI.CLEAR_LINE}")
        if message:
            sys.stdout.write(f"{ANSI.GREEN}[OK]{ANSI.RESET} {message}\n")
        sys.stdout.flush()

    def __enter__(self):
        """Context manager support."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner on context exit."""
        if exc_type is None:
            self.stop(f"{self.message} completed")
        else:
            self.stop(f"{self.message} failed")


# ── Progress Context Manager ───────────────────────────────────────────────

class ProgressContext:
    """
    Context manager that automatically creates appropriate progress indicator.

    Usage:
        with ProgressContext(total=100, message="Processing") as progress:
            for item in items:
                # Process item
                progress.update()
    """

    def __init__(self, total: int = 0, message: str = "", show_eta: bool = True):
        """
        Initialize progress context.

        Args:
            total: Total items (0 = indeterminate)
            message: Progress message
            show_eta: Whether to show ETA
        """
        self.total = total
        self.message = message
        self.show_eta = show_eta
        self._progress: Optional[ProgressBar] = None
        self._spinner: Optional[Spinner] = None
        self._current = 0

    def __enter__(self):
        """Enter context and start progress."""
        if self.total > 0:
            self._progress = ProgressBar(self.total, self.message, self.show_eta)
        else:
            self._spinner = Spinner(self.message)
            self._spinner.start()
        return self

    def update(self, delta: int = 1, message: Optional[str] = None) -> None:
        """
        Update progress.

        Args:
            delta: Amount to increment (for determinate progress)
            message: New message
        """
        if self._progress:
            self._current += delta
            self._progress.update(self._current, message)
        elif self._spinner and message:
            self._spinner.message = message

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and finish progress."""
        if self._progress:
            if exc_type is None:
                self._progress.finish()
            else:
                self._progress.finish(f"{self.message} failed")
        elif self._spinner:
            if exc_type is None:
                self._spinner.stop(f"{self.message} completed")
            else:
                self._spinner.stop(f"{self.message} failed")


# ── Progress Iterators ─────────────────────────────────────────────────────

def progress_iterate(
    iterable,
    message: str = "Processing",
    show_eta: bool = True,
    callback: Optional[Callable[[int, Any], None]] = None,
):
    """
    Iterate over iterable with progress bar.

    Args:
        iterable: Iterable to process
        message: Progress message
        show_eta: Whether to show ETA
        callback: Optional callback(current, item) called for each item

    Yields:
        Items from iterable

    Example:
        for item in progress_iterate(items, "Processing items"):
            # Process item
            pass
    """
    try:
        total = len(iterable)
    except TypeError:
        # No len() available, use spinner
        with Spinner(message) as spinner:
            for item in iterable:
                yield item
                if callback:
                    callback(-1, item)
    else:
        with ProgressBar(total, message, show_eta) as bar:
            for idx, item in enumerate(iterable, 1):
                if callback:
                    callback(idx, item)
                bar.update(idx)
                yield item


# ── Silent Progress (for testing/disabled) ─────────────────────────────────

class SilentProgress:
    """No-op progress indicator for testing or when progress is disabled."""

    def __init__(self, *args, **kwargs):
        pass

    def update(self, *args, **kwargs):
        pass

    def increment(self, *args, **kwargs):
        pass

    def set_message(self, *args, **kwargs):
        pass

    def finish(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args, **kwargs):
        pass


# ── Factory Functions ─────────────────────────────────────────────────────

def create_progress_bar(total: int, message: str = "", show_eta: bool = True) -> ProgressBar:
    """
    Create a progress bar.

    Args:
        total: Total number of items
        message: Progress message
        show_eta: Whether to show ETA

    Returns:
        ProgressBar instance
    """
    return ProgressBar(total, message, show_eta)


def create_spinner(message: str = "Processing...") -> Spinner:
    """
    Create a spinner.

    Args:
        message: Spinner message

    Returns:
        Spinner instance
    """
    return Spinner(message)


def create_progress(
    total: int = 0,
    message: str = "",
    show_eta: bool = True,
    enabled: bool = True,
):
    """
    Create appropriate progress indicator.

    Args:
        total: Total items (0 = spinner, >0 = progress bar)
        message: Progress message
        show_eta: Whether to show ETA
        enabled: Whether to enable progress (False = silent)

    Returns:
        ProgressBar, Spinner, or SilentProgress
    """
    if not enabled:
        return SilentProgress()

    if total > 0:
        return ProgressBar(total, message, show_eta)
    else:
        return Spinner(message)
