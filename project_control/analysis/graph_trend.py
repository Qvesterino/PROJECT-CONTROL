"""Compute stability trends from drift history."""

from __future__ import annotations

import math
from statistics import mean, pstdev
from typing import Any, Dict, List


class GraphTrendAnalyzer:
    def __init__(self, history: List[Dict[str, Any]]):
        self.history = history

    def _intensity(self, drift: Dict[str, Any]) -> float:
        node_delta = abs(drift.get("metric_deltas", {}).get("nodes", 0))
        edge_delta = abs(drift.get("metric_deltas", {}).get("edges", 0))
        density_delta = abs(drift.get("metric_deltas", {}).get("density", 0))
        smell_delta = abs(drift.get("metric_deltas", {}).get("smell_score", 0))
        return node_delta + edge_delta + density_delta + smell_delta

    def compute(self) -> Dict[str, Any]:
        intensities = [self._intensity(record) for record in self.history]
        if not intensities:
            return {}
        avg_intensity = mean(intensities)
        volatility = pstdev(intensities) if len(intensities) > 1 else 0.0
        stability_index = 1 / (1 + avg_intensity) if avg_intensity >= 0 else 1.0
        if avg_intensity <= 0.05:
            classification = "STABLE"
        elif avg_intensity <= 0.2:
            classification = "MODERATE"
        else:
            classification = "UNSTABLE"
        return {
            "intensity": intensities,
            "avg_intensity": round(avg_intensity, 4),
            "volatility": round(volatility, 4),
            "stability_index": round(stability_index, 4),
            "classification": classification,
        }
