#!/usr/bin/env python3
"""
Root-level launcher for PROJECT CONTROL.

Allows:
    python pc.py gui
    python pc.py ui
    python pc.py scan
"""

from __future__ import annotations


def main() -> None:
    try:
        from project_control.pc import main as project_control_main
    except ModuleNotFoundError as exc:
        print("PROJECT CONTROL could not start because a Python dependency is missing.")
        print(f"Missing module: {exc.name}")
        print("")
        print("From this folder, run:")
        print("  python -m pip install -e .")
        raise SystemExit(1) from exc

    project_control_main()


if __name__ == "__main__":
    main()
