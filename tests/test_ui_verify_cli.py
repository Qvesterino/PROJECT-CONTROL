"""Focused parser tests for the first-class UI verification command."""

from __future__ import annotations

import unittest

from project_control.pc import build_parser


class UIVerifyParserTests(unittest.TestCase):
    def test_parser_preserves_tui_menu_fallback(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui"])

        self.assertEqual(args.command, "tui")
        self.assertIsNone(args.tui_cmd)

    def test_parser_exposes_tui_verify_command(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "verify", "--html"])

        self.assertEqual(args.command, "tui")
        self.assertEqual(args.tui_cmd, "verify")
        self.assertTrue(args.html)
        self.assertTrue(args.headless)

    def test_parser_exposes_tui_verify_profile_selection(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "verify", "--profile", "demo"])

        self.assertEqual(args.command, "tui")
        self.assertEqual(args.tui_cmd, "verify")
        self.assertEqual(args.profile, "demo")

    def test_parser_exposes_tui_verify_list_profiles(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["tui", "verify", "--list-profiles", "--json"])

        self.assertEqual(args.command, "tui")
        self.assertEqual(args.tui_cmd, "verify")
        self.assertTrue(args.list_profiles)
        self.assertTrue(args.json)

    def test_parser_rejects_removed_ui_command(self) -> None:
        parser = build_parser()

        with self.assertRaises(SystemExit):
            parser.parse_args(["ui", "verify", "--profile", "demo"])

    def test_parser_exposes_gui_command(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["gui", "."])

        self.assertEqual(args.command, "gui")
        self.assertEqual(args.project_root, ".")


if __name__ == "__main__":
    unittest.main()
