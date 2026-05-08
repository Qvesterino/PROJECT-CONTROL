"""Patron's Path integration contract loader."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Union

import yaml

LOGGER = logging.getLogger(__name__)


DEFAULT_PATRON_PATH_CONTRACT: Dict[str, Any] = {
    "codebase_nebula_root": r"D:\QVESTER_LANDING_PAGE\apps\Codebase_Nebula",
    "patrons_path_root": r"D:\QVESTER_LANDING_PAGE\apps\Patrons_Path",
    "file_genome": {
        "analyze_url": "https://file-genome.com/analyze",
        "batch_url": "https://file-genome.com/batch",
    },
    "nebula_bridge": {
        "directory": ".project-control/exports",
        "file_name": "nebula_bridge.json",
    },
}


def _copy_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _copy_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_copy_value(item) for item in value]
    return value


def _merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    merged = _copy_value(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged[key], value)
        else:
            merged[key] = _copy_value(value)
    return merged


def get_default_patron_path_contract() -> Dict[str, Any]:
    """Return a fresh copy of the default Patron's Path contract."""
    return _copy_value(DEFAULT_PATRON_PATH_CONTRACT)


def get_patron_path_contract_path(project_root: Union[str, Path]) -> Path:
    """Return the on-disk path of the Patron's Path contract file."""
    return Path(project_root) / ".project-control" / "patron_path.yaml"


def load_patron_path_contract(project_root: Union[str, Path]) -> Dict[str, Any]:
    """Load the Patron's Path contract, falling back to built-in defaults."""
    contract_path = get_patron_path_contract_path(project_root)

    if not contract_path.is_file():
        return get_default_patron_path_contract()

    try:
        with contract_path.open(encoding="utf-8") as stream:
            data = yaml.safe_load(stream) or {}
    except (yaml.YAMLError, OSError) as error:
        LOGGER.debug("Failed to load Patron's Path contract from %s: %s", contract_path, error)
        return get_default_patron_path_contract()

    if not isinstance(data, dict):
        return get_default_patron_path_contract()

    return _merge_dicts(get_default_patron_path_contract(), data)
