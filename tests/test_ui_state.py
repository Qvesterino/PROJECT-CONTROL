"""Tests for persistent UI app state."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest import TestCase

from project_control.ui.state import (
    AppState,
    add_to_favorites,
    add_to_history,
    load_state,
    remove_from_favorites,
    save_state,
)


class TestUIState(TestCase):
    def test_state_round_trip_preserves_last_ui_verification_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            state = AppState(
                project_mode="python",
                graph_profile="strict",
                trace_direction="outbound",
                trace_depth=12,
                trace_all_paths=True,
                favorites=["alpha"],
                history=["scan"],
                onboarding_seen=True,
                last_ui_verification_profile="beta",
            )

            save_state(project_root, state)
            loaded_state = load_state(project_root)

            self.assertEqual(loaded_state.project_mode, "python")
            self.assertEqual(loaded_state.graph_profile, "strict")
            self.assertEqual(loaded_state.last_ui_verification_profile, "beta")

    def test_state_helpers_preserve_last_ui_verification_profile(self) -> None:
        state = AppState(
            favorites=["alpha"],
            history=["scan"],
            last_ui_verification_profile="beta",
        )

        updated_history_state = add_to_history(state, "trace")
        updated_favorites_state = add_to_favorites(state, "gamma")
        removed_favorites_state = remove_from_favorites(updated_favorites_state, "gamma")

        self.assertEqual(updated_history_state.last_ui_verification_profile, "beta")
        self.assertEqual(updated_favorites_state.last_ui_verification_profile, "beta")
        self.assertEqual(removed_favorites_state.last_ui_verification_profile, "beta")
