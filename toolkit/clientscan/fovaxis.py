"""Settle WHICH AXIS the client's field of view spans, from its own memory.

    python toolkit/clientscan/fovaxis.py

FINDINGS section 10 measured the field of view exactly -- 75.000 degrees --
and could not say whether that angle is the vertical, horizontal or diagonal
one. The three readings differ by more than 40 degrees of horizontal field, so
the difference is not cosmetic: it decides what `gwcam.py` frames.

WHY THIS WORKS WITHOUT A SCREENSHOT OR AN INJECTION. Whatever axis the client
means, it must end up building a perspective projection, and a perspective
projection contains the two cotangents

    m00 = cot(horizontal / 2)      m11 = cot(vertical / 2)

whose RATIO is the render aspect. So each reading of "75 degrees" predicts a
DIFFERENT, exactly-computable pair, and the pairs do not overlap:

    if 75 is VERTICAL    m11 = cot(37.5) = 1.30323, m00 = m11 / aspect
    if 75 is HORIZONTAL  m00 = cot(37.5) = 1.30323, m11 = m00 * aspect
    if 75 is DIAGONAL    neither is 1.30323 at all

A search of the live process for those specific floats therefore does not need
to know any struct layout, find any matrix by its shape, or trust our renderer.
It asks one question the client cannot answer ambiguously: which cotangent is
actually in there. An earlier attempt to find the matrix by its SHAPE scanned
399 MB and found nothing; this looks for the VALUES instead, which survives the
matrix being stored transposed, split, or as frustum planes.

THE CONTROL IS BUILT IN, and it is what makes a hit a measurement rather than a
coincidence: a bare float can occur anywhere, so a hit only counts when its
PARTNER is present nearby at the ratio the render aspect demands. A lone
1.30323 with no partner is reported as exactly that and settles nothing.

**DO NOT RUN THIS AT A SQUARE WINDOW.** At aspect 1.0 the horizontal and
vertical readings predict the IDENTICAL pair -- cot(fov/2) twice -- so the test
cannot discriminate at all; and because the partner search below looks in a
window that always contains the found float itself, each reading would
self-confirm off one stored value. The verdict then prints UNSETTLED, which is
honest but wastes the run. Near-square is WORSE than exactly square: at aspect
0.9999 the two predictions are ~2.6e-4 apart, at this file's own tolerance,
where a floating-point difference could tip a false winner instead of failing
loudly. Pick an aspect far from 1.0 -- portrait is ideal, because below 1.0 the
two readings SWAP which cotangent is larger, making the answer a qualitative
flip rather than a fitted number. (Both hazards are measured, not theorised:
FINDINGS section 12, where the run used 0.699 and the predictions sat 0.39
apart.)

Read-only: `ReadProcessMemory` and nothing else. The client must be IN A MAP.
"""

import argparse
import ctypes
import math
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "harness"))

import keytap  # noqa: E402

IMAGE_BASE = 0x00400000
VA_FOV = 0x00C078C4
#: How close a float must be to a predicted cotangent. The predictions differ
#: from each other by whole percent, so this is tight enough to separate them
#: and loose enough for float32 rounding.
TOL = 2e-4


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", ctypes.c_ulong),
                ("RegionSize", ctypes.c_size_t),
                ("State", ctypes.c_ulong),
                ("Protect", ctypes.c_ulong),
                ("Type", ctypes.c_ulong)]


def find_pid(image="Gw.exe"):
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}",
                          "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image.lower():
            return int(parts[1])
    return None


def client_aspect(pid):
    """The render area's aspect, off the client's own window."""
    user32 = ctypes.windll.user32

    class RECT(ctypes.Structure):
        _fields_ = [("l", ctypes.c_long), ("t", ctypes.c_long),
                    ("r", ctypes.c_long), ("b", ctypes.c_long)]

    found = []

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _lp):
        got = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(got))
        if got.value == pid and user32.IsWindowVisible(hwnd):
            r = RECT()
            if user32.GetClientRect(hwnd, ctypes.byref(r)) and r.r > 100:
                found.append((r.r - r.l, r.b - r.t))
        return True

    user32.EnumWindows(cb, None)
    if not found:
        return None, None
    w, h = max(found)
    return (w, h), w / float(h)


def predictions(fov, aspect):
    """The (m00, m11) pair each reading of `fov` demands."""
    cot = lambda a: 1.0 / math.tan(a / 2.0)          # noqa: E731
    out = {}
    out["vertical"] = (cot(fov) / aspect, cot(fov))
    out["horizontal"] = (cot(fov), cot(fov) * aspect)
    diag_v = 2 * math.atan(math.tan(fov / 2) / math.hypot(aspect, 1.0))
    out["diagonal"] = (cot(diag_v) / aspect, cot(diag_v))
    return out


def scan(pid, wanted, span=0x400):
    """Every occurrence of each wanted float, with the floats around it."""
    h = keytap.open_read(pid)
    k32 = ctypes.windll.kernel32
    mbi = MBI()
    addr = 0
    hits = {name: [] for name in wanted}
    scanned = 0
    while addr < 0x7FFF0000:
        if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr), ctypes.byref(mbi),
                                  ctypes.sizeof(mbi)):
            break
        base = mbi.BaseAddress or 0
        size = mbi.RegionSize or 0
        if (mbi.State == 0x1000 and mbi.Protect in (0x02, 0x04, 0x20, 0x40)
                and 0 < size <= 64 * 1024 * 1024):
            buf = keytap.read_at(pid, base, size)
            if buf:
                scanned += len(buf)
                for off in range(0, len(buf) - 4, 4):
                    (f,) = struct.unpack_from("<f", buf, off)
                    for name, (want, _partner) in wanted.items():
                        if abs(f - want) <= TOL:
                            lo = max(0, off - span)
                            hits[name].append(
                                (base + off, buf[lo:off + span], off - lo))
        addr = base + size if size else addr + 0x1000
    return hits, scanned


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--aspect", type=float, default=None,
                    help="override the render aspect (default: the client's "
                         "own window)")
    args = ap.parse_args(argv)

    pid = find_pid()
    if not pid:
        raise SystemExit("[FAIL] no Gw.exe running")
    base = keytap.module_base(pid, "Gw.exe")
    raw = keytap.read_at(pid, base + (VA_FOV - IMAGE_BASE), 4)
    (fov,) = struct.unpack("<f", raw)
    if fov == 0.0:
        raise SystemExit("[FAIL] fov reads 0.0 -- the client is not in a map")
    size, aspect = client_aspect(pid)
    if args.aspect:
        aspect = args.aspect
    if not aspect:
        raise SystemExit("[FAIL] could not read the client's window")
    print(f"[ok] pid {pid}  fov {fov!r} rad = {math.degrees(fov):.3f} deg")
    print(f"[ok] render area {size[0]}x{size[1]}, aspect {aspect:.5f}")

    pred = predictions(fov, aspect)
    print("\nWhat each reading demands:")
    for name, (m00, m11) in pred.items():
        print(f"  {name:11s} m00 = {m00:.6f}   m11 = {m11:.6f}")

    wanted = {name: (m11, m00) for name, (m00, m11) in pred.items()}
    print("\n[ok] scanning for those cotangents ...")
    hits, scanned = scan(pid, wanted)
    print(f"[ok] scanned {scanned/1e6:.0f} MB")

    verdict = {}
    for name, (m00, m11) in pred.items():
        confirmed = []
        for addr, window, at in hits[name]:
            n = len(window) // 4
            floats = struct.unpack_from(f"<{n}f", window, 0)
            # THE CONTROL: the partner must be present nearby, at the ratio the
            # aspect demands. Without it a lone float proves nothing.
            if any(abs(f - m00) <= TOL for f in floats):
                confirmed.append(addr)
        verdict[name] = (len(hits[name]), confirmed)
        print(f"\n  {name:11s} m11={m11:.6f}: {len(hits[name])} bare hit(s), "
              f"{len(confirmed)} WITH the partner m00={m00:.6f} nearby")
        for a in confirmed[:6]:
            print(f"      confirmed pair @ 0x{a:08X}")

    winners = [n for n, (_b, c) in verdict.items() if c]
    print()
    if len(winners) == 1:
        n = winners[0]
        m00, m11 = pred[n]
        print(f"[MEASURED] the field of view is {math.degrees(fov):.3f} deg "
              f"on the {n.upper()} axis")
        print(f"           horizontal {2*math.degrees(math.atan(1/m00)):.3f} "
              f"deg, vertical {2*math.degrees(math.atan(1/m11)):.3f} deg")
    elif not winners:
        print("[UNSETTLED] no reading's cotangent PAIR is present in memory. "
              "The projection is not stored as cotangents anywhere readable -- "
              "this run refutes nothing and settles nothing.")
    else:
        print(f"[UNSETTLED] more than one reading has a confirmed pair "
              f"({winners}); the signatures are not separating.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
