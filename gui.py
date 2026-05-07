#!/usr/bin/env python3
"""
One-command desktop launcher for PROJECT CONTROL.

Allows:
    python .\\gui.py
    .\\pc.ps1 gui
    .\\pc.cmd gui
"""

from __future__ import annotations

import sys

from pc import main as launcher_main


if __name__ == "__main__":
    sys.argv = [sys.argv[0], "gui", *sys.argv[1:]]
    launcher_main()
