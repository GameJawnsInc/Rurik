r"""Watch the client's own morale value change, in its own memory.

    python toolkit/clientscan/moralestore.py --find 77          # locate, then watch
    python toolkit/clientscan/moralestore.py --find 77 --seconds 140

THE QUESTION (MORALE-Q7, studies/morale/FINDINGS.md). `--probe morale` measured
what reaches the SCREEN: `0x009C [agent, percent]` draws the death-penalty
indicator and `0x00EE [attr 10, delta]` draws nothing at all. That is not the
same claim as "the delta does nothing" -- a message can update a stored value
and never repaint it, and the corner was the only readout that run had. This
reads the store directly, so the two readings separate.

NOBODY'S OFFSETS ARE USED HERE, and that is the point rather than an accident.
We do not need to know where morale lives, because we are the ones who put the
value there: the probe sets the attribute store to a distinctive number through
`0x00E9`, this scans the client's committed memory for every dword holding it,
and then WATCHES all of them. The probe then sets two more distinct values, and
the addresses whose history tracks that sequence are the store -- everything
else is a coincidence that fails on the second or third step. It is the same
argument the FFNA chunk walk makes: a check the artifact can refute.

    step 1  0x00E9 field 10 = 77   ->  scan finds every dword == 77
    step 2  0x00E9 field 10 = 88   ->  candidates that did not follow are out
    step 3  0x00E9 field 10 = 66   ->  and again; three in a row is a store
    step 4  0x00EE [10, -13]       ->  THE QUESTION: does it read 53 or stay 66?
    step 5  0x009C [player, 41]    ->  the OTHER store, per-agent rather than
                                       per-player; does it live somewhere else?
    step 6  0x00EE [10, +7]        ->  the positive direction too

Read-only by construction: `keytap.open_read` asks for PROCESS_VM_READ and
never PROCESS_VM_WRITE, so this module cannot modify the client even by mistake.
Windows, ctypes, standard library only.

Pair it with the probe on the other side of the loopback:

    python toolkit/harness/session.py --keep-open --hold 130 --shots 0 \
        --game-args "--probe morale_store --map 146"
"""
import argparse
import ctypes
import os
import struct
import subprocess
import sys
import time
from ctypes import wintypes

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "harness"))
import keytap  # noqa: E402

MEM_COMMIT = 0x1000
MEM_PRIVATE = 0x20000
# Readable and writable: a value the server sets has to live somewhere the
# client writes. Excluding the read-only pages drops the image's constants,
# which cannot be a mutable store and are most of the false positives.
WRITABLE = (0x04, 0x08, 0x40, 0x80)     # PAGE_READWRITE, WRITECOPY, EXECUTE_*
# High enough for a 64-bit target as well as the 32-bit client, because the
# POSITIVE CONTROL is a 64-bit python process and a ceiling of 0x7FFF0000 would
# have made the scanner unable to see it -- a filter that cannot see the thing
# it is being tested with proves nothing. The walk ends when VirtualQueryEx
# refuses, which for a WOW64 target is just past 2 GB anyway.
USER_SPACE_END = 0x7FFFFFFF0000


class MBI(ctypes.Structure):
    _fields_ = [("BaseAddress", ctypes.c_void_p),
                ("AllocationBase", ctypes.c_void_p),
                ("AllocationProtect", wintypes.DWORD),
                ("RegionSize", ctypes.c_size_t),
                ("State", wintypes.DWORD),
                ("Protect", wintypes.DWORD),
                ("Type", wintypes.DWORD)]


def find_pid(image="Gw.exe"):
    out = subprocess.run(["tasklist", "/FI", f"IMAGENAME eq {image}",
                          "/FO", "CSV", "/NH"],
                         capture_output=True, text=True).stdout
    for line in out.splitlines():
        parts = [p.strip('" ') for p in line.split('","')]
        if len(parts) >= 2 and parts[0].lower() == image.lower():
            return int(parts[1])
    return None


def scan_u32(pid, value):
    """Every 4-byte-aligned address in `pid` holding `value`, plus bytes scanned.

    `bytes.find` does the searching, so this is a C-speed sweep over each
    region rather than a Python loop over dwords -- the difference between a
    scan that finishes inside one probe step and one that does not.
    """
    needle = struct.pack("<I", value & 0xFFFFFFFF)
    h = keytap.open_read(pid)
    k32 = ctypes.windll.kernel32
    mbi = MBI()
    hits, scanned, addr = [], 0, 0
    try:
        while addr < USER_SPACE_END:
            if not k32.VirtualQueryEx(h, ctypes.c_void_p(addr),
                                      ctypes.byref(mbi), ctypes.sizeof(mbi)):
                break
            base = mbi.BaseAddress or 0
            size = mbi.RegionSize or 0
            if (mbi.State == MEM_COMMIT and mbi.Protect in WRITABLE
                    and 0 < size <= 256 * 1024 * 1024):
                buf = keytap.read_handle(h, base, size)
                if buf:
                    scanned += len(buf)
                    off = buf.find(needle)
                    while off != -1:
                        if off % 4 == 0:
                            hits.append(base + off)
                        off = buf.find(needle, off + 1)
            addr = base + size if size else addr + 0x1000
    finally:
        k32.CloseHandle(h)
    return hits, scanned


def watch(pid, addresses, seconds, period=0.5, context=0):
    """Poll `addresses`, returning {address: [(t, value), ...]} of CHANGES only.

    The first sample of every address is recorded, so a history of length 1 is
    "never moved" and is exactly what a coincidence looks like.
    """
    h = keytap.open_read(pid)
    hist = {}
    t0 = time.time()
    try:
        while time.time() - t0 < seconds:
            now = time.time() - t0
            for a in addresses:
                raw = keytap.read_handle(h, a, 4)
                if raw is None:
                    continue
                (v,) = struct.unpack("<I", raw)
                seq = hist.setdefault(a, [])
                if not seq or seq[-1][1] != v:
                    seq.append((now, v))
            time.sleep(period)
    finally:
        ctypes.windll.kernel32.CloseHandle(h)
    if context:
        pass
    return hist


def neighbourhood(pid, address, span=0x20):
    """The dwords either side of `address` -- the store's own shape, if any."""
    raw = keytap.read_at(pid, address - span, span * 2 + 4)
    if not raw:
        return []
    return [(address - span + i, struct.unpack_from("<I", raw, i)[0])
            for i in range(0, len(raw) - 3, 4)]


def watch_window(pid, anchors, span, seconds, period=0.5):
    """Poll a window of dwords around each anchor; return per-offset histories.

    {anchor: {offset: [(t, value), ...]}} with a sample recorded only when the
    value CHANGES, so an offset with one entry never moved.
    """
    h = keytap.open_read(pid)
    hist = {a: {} for a in anchors}
    size = span * 2 + 4
    t0 = time.time()
    try:
        while time.time() - t0 < seconds:
            now = time.time() - t0
            for a in anchors:
                raw = keytap.read_handle(h, a - span, size)
                if raw is None:
                    continue
                for i in range(0, size - 3, 4):
                    (v,) = struct.unpack_from("<I", raw, i)
                    seq = hist[a].setdefault(i - span, [])
                    if not seq or seq[-1][1] != v:
                        seq.append((now, v))
            time.sleep(period)
    finally:
        ctypes.windll.kernel32.CloseHandle(h)
    return hist


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--pid", type=int, default=None,
                    help="scan this process instead of the running Gw.exe. "
                         "Exists for the POSITIVE CONTROL: point it at a "
                         "process holding a known value and confirm this "
                         "scanner finds it, because a null from a filter "
                         "nobody has proven can see anything is not evidence.")
    ap.add_argument("--module", default="Gw.exe",
                    help="module whose runtime base is printed, for RVAs")
    ap.add_argument("--anchor", type=int, default=424242,
                    help="a value the probe holds CONSTANT through every step "
                         "-- the experience field. Locating on a constant is "
                         "what makes this immune to the race that broke the "
                         "first attempt: a scan for the value under test can "
                         "run before the probe sets it and lock onto hundreds "
                         "of coincidences, and no later step can rescue it.")
    ap.add_argument("--span", type=lambda v: int(v, 0), default=0x80,
                    help="bytes either side of the anchor to watch (0x80)")
    ap.add_argument("--seconds", type=float, default=100.0,
                    help="how long to watch once the anchor is found")
    ap.add_argument("--period", type=float, default=0.5,
                    help="poll interval, seconds")
    ap.add_argument("--tries", type=int, default=120,
                    help="rescans while waiting for the anchor to appear")
    ap.add_argument("--wait-for-client", type=float, default=0.0,
                    help="seconds to wait for Gw.exe to exist before giving up")
    ap.add_argument("--max-anchors", type=int, default=64,
                    help="refuse to watch more windows than this")
    args = ap.parse_args(argv)

    pid = args.pid
    if not pid:
        deadline = time.time() + args.wait_for_client
        while True:
            pid = find_pid()
            if pid or time.time() > deadline:
                break
            time.sleep(1.0)
    if not pid:
        raise SystemExit("[FAIL] no Gw.exe running -- start the session first")
    try:
        base, path = keytap.module_info(pid, args.module)
    except Exception:                          # noqa: BLE001
        base, path = 0, "(module base unavailable)"
    print(f"pid {pid}, {args.module} at 0x{base:08X}\n  {path}", flush=True)

    anchors = []
    for attempt in range(1, args.tries + 1):
        anchors, scanned = scan_u32(pid, args.anchor)
        print(f"  scan {attempt} for anchor {args.anchor}: {len(anchors):,} "
              f"hit(s) in {scanned / 1e6:.0f} MB", flush=True)
        if anchors:
            break
        time.sleep(1.0)
    if not anchors:
        raise SystemExit(f"[FAIL] the anchor {args.anchor} never appeared. The "
                         f"client does not store it, or the probe's first step "
                         f"never landed.")
    if len(anchors) > args.max_anchors:
        raise SystemExit(f"[FAIL] {len(anchors)} anchors is too many to watch; "
                         f"pick a rarer constant")

    print(f"\nwatching +-0x{args.span:X} around {len(anchors)} anchor(s) for "
          f"{args.seconds:.0f}s at {1 / args.period:.0f} Hz", flush=True)
    hist = watch_window(pid, anchors, args.span, args.seconds, args.period)

    for a, offsets in hist.items():
        movers = {o: h for o, h in offsets.items() if len(h) > 1}
        print(f"\n=== anchor 0x{a:08X} "
              + (f"(Gw.exe+0x{a - base:X}) " if base and 0 < a - base < 0x2000000
                 else "")
              + f"-- {len(movers)} offset(s) moved ===")
        for o in sorted(movers):
            trail = "  ".join(f"t+{t:5.1f}={v}" for t, v in movers[o])
            print(f"  {o:+5d}  {trail}")
        if not movers:
            print("  nothing in this window ever changed")

    print("\nfinal window dump (the block's own shape):")
    for a in anchors[:4]:
        raw = keytap.read_at(pid, a - args.span, args.span * 2 + 4)
        if not raw:
            print(f"  0x{a:08X}: unreadable now (client gone?)")
            continue
        print(f"  around 0x{a:08X}:")
        row = []
        for i in range(0, len(raw) - 3, 4):
            (v,) = struct.unpack_from("<I", raw, i)
            row.append(f"{i - args.span:+d}:{v}")
            if len(row) == 6:
                print("      " + "  ".join(row))
                row = []
        if row:
            print("      " + "  ".join(row))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
