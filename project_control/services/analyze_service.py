from __future__ import annotations

import json
from pathlib import Path

from project_control.core.ghost import ghost
from project_control.core.content_store import ContentStore
from project_control.config.patterns_loader import load_patterns
from project_control.graph.ensure import ensure_graph
from project_control.services._config import config_with_state
from project_control.ui.state import AppState


def ghost_fast(project_root: Path) -> None:
    """Run shallow ghost detectors using canonical ghost core."""
    snapshot_path = project_root / ".project-control" / "snapshot.json"
    if not snapshot_path.exists():
        print("Run pc scan first.")
        return
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
    content_store = ContentStore(snapshot, snapshot_path)
    patterns = load_patterns(project_root)

    result = ghost(snapshot, patterns, content_store)
    counts = {k: len(v) for k, v in result.items() if isinstance(v, list)}
    print("Ghost detectors (shallow):")
    for k, v in sorted(counts.items()):
        print(f"- {k}: {v}")


def ghost_structural(project_root: Path, state: AppState) -> None:
    cfg = config_with_state(project_root, state)
    _, metrics_path, _ = ensure_graph(project_root, cfg, force=False)
    try:
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    except Exception:
        print("Metrics unavailable; run graph build first.")
        return
    totals = metrics.get("totals", {})
    cycles = metrics.get("cycles", [])
    orphans = metrics.get("orphanCandidates", [])
    print("Structural graph findings (from metrics):")
    print(f"- Nodes: {totals.get('nodeCount', '?')}")
    print(f"- Edges: {totals.get('edgeCount', '?')}")
    print(f"- Cycles: {len(cycles)}")
    print(f"- Orphans: {len(orphans)}")
