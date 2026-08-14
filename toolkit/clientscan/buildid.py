"""The client's own build number, read out of a `Gw.exe`.

    python toolkit/clientscan/buildid.py                  # the pinned client
    python toolkit/clientscan/buildid.py --exe <path>
    python toolkit/clientscan/buildid.py --all            # every vaulted build

WHY. `studies/crossbuild/PLAN.md` §8 recorded this as NOT FOUND: nothing in this
repo derived a build number from a binary. `pinned.BUILD = 38797` was
hand-written, and the consequence was small and absurd -- **the older vaulted
build's number appeared nowhere in the tree**, so half the corpus could not
satisfy the rule `HANDOFF.md`:237 has held since day one, "record the build id in
every capture manifest".

THE OBVIOUS PLACE DOES NOT WORK, and it was refuted before this was written.
`snapshot_client.py`:80-92 already reads the PE version resource, and both
vaulted builds report `FileVersion '1, 0, 0, 1'` -- identical to each other and
to four sibling DLLs that never changed. The version resource is not a build
discriminator and never was.

WHERE IT ACTUALLY LIVES. The client compiles its build number as a whole
function:

    cc                    (int3 pad)
    b8 8d 97 00 00        mov eax, 38797
    c3                    ret
    cc cc cc              (int3 pad)

MEASURED on build 38797: that dword occurs exactly ONCE in `.text`, at
0x004729E1, and the function around it at 0x004729E0 has 16 callers -- the build
is consulted all over the client, which is why it is a getter rather than an
inline constant.

HOW THIS FINDS IT, and what the filter is doing. The shape alone is common: 54
functions on 38797 and 56 on the older build are `mov eax, <imm32>; ret`, which
is what MSVC emits for any constant getter. What separates the build number from
the other 53 is the VALUE -- Guild Wars build numbers are five digits in the
30000s (37600 pre-Reforged per gw-preservation, 38688 and 38771 upstream, 38797
ours), so a candidate must land in `BUILD_MIN..BUILD_MAX`. **MEASURED: exactly
one candidate on each build**, and this REFUSES on none or several rather than
picking one.

The range is a stated assumption and it is the weakest link here; it is also
checkable, because the number it produces has an independent witness. For the
pinned build the client tells us the same number over the NETWORK -- `authsrv.py`
records it from the VERSION frame and the live `User-Agent: Gw/38797.0 (Win32)`
carries it in the clear -- so a value derived from the bytes and a value observed
on the wire agree from two directions that share nothing. `test_buildid.py` §3
asserts that agreement.

CALLER COUNT IS CORROBORATION, NOT A FILTER, and the difference was measured: on
38797 the build getter is the SECOND most-called of the 54 candidates and on the
older build it is the first, so ranking by callers would have picked the wrong
function on one of the two. It is reported because a build getter with one caller
would be worth a second look, not used to choose.

STANDARD LIBRARY ONLY. READ ONLY: opens the exe for reading and nothing else.
"""
import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from gwpe import PE                                          # noqa: E402
import pinned                                                # noqa: E402

find_exe = pinned.find

# A Guild Wars build number. 37600 is the pre-Reforged client gw-preservation
# pins, 38688 the highest Headquarter tracks, 38771 the one ldufr dumped, 38797
# ours: five digits, all in the 30000s. Deliberately wide at the top so a client
# several years newer than this comment still reads, and hard-floored well above
# the small constants (0, 1, 2, flags) that dominate the other getters.
BUILD_MIN, BUILD_MAX = 30_000, 99_999

# `mov eax, imm32` / `ret`, with MSVC's int3 padding on both sides. The padding
# is what makes it a whole FUNCTION rather than the tail of a longer one.
PAD, MOV_EAX, RET = 0xCC, 0xB8, 0xC3
GETTER_LEN = 6                                   # b8 imm32 c3


class NoBuildId(SystemExit):
    """The build number could not be read. Never a guess, never a default."""


def candidates(pe):
    """[(va, value, callers)] for every `mov eax, imm32; ret` function in .text.

    Unfiltered -- the caller decides. Returned with caller counts because a
    surprising answer is diagnosed by looking at what else was on the list.
    """
    sec = pe.section(".text")
    if sec is None:
        raise NoBuildId("no .text section")
    lo, hi = sec["rawptr"], sec["rawptr"] + sec["rawsize"]
    tlo = pe.image_base + sec["vaddr"]
    d = pe.data

    found, i = [], lo
    while True:
        i = d.find(bytes((PAD, MOV_EAX)), i, hi - GETTER_LEN - 2)
        if i == -1:
            break
        if d[i + GETTER_LEN] == RET and d[i + GETTER_LEN + 1] == PAD:
            found.append((tlo + (i + 1 - lo),
                          int.from_bytes(d[i + 2:i + 6], "little")))
        i += 1

    counts = {va: 0 for va, _ in found}
    i = lo
    while True:
        i = d.find(b"\xe8", i, hi - 5)
        if i == -1:
            break
        tgt = tlo + (i - lo) + 5 + struct.unpack_from("<i", d, i + 1)[0]
        if tgt in counts:
            counts[tgt] += 1
        i += 1
    return [(va, val, counts[va]) for va, val in found]


def read(path):
    """(build number, VA of its getter, caller count) for one client.

    REFUSES on none and on several rather than choosing -- `studies/crossbuild/`
    `PLAN.md` §7 rule 1. Two candidates in the build range would mean the value
    is no longer identified by its range alone, which is a finding about the
    client and not something to resolve by taking the first.
    """
    try:
        pe = PE(path)
    except Exception as exc:                                 # noqa: BLE001
        # Anything that is not a readable PE is a refusal, not a traceback: the
        # caller asked which build a client is, and "that is not a client" is an
        # answer to give in the same shape as the others.
        raise NoBuildId(f"{path}: not a readable PE image: "
                        f"{type(exc).__name__}: {exc}")
    all_c = candidates(pe)
    hits = [c for c in all_c if BUILD_MIN <= c[1] <= BUILD_MAX]
    if not hits:
        raise NoBuildId(
            f"{path}: no build number found.\n"
            f"  Looked for an int3-padded `mov eax, imm32; ret` whose value is in "
            f"{BUILD_MIN}..{BUILD_MAX};\n"
            f"  {len(all_c)} function(s) of that shape exist and none qualifies. "
            f"Either the client stopped\n"
            f"  compiling the build as a getter, or it left the range this module "
            f"assumes -- see its\n"
            f"  docstring, where that range is the stated weak link.")
    if len(hits) > 1:
        listed = ", ".join(f"{v} at 0x{va:08X}" for va, v, _ in hits)
        raise NoBuildId(
            f"{path}: {len(hits)} candidate build numbers, expected 1: {listed}.\n"
            f"  Refusing to guess. The range no longer identifies it on its own.")
    va, number, callers = hits[0]
    return number, va, callers


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--exe", help="client to read; defaults to the pinned one")
    ap.add_argument("--all", action="store_true",
                    help="every build in pinned.BUILDS")
    ap.add_argument("--candidates", action="store_true",
                    help="list every getter of the shape, not just the answer")
    a = ap.parse_args(argv)

    if a.all:
        rc = 0
        for b in pinned.BUILDS:
            try:
                p, _why = pinned.find(b.stamp)
            except SystemExit as exc:
                print(f"{b.stamp}: {exc}")
                rc = 1
                continue
            try:
                n, va, callers = read(p)
            except NoBuildId as exc:
                print(f"{b.stamp}: {exc}")
                rc = 2
                continue
            recorded = "" if b.number is None else f", recorded {b.number}"
            agree = b.number is None or b.number == n
            print(f"{b.stamp}: build {n}  (getter 0x{va:08X}, {callers} "
                  f"callers{recorded}){'' if agree else '   <- DISAGREES'}")
            if not agree:
                rc = 1
        return rc

    exe, why = ((a.exe, "given on the command line") if a.exe else find_exe())
    print(f"client: {exe}\n        ({why})\n")
    if a.candidates:
        for va, val, n in sorted(candidates(PE(exe)), key=lambda c: -c[2]):
            mark = " <- in the build range" if BUILD_MIN <= val <= BUILD_MAX else ""
            print(f"  0x{va:08X}  {n:3d} caller(s)  {val}{mark}")
        return 0
    n, va, callers = read(exe)
    print(f"build {n}, from the getter at 0x{va:08X} ({callers} callers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
