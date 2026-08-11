"""Read the full text out of Guild Wars' fatal-error dialog.

The dialog shows a scrolled view of a much longer report. Screenshotting it gives
only the visible slice -- which for three runs in a row was the tail of Gw.log,
telling us nothing about the actual fault. The top of that same control carries
the exception or assertion record, including the client source file and line that
rejected our data. WM_GETTEXT returns the whole buffer regardless of scroll.

Read-only by construction: it enumerates windows and asks for their text. It never
clicks. The dialog's default action is "Send report to ArenaNet", which would
upload a crash dump from a patched client to the vendor -- exactly what the
owner's standing rule forbids -- so nothing here is allowed to press a button.

READ THE TRACE REBASED, OR IT DECODES TO GARBAGE THAT LOOKS LIKE CODE. Every
address in the dump -- `Pc:`, `Rt:`, the DllList, the `*--> Code <--*` block -- is
a RUNTIME address, and the client is loaded wherever ASLR put it. The dump states
the base twice: `BaseAddr:` in the header and the first `DllList` row. Build
38797's PE `ImageBase` is 0x00400000, so a dump reporting `BaseAddr: 007A0000`
needs **0x3A0000 subtracted** before anything in it can be looked up in the file
or handed to `codescan.py --dis`:

    file_va = trace_addr - BaseAddr + 0x00400000

The failure mode is what makes this worth a docstring rather than a comment. Feeding
`codescan.py --dis` an un-rebased address does not error and does not return
nothing -- it disassembles whatever bytes are there and prints confident-looking
instructions (`int1`, `aas`, `xchg ebp, eax`, immediates like 0x9895a912). On
2026-08-11 that cost a read of four crash frames before the base was noticed, and
the rebased addresses then landed exactly on documented ground: `0x00BB829D` became
`0x0081829D`, which is the instruction after a five-byte `call rel32` at
`0x00818298`, inside the agent-property dispatcher this repo had already written
about at `0x0081823C`. Landing on known code is also the CHECK
that the rebase is right -- do that before trusting a frame.

    python toolkit/harness/read_error_dialog.py            # wait for it, then dump
    python toolkit/harness/read_error_dialog.py --once     # dump now or exit 1
"""

import argparse
import ctypes
import os
import sys
import time
from ctypes import wintypes

user32 = ctypes.WinDLL("user32", use_last_error=True)

WM_GETTEXT = 0x000D
WM_GETTEXTLENGTH = 0x000E

# argtypes are not optional: without them ctypes truncates 64-bit HWNDs to int,
# and every call silently operates on a corrupt handle. That cost a whole round of
# "empty screenshots that did not error" earlier in this project.
user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
user32.IsWindowVisible.argtypes = [wintypes.HWND]
user32.SendMessageW.argtypes = [wintypes.HWND, ctypes.c_uint, ctypes.c_size_t, ctypes.c_void_p]
user32.SendMessageW.restype = ctypes.c_ssize_t

WNDENUMPROC = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)


def _pid_of(hwnd):
    pid = wintypes.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return pid.value


def _class_of(hwnd):
    buf = ctypes.create_unicode_buffer(256)
    user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _text_of(hwnd):
    """WM_GETTEXT rather than GetWindowText: the latter returns nothing for
    controls in another process, which is every control we care about here."""
    n = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, None)
    if n <= 0:
        return ""
    buf = ctypes.create_unicode_buffer(n + 1)
    user32.SendMessageW(hwnd, WM_GETTEXT, n + 1, ctypes.cast(buf, ctypes.c_void_p))
    return buf.value


def _children(parent):
    out = []
    user32.EnumChildWindows(parent, WNDENUMPROC(lambda h, _: (out.append(h), True)[1]), 0)
    return out


def gw_pids():
    import subprocess
    try:
        r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq Gw.exe", "/FO", "CSV", "/NH"],
                           capture_output=True, text=True, timeout=15)
    except Exception:
        return []
    pids = []
    for line in r.stdout.splitlines():
        parts = [p.strip('"') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == "gw.exe":
            try:
                pids.append(int(parts[1]))
            except ValueError:
                pass
    return pids


def dump(pids):
    """Return every non-empty control string belonging to those pids."""
    tops = []
    user32.EnumWindows(WNDENUMPROC(lambda h, _: (tops.append(h), True)[1]), 0)

    found = []
    for hwnd in tops:
        if _pid_of(hwnd) not in pids or not user32.IsWindowVisible(hwnd):
            continue
        title = _text_of(hwnd)
        blocks = []
        for child in _children(hwnd):
            t = _text_of(child)
            if t.strip():
                blocks.append((_class_of(child), t))
        if blocks:
            found.append((hwnd, title, blocks))
    return found


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="dump immediately instead of waiting for a dialog")
    ap.add_argument("--timeout", type=float, default=120.0)
    ap.add_argument("--out", default=None, help="also write the dump here")
    args = ap.parse_args()

    deadline = time.time() + (0 if args.once else args.timeout)
    while True:
        pids = gw_pids()
        found = dump(pids) if pids else []
        # The main game window has no child controls worth reading; the dialog is
        # full of them. More than one block is the signal that the dialog is up.
        interesting = [f for f in found if len(f[2]) >= 2]
        if interesting or time.time() >= deadline:
            break
        time.sleep(0.5)

    if not interesting:
        print("no error dialog found", file=sys.stderr)
        return 1

    lines = []
    for hwnd, title, blocks in interesting:
        lines.append(f"=== window 0x{hwnd:X}  title={title!r}")
        for cls, text in blocks:
            lines.append(f"--- control class={cls}  ({len(text)} chars)")
            lines.append(text)
    out = "\n".join(lines)
    # The console here is cp1252; the report can carry characters it cannot encode.
    print(out.encode("ascii", "replace").decode("ascii"))
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(f"\nwritten: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
