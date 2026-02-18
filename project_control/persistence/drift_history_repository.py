"""Persistent, bounded drift history storage."""

from __future__ import annotations

import json
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Optional

DRIFT_HISTORY_VERSION = 1
DEFAULT_MAX_ENTRIES = 500

_CORRUPTED_MSG = "DRIFT HISTORY CORRUPTED - ignoring file (no overwrite performed)"


class DriftHistoryRepository:
    def __init__(self, project_root: Path, max_entries: int = DEFAULT_MAX_ENTRIES):
        self.project_root = project_root
        self.max_entries = max_entries
        self.path = self.project_root / ".project-control" / "drift_history.json"
        self.data: Optional[Dict[str, Any]] = None

    def _validate(self, data: Any) -> Dict[str, Any]:
        if not isinstance(data, dict):
            raise ValueError("History root must be a dict.")
        if "version" not in data:
            raise ValueError("History missing version.")
        if data["version"] != DRIFT_HISTORY_VERSION:
            raise ValueError(f"version-mismatch:{data['version']}")
        if "history" not in data or not isinstance(data["history"], list):
            raise ValueError("History missing 'history' list.")
        for idx, entry in enumerate(data["history"]):
            if not isinstance(entry, dict):
                raise ValueError(f"history[{idx}] must be a dict.")
            ts = entry.get("timestamp")
            drift = entry.get("drift")
            if not isinstance(ts, str) or not ts:
                raise ValueError(f"history[{idx}].timestamp must be a non-empty string.")
            if not isinstance(drift, dict):
                raise ValueError(f"history[{idx}].drift must be a dict.")
        return data

    def load(self) -> Optional[Dict[str, Any]]:
        if not self.path.exists():
            self.data = {"version": DRIFT_HISTORY_VERSION, "history": []}
            return self.data
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, JSONDecodeError):
            print(_CORRUPTED_MSG)
            self.data = None
            return None
        try:
            self.data = self._validate(raw)
            return self.data
        except ValueError as exc:
            if str(exc).startswith("version-mismatch:"):
                found = str(exc).split(":")[1]
                print(f"DRIFT HISTORY VERSION MISMATCH - expected {DRIFT_HISTORY_VERSION}, found {found} (ignoring file)")
            else:
                print(_CORRUPTED_MSG)
            self.data = None
            return None

    def append(self, drift_entry: Dict[str, Any]) -> None:
        if self.data is None:
            return
        self.data.setdefault("history", []).append(drift_entry)
        if len(self.data["history"]) > self.max_entries:
            self.data["history"] = self.data["history"][-self.max_entries :]

    def save(self) -> None:
        if self.data is None:
            return
        payload = {
            "version": DRIFT_HISTORY_VERSION,
            "history": self.data.get("history", []),
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    def current_history(self) -> List[Dict[str, Any]]:
        if self.data and isinstance(self.data.get("history"), list):
            return self.data["history"]
        return []
