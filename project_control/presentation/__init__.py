"""Shared presentation adapters for CLI-compatible workflows."""

from project_control.presentation.adapters import (
    PresentationResult,
    present_dead,
    present_ghost,
    present_graph_report,
    present_graph_trace,
    present_report_registry,
    present_scan,
    present_ui_verification,
    present_vfx_audit,
)

__all__ = [
    "PresentationResult",
    "present_scan",
    "present_ghost",
    "present_dead",
    "present_graph_report",
    "present_graph_trace",
    "present_vfx_audit",
    "present_ui_verification",
    "present_report_registry",
]
