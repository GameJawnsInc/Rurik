#!/usr/bin/env python3
"""Rurik model viewer -- double-click launcher (windowless via pythonw).

Opens `tools/viewer/modelviewer.py`: every model in the owner's `Gw.dat`, textured,
with the skeleton overlay, browsable by file id, content template or content map.
Needs PySide6 (`py -m pip install PySide6`); everything it knows about the archive
comes from `toolkit/mapdata/modelcatalog.py`, which is stdlib and in the suite.
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "tools", "viewer"))


def main():
    try:
        import modelviewer
    except SystemExit as exc:               # modelviewer exits with the PySide6 hint
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror("Rurik model viewer", str(exc))
        return 1
    return modelviewer.main()


if __name__ == "__main__":
    sys.exit(main())
