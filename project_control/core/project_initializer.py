from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

from project_control.config.patterns_loader import get_default_patterns
from project_control.config.patron_path_loader import get_default_patron_path_contract, get_patron_path_contract_path


@dataclass(frozen=True)
class InitializationResult:
    """Details about an initialization pass."""

    initialized_now: bool
    created_control_dir: bool
    created_patterns: bool
    created_status: bool
    created_exports_dir: bool
    created_out_dir: bool
    updated_gitignore: bool


def _ensure_gitignore(project_root: Path) -> bool:
    """Add .project-control/ to .gitignore when missing."""
    gitignore = project_root / ".gitignore"
    entry = ".project-control/"

    existing_lines: list[str] = []
    if gitignore.exists():
        existing_lines = gitignore.read_text(encoding="utf-8").splitlines()

    if any(line.strip() == entry.rstrip("/") or line.strip() == entry for line in existing_lines):
        return False

    with gitignore.open("a", encoding="utf-8") as handle:
        if existing_lines and existing_lines[-1].strip() != "":
            handle.write("\n")
        handle.write(f"\n# Project Control artifacts\n{entry}\n")

    return True


def ensure_project_initialized(project_root: Path) -> InitializationResult:
    """Create the minimum PROJECT CONTROL structure for interactive flows."""
    control_dir = project_root / ".project-control"
    exports_dir = control_dir / "exports"
    out_dir = control_dir / "out"
    patterns_file = control_dir / "patterns.yaml"
    patron_path_file = get_patron_path_contract_path(project_root)
    status_file = control_dir / "status.yaml"

    created_control_dir = False
    if not control_dir.exists():
        control_dir.mkdir(parents=True, exist_ok=True)
        created_control_dir = True

    created_exports_dir = False
    if not exports_dir.exists():
        exports_dir.mkdir(parents=True, exist_ok=True)
        created_exports_dir = True

    created_out_dir = False
    if not out_dir.exists():
        out_dir.mkdir(parents=True, exist_ok=True)
        created_out_dir = True

    created_patterns = False
    if not patterns_file.exists():
        with patterns_file.open("w", encoding="utf-8") as handle:
            yaml.dump(get_default_patterns(), handle, sort_keys=False)
        created_patterns = True

    created_patron_path = False
    if not patron_path_file.exists():
        with patron_path_file.open("w", encoding="utf-8") as handle:
            yaml.dump(get_default_patron_path_contract(), handle, sort_keys=False)
        created_patron_path = True

    created_status = False
    if not status_file.exists():
        with status_file.open("w", encoding="utf-8") as handle:
            yaml.dump({"tags": {}}, handle, sort_keys=False)
        created_status = True

    updated_gitignore = _ensure_gitignore(project_root)
    initialized_now = any(
        (
            created_control_dir,
            created_exports_dir,
            created_out_dir,
            created_patterns,
            created_status,
            updated_gitignore,
            created_patron_path,
        )
    )

    return InitializationResult(
        initialized_now=initialized_now,
        created_control_dir=created_control_dir,
        created_patterns=created_patterns,
        created_status=created_status,
        created_exports_dir=created_exports_dir,
        created_out_dir=created_out_dir,
        updated_gitignore=updated_gitignore,
    )
