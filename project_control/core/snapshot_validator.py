"""Strict snapshot schema validator."""

from __future__ import annotations

import re
from typing import Any, Dict, List


class SnapshotValidationError(Exception):
    """Raised when snapshot schema validation fails."""


def _ensure(condition: bool, message: str) -> None:
    if not condition:
        raise SnapshotValidationError(message)


def _validate_file_entry(entry: Dict[str, Any], index: int) -> None:
    prefix = f"files[{index}]"
    _ensure(isinstance(entry, dict), f"{prefix} must be a dict.")

    required_keys: List[str] = ["path", "size", "modified", "sha256"]
    for key in required_keys:
        _ensure(key in entry, f"{prefix} missing required key: {key}")
        _ensure(entry[key] is not None, f"{prefix}.{key} must not be None.")

    path = entry["path"]
    _ensure(isinstance(path, str) and path.strip(), f"{prefix}.path must be a non-empty string.")

    size = entry["size"]
    _ensure(isinstance(size, int) and not isinstance(size, bool), f"{prefix}.size must be an integer.")
    _ensure(size >= 0, f"{prefix}.size must be >= 0.")

    modified = entry["modified"]
    _ensure(isinstance(modified, str) and modified.strip(), f"{prefix}.modified must be a non-empty string.")

    sha256 = entry["sha256"]
    _ensure(isinstance(sha256, str), f"{prefix}.sha256 must be a string.")
    _ensure(
        len(sha256) == 64 and re.fullmatch(r"[0-9a-fA-F]{64}", sha256) is not None,
        f"{prefix}.sha256 must be a 64-character hex string.",
    )


def validate_snapshot(snapshot: Dict[str, Any]) -> None:
    """Validate snapshot structure against the required schema."""
    _ensure(isinstance(snapshot, dict), "Snapshot must be a dict.")
    _ensure(snapshot is not None, "Snapshot must not be None.")
    _ensure("files" in snapshot, "Snapshot missing required key: files")

    files = snapshot["files"]
    _ensure(files is not None, "Snapshot 'files' must not be None.")
    _ensure(isinstance(files, list), "Snapshot 'files' must be a list.")

    for index, entry in enumerate(files):
        _validate_file_entry(entry, index)


if __name__ == "__main__":
    # Inline sanity checks (minimal, no external test runner needed)
    VALID_SHA = "0" * 64

    def _run(name: str, payload: Dict[str, Any], should_fail: bool) -> None:
        try:
            validate_snapshot(payload)
            outcome = "passed"
        except SnapshotValidationError as exc:
            outcome = f"failed ({exc})"
        print(f"{name}: {outcome}")
        if should_fail and outcome.startswith("passed"):
            raise SystemExit(1)
        if not should_fail and outcome.startswith("failed"):
            raise SystemExit(1)

    valid_snapshot = {"files": [{"path": "app.py", "size": 1, "modified": "2026-02-18T00:00:00Z", "sha256": VALID_SHA}]}
    missing_key = {"files": [{"size": 1, "modified": "2026-02-18T00:00:00Z", "sha256": VALID_SHA}]}
    bad_hash = {"files": [{"path": "app.py", "size": 1, "modified": "2026-02-18T00:00:00Z", "sha256": "abc"}]}

    _run("valid snapshot", valid_snapshot, should_fail=False)
    _run("missing path", missing_key, should_fail=True)
    _run("bad sha", bad_hash, should_fail=True)

