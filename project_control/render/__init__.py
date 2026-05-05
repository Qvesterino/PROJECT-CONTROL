"""Render layer for analysis results."""

from project_control.render.dead_renderer import render_dead
from project_control.render.ui_verification_renderer import (
    render_ui_verification_console_summary,
    render_ui_verification_markdown,
    write_ui_verification_html_report,
    write_ui_verification_json_report,
    write_ui_verification_markdown_report,
    write_ui_verification_outputs,
)
from project_control.render.vfx_contract_renderer import (
    render_vfx_contract_console,
    render_vfx_contract_markdown,
    write_vfx_contract_outputs,
)

__all__ = [
    "render_dead",
    "render_ui_verification_console_summary",
    "render_ui_verification_markdown",
    "render_vfx_contract_console",
    "render_vfx_contract_markdown",
    "write_ui_verification_html_report",
    "write_ui_verification_json_report",
    "write_ui_verification_markdown_report",
    "write_ui_verification_outputs",
    "write_vfx_contract_outputs",
]
