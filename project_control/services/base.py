from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, Callable


@dataclass
class ServiceResult:
    """Structured result from service execution."""

    success: bool
    message: str
    data: Any = None
    exit_code: int = 0


class Service(Protocol):
    """Standardized interface for all services."""

    def execute(self, project_root: Path, **kwargs) -> ServiceResult:
        """Execute service and return structured result.

        Args:
            project_root: Root path of the project
            **kwargs: Additional service-specific parameters

        Returns:
            ServiceResult with success status, message, and optional data
        """
        ...


def with_error_handling(func: Callable) -> Callable:
    """Decorator to convert exceptions to ServiceResult.

    Args:
        func: Service function to wrap

    Returns:
        Wrapped function that returns ServiceResult instead of raising exceptions
    """
    from project_control.core.error_handler import ProjectControlError

    def wrapper(*args, **kwargs) -> ServiceResult:
        try:
            return func(*args, **kwargs)
        except ProjectControlError as e:
            return ServiceResult(
                success=False,
                message=e.message,
                data=None,
                exit_code=e.exit_code
            )
        except Exception as e:
            return ServiceResult(
                success=False,
                message=f"Unexpected error: {str(e)}",
                data=None,
                exit_code=1
            )
    return wrapper
