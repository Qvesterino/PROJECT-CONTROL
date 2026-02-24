"""Versioned, bounded drift history persistence."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DRIFT_HISTORY_VERSION = 1
MAX_HISTORY_ENTRIES = 500

_CORRUPTED_MSG = "DRIFT HISTORY CORRUPTED - ignoring file (no overwrite performed)"


class DriftHistoryError(Exception):
    """Base error for drift history issues."""


class DriftHistoryCorrupted(DriftHistoryError):
    """Raised when drift history structure is invalid."""


class DriftHistoryVersionMismatch(DriftHistoryError):
    """Raised when drift history version is unsupported."""


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise DriftHistoryCorrupted(message)


def _validate_history_structure(data: Any) -> List[Dict[str, Any]]:
    _ensure(isinstance(data, dict), "History root must be a dict.")
    _ensure("version" in data, "History missing version.")
    version = data["version"]
    if version != DRIFT_HISTORY_VERSION:
        raise DriftHistoryVersionMismatch(f"Unsupported drift history version: {version}")

    _ensure("history" in data, "History missing 'history' key.")
    history = data["history"]
    _ensure(isinstance(history, list), "'history' must be a list.")

    for idx, entry in enumerate(history):
        _ensure(isinstance(entry, dict), f"history[{idx}] must be a dict.")
        _ensure("timestamp" in entry, f"history[{idx}] missing timestamp.")
        _ensure("drift" in entry, f"history[{idx}] missing drift.")
        ts = entry["timestamp"]
        _ensure(isinstance(ts, str) and ts, f"history[{idx}].timestamp must be a non-empty string.")
        _ensure("T" in ts and (ts.endswith("Z") or ts.endswith("+00:00")), f"history[{idx}].timestamp must be ISO UTC.")
        _ensure(isinstance(entry["drift"], dict), f"history[{idx}].drift must be a dict.")

    return history


def load_drift_history(path: Path) -> Optional[List[Dict[str, Any]]]:
    """
    Load and validate drift history.

    Returns a list when valid, [] when missing file, or None when corrupted/unsupported.
    """
    if not path.exists():
        return []

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, JSONDecodeError):
        print(_CORRUPTED_MSG)
        return None

    try:
        return _validate_history_structure(data)
    except DriftHistoryVersionMismatch:
        print(f"DRIFT HISTORY VERSION MISMATCH - expected {DRIFT_HISTORY_VERSION}, found {data.get('version')} (ignoring file)")
        return None
    except DriftHistoryCorrupted:
        print(_CORRUPTED_MSG)
        return None


def append_drift_history(
    path: Path, drift: Dict[str, Any], timestamp: str, debug: bool = False
) -> Optional[Tuple[List[Dict[str, Any]], int]]:
    """
    Append a drift record and persist bounded history.

    Returns (history, trimmed_count) on success, or None when history could not be used.
    """
    history = load_drift_history(path)
    if history is None:
        return None

    history.append({"timestamp": timestamp, "drift": drift})

    trimmed = 0
    if len(history) > MAX_HISTORY_ENTRIES:
        trimmed = len(history) - MAX_HISTORY_ENTRIES
        history = history[-MAX_HISTORY_ENTRIES:]

    payload = {"version": DRIFT_HISTORY_VERSION, "history": history}
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    if debug:
        print(f"Drift history entries: {len(history)}")
        print(f"Trimmed: {trimmed}")
        print(f"Version: {DRIFT_HISTORY_VERSION}")

    return history, trimmed
