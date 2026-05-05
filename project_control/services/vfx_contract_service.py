"""Service wrapper for VFX contract audits."""

from __future__ import annotations

from pathlib import Path

from project_control.analysis.vfx_contract_audit import (
    VFXContractAuditResult,
    analyze_vfx_contract,
)
from project_control.render.vfx_contract_renderer import write_vfx_contract_outputs


def run_vfx_contract_audit(project_root: Path, output_dir: Path | None = None) -> tuple[VFXContractAuditResult, Path, Path]:
    """Run the VFX contract audit and persist its standard outputs."""
    result = analyze_vfx_contract(project_root)
    target_dir = output_dir or project_root / ".project-control" / "exports"
    markdown_path, json_path = write_vfx_contract_outputs(result, target_dir)
    return result, markdown_path, json_path