"""Centralized error handling for PROJECT_CONTROL."""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ── Custom Exceptions ───────────────────────────────────────────────────────

class ProjectControlError(Exception):
    """Base exception for all PROJECT_CONTROL errors."""
    def __init__(self, message: str, exit_code: int = 1, details: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.details = details or ""

    def __str__(self) -> str:
        msg = self.message
        if self.details:
            msg += f"\n  Details: {self.details}"
        return msg


class ValidationError(ProjectControlError):
    """Validation failed."""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, exit_code=2, details=details)


class OperationError(ProjectControlError):
    """Operation failed."""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, exit_code=1, details=details)


class ConfigurationError(ProjectControlError):
    """Configuration error."""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, exit_code=2, details=details)


class FileNotFoundError(ProjectControlError):
    """Required file or directory not found."""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, exit_code=2, details=details)


class DependencyError(ProjectControlError):
    """External dependency missing or unavailable."""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, exit_code=2, details=details)


class CorruptedDataError(ProjectControlError):
    """Data is corrupted or invalid."""
    def __init__(self, message: str, details: Optional[str] = None):
        super().__init__(message, exit_code=2, details=details)


# ── Error Handler ───────────────────────────────────────────────────────────

class ErrorHandler:
    """Centralized error handling with user-friendly messages."""

    @staticmethod
    def handle(error: Exception, context: str = "") -> int:
        """
        Handle exception with user-friendly message and appropriate exit code.

        Args:
            error: The exception to handle
            context: Additional context about where error occurred

        Returns:
            Appropriate exit code
        """
        if isinstance(error, ProjectControlError):
            return ErrorHandler._handle_project_control_error(error, context)
        elif isinstance(error, (KeyboardInterrupt, EOFError)):
            print("\n\nOperation cancelled by user.")
            return 130  # Standard exit code for SIGINT
        else:
            return ErrorHandler._handle_unexpected_error(error, context)

    @staticmethod
    def _handle_project_control_error(error: ProjectControlError, context: str) -> int:
        """Handle PROJECT_CONTROL specific errors."""
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"ERROR: {error.message}", file=sys.stderr)

        if context:
            print(f"\nContext: {context}", file=sys.stderr)

        if error.details:
            print(f"\n{error.details}", file=sys.stderr)

        # Add helpful suggestions based on error type
        suggestions = ErrorHandler._get_suggestions(error)
        if suggestions:
            print(f"\nSuggestions:", file=sys.stderr)
            for suggestion in suggestions:
                print(f"  • {suggestion}", file=sys.stderr)

        print(f"{'='*60}\n", file=sys.stderr)
        logger.error(f"{type(error).__name__}: {error.message} | Context: {context}")

        return error.exit_code

    @staticmethod
    def _handle_unexpected_error(error: Exception, context: str) -> int:
        """Handle unexpected errors."""
        print(f"\n{'='*60}", file=sys.stderr)
        print(f"UNEXPECTED ERROR: {str(error)}", file=sys.stderr)

        if context:
            print(f"\nContext: {context}", file=sys.stderr)

        print(f"\nThis is a bug. Please report it with the following information:", file=sys.stderr)
        print(f"  Error type: {type(error).__name__}", file=sys.stderr)
        print(f"  Error message: {str(error)}", file=sys.stderr)

        print(f"\nSuggestions:", file=sys.stderr)
        print(f"  • Run 'pc scan' to create a fresh snapshot", file=sys.stderr)
        print(f"  • Check logs for more details", file=sys.stderr)
        print(f"  • Report this issue: https://github.com/danielhlavac/project-control/issues", file=sys.stderr)

        print(f"{'='*60}\n", file=sys.stderr)
        logger.exception(f"Unexpected error in {context}")

        return 1

    @staticmethod
    def _get_suggestions(error: ProjectControlError) -> list[str]:
        """Get helpful suggestions based on error type."""
        suggestions = []

        if isinstance(error, FileNotFoundError):
            if "snapshot" in error.message.lower():
                suggestions.extend([
                    "Run 'pc scan' to create a snapshot",
                    "Ensure you're in the correct project directory",
                ])
            elif "graph" in error.message.lower():
                suggestions.extend([
                    "Run 'pc graph build' to build the dependency graph",
                    "Ensure you've run 'pc scan' first",
                ])
            else:
                suggestions.append("Check that all required files and directories exist")

        elif isinstance(error, ValidationError):
            suggestions.extend([
                "Check your configuration in .project-control/",
                "Run 'pc init' to reset to defaults",
                "Validate your project structure",
            ])

        elif isinstance(error, DependencyError):
            suggestions.extend([
                "Install the missing dependency",
                "Check if the service is running (e.g., Ollama for embeddings)",
                "Verify your system meets all requirements",
            ])

        elif isinstance(error, CorruptedDataError):
            suggestions.extend([
                "Run 'pc scan' to create a fresh snapshot",
                "Try deleting .project-control/ and running 'pc init'",
                "Check for disk errors or permission issues",
            ])

        elif isinstance(error, ConfigurationError):
            suggestions.extend([
                "Check .project-control/patterns.yaml",
                "Check .project-control/graph.config.yaml",
                "Run 'pc init' to reset to defaults",
            ])

        return suggestions

    @staticmethod
    def wrap(context: str):
        """
        Decorator to wrap functions with error handling.

        Usage:
            @ErrorHandler.wrap("Scanning project")
            def scan_project(...):
                ...
        """
        def decorator(func):
            def wrapper(*args, **kwargs):
                try:
                    return func(*args, **kwargs)
                except ProjectControlError as e:
                    sys.exit(ErrorHandler.handle(e, context))
                except Exception as e:
                    sys.exit(ErrorHandler.handle(e, context))
            return wrapper
        return decorator


# ── Context Managers ───────────────────────────────────────────────────────

class ErrorContext:
    """Context manager for error handling with automatic context."""

    def __init__(self, context: str, reraise: bool = False):
        self.context = context
        self.reraise = reraise

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            exit_code = ErrorHandler.handle(exc_val, self.context)
            if not self.reraise:
                sys.exit(exit_code)
        return False


# ── Validation Helpers ─────────────────────────────────────────────────────

class Validator:
    """Common validation helpers."""

    @staticmethod
    def require_file_exists(path: Path, name: str = "file") -> None:
        """Require that a file exists, raise FileNotFoundError if not."""
        if not path.exists():
            raise FileNotFoundError(
                f"{name} not found: {path}",
                details=f"Expected path: {path.resolve()}"
            )

    @staticmethod
    def require_dir_exists(path: Path, name: str = "directory") -> None:
        """Require that a directory exists, raise FileNotFoundError if not."""
        if not path.exists():
            raise FileNotFoundError(
                f"{name} not found: {path}",
                details=f"Expected path: {path.resolve()}"
            )
        if not path.is_dir():
            raise ValidationError(
                f"Path exists but is not a directory: {path}",
                details=f"Expected a directory, got a file"
            )

    @staticmethod
    def require_true(condition: bool, message: str, details: Optional[str] = None) -> None:
        """Require a condition to be True, raise ValidationError if not."""
        if not condition:
            raise ValidationError(message, details=details)

    @staticmethod
    def validate_json_loadable(path: Path, name: str = "JSON file") -> None:
        """Validate that a file contains valid JSON."""
        import json
        try:
            path.read_text(encoding="utf-8")
        except (OSError, IOError) as e:
            raise FileNotFoundError(f"Cannot read {name}: {path}", details=str(e))
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as e:
            raise CorruptedDataError(
                f"{name} contains invalid JSON: {path}",
                details=f"JSON error at line {e.lineno}, column {e.colno}: {e.msg}"
            )
