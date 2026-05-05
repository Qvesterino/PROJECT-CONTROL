"""Focused parser tests for the first-class UI verification command."""

from __future__ import annotations

import unittest

from project_control.pc import build_parser


class UIVerifyParserTests(unittest.TestCase):
    def test_parser_preserves_ui_menu_fallback(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["ui"])

        self.assertEqual(args.command, "ui")
        self.assertIsNone(args.ui_cmd)

    def test_parser_exposes_ui_verify_command(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["ui", "verify", "--html"])

        self.assertEqual(args.command, "ui")
        self.assertEqual(args.ui_cmd, "verify")
        self.assertTrue(args.html)
        self.assertTrue(args.headless)

    def test_parser_exposes_ui_verify_profile_selection(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["ui", "verify", "--profile", "demo"])

        self.assertEqual(args.command, "ui")
        self.assertEqual(args.ui_cmd, "verify")
        self.assertEqual(args.profile, "demo")

    def test_parser_exposes_ui_verify_list_profiles(self) -> None:
        parser = build_parser()

        args = parser.parse_args(["ui", "verify", "--list-profiles", "--json"])

        self.assertEqual(args.command, "ui")
        self.assertEqual(args.ui_cmd, "verify")
        self.assertTrue(args.list_profiles)
        self.assertTrue(args.json)


if __name__ == "__main__":
    unittest.main()