#!/usr/bin/env python3
"""
Root-level launcher for PROJECT CONTROL.

Allows:
    python .\\pc.py gui
    python .\\pc.py tui
    python .\\pc.py scan

Repo-local Windows shims:
    .\\pc.ps1 gui
    .\\pc.cmd tui
"""

from __future__ import annotations

import sys


def main() -> None:
    try:
        from project_control.pc import main as project_control_main
    except ModuleNotFoundError as exc:
        print("PROJECT CONTROL could not start because a Python dependency is missing.")
        print(f"Missing module: {exc.name}")
        print("")
        print("Launch modes from this repository:")
        if sys.platform == "win32":
            print("  Repo-local: .\\pc.ps1 tui")
            print("  Repo-local: .\\pc.cmd gui")
            print("  Python:     python .\\pc.py tui")
        else:
            print("  Python:     python ./pc.py tui")
            print("  Python:     python ./pc.py gui")
        print("")
        print("If you want the global 'pc' command, install PROJECT CONTROL first:")
        print("  End users:  pipx install .")
        print("  Developers: python -m pip install -e .")
        raise SystemExit(1) from exc

    project_control_main()


if __name__ == "__main__":
    main()
