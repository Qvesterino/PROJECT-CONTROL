import json
from pathlib import Path


def load_snapshot(project_root):
    snapshot_path = Path(project_root) / ".project-control" / "snapshot.json"

    if not snapshot_path.exists():
        raise FileNotFoundError("Snapshot not found. Run scan first.")

    with open(snapshot_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def get_snapshot_files(project_root):
    snapshot = load_snapshot(project_root)
    return snapshot.get("files", [])
