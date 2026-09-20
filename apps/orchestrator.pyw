#!/usr/bin/env python3
"""Rurik run orchestrator -- double-click launcher (windowless via pythonw).

Opens `tools/orchestrator/orchestrator.py`: the vertical slice as a practice
sandbox -- pick the character's professions, the heroes and their bars, the
hostile groups and the boss, the skill libraries; then press Launch. Needs
PySide6 (`py -m pip install PySide6`); everything it knows comes from
`toolkit/harness/sandbox.py` (the compiler, stdlib, in the suite),
`toolkit/content.py` and the owner's own archive for the names.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools", "orchestrator"))


def main():
    try:
        import orchestrator
    except SystemExit as exc:               # orchestrator exits with the PySide6 hint
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Rurik run orchestrator", str(exc))
        return 1
    return orchestrator.main()


if __name__ == "__main__":
    sys.exit(main())
