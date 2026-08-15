r"""Repoint an area row's compass FOOTPRINT rect, out of place. (PLAN A2.)

    python toolkit/clientpatch/footprint.py --map 143 --show
    python toolkit/clientpatch/footprint.py --map 143 --size 64x64 --out <vault>\client-tier3\Gw.exe

WHAT THIS MOVES, AND WHY IT IS THE ONLY LEVER FOR AN AUTHORED MAP'S COMPASS.

`s_missionClientData[map]` carries TWO footprint rectangles, at `+0x48`
(MISSION_MAP_OUTPOST) and `+0x58` (MISSION_MAP_GAME), each four int32 in
terrain cells. The `0x0199` map-type byte picks between them -- which is not a
reading but a MEASUREMENT: rung C3 flipped that byte on map 474, whose two
rects differ, and the compass image changed with a rotation-invariant histogram
distance of 0.915 against a 0.027-0.109 within-arm noise floor, while map 143,
whose two rects are EQUAL, scored 0.000 (`studies/minimap/FINDINGS.md` §6e).

The rect's ORIGIN is added to the crop coordinate (`0x008C2782 add edx, eax`)
before the `>> 9` that picks an atlas tile, so it decides WHICH part of the
continent atlas a map's compass shows. That is the whole reason this file
exists: an authored map served at a borrowed slot inherits the DONOR's origin
and therefore the donor's picture.

**WHAT THIS FILE DOES NOT CLAIM.** PLAN A2 predicts that making the rect's SIZE
equal our authored dims "makes the compass crop that size". That is NOT
established, and the code disagrees with it: the crop clamps against
`[CompassMap+0x50..0x5c]`, which is latched from the LOADED MAP FILE's own cell
dims (`0x008C28D0`, §6c), not from this rect. So the size here is very likely
inert for the crop window and the ORIGIN is the load-bearing half. The tool
writes whatever rect it is told to and prints both, so the experiment can
settle it; do not let the flag's existence imply the prediction was confirmed.

THREE CONSTRAINTS, the same ones `reskin.py`'s four tables earned:

  * **Located structurally, never by address.** `consttable.table_for(pe,
    "s_missionClientData")` finds the table by its own anchor and stride; a
    hardcoded `0x0056CE38` would be wrong on the next build and would still
    write something.
  * **Out of place.** Never the input, never `C:\gw`, never a checkout of this
    repo. A patched client is a derived ArenaNet artifact.
  * **Containment plus read-back.** Exactly the 16 or 32 bytes intended may
    differ, checked byte-for-byte against the source, and the output is REOPENED
    and re-located from scratch to confirm the new rect reads back. `test_reskin.py`
    earned that second half: its first version asserted "4 bytes changed" when
    only two had moved, and passed.

Standard library plus `pefile` only through `consttable`/`maprows`, which the
2026-08-06 carve-out already covers for read-only client analysis; this file
adds no new dependency.
"""

from __future__ import annotations

import argparse
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
sys.path.insert(0, os.path.dirname(HERE))

import consttable                                             # noqa: E402
import maprows                                                # noqa: E402
import vaultpath                                              # noqa: E402

SYMBOL = "s_missionClientData"
OFF_A = 0x48          # MISSION_MAP_OUTPOST footprint, four int32 cells
OFF_B = 0x58          # MISSION_MAP_GAME footprint
RECTS = {"A": OFF_A, "B": OFF_B}
LIVE_INSTALL = os.path.normcase(r"C:\gw")


def working_tree_roots():
    """Every checkout of this repo, so none of them can be written into."""
    roots = set()
    here = os.path.abspath(HERE)
    while True:
        if os.path.isdir(os.path.join(here, ".git")) or os.path.isfile(
                os.path.join(here, ".git")):
            roots.add(os.path.normcase(here))
            break
        nxt = os.path.dirname(here)
        if nxt == here:
            break
        here = nxt
    return roots


def refuse_bad_output(src, out):
    """Out of place, outside C:\\gw, and outside every checkout of this repo."""
    out_abs = os.path.normcase(os.path.abspath(out))
    if out_abs == os.path.normcase(os.path.abspath(src)):
        raise SystemExit(
            "--out is the input. This tool never patches in place: the "
            "pristine copy is the only reference for every future scan.")
    if out_abs == LIVE_INSTALL or out_abs.startswith(LIVE_INSTALL + os.sep):
        raise SystemExit(
            f"Refusing to write into the owner's install at {LIVE_INSTALL}. "
            f"That copy is read-only to this project, always.")
    try:
        vault = os.path.normcase(os.path.abspath(vaultpath.vault_root()))
        if out_abs == vault or out_abs.startswith(vault + os.sep):
            return
    except SystemExit:
        pass
    for root in working_tree_roots():
        if out_abs == root or out_abs.startswith(root + os.sep):
            raise SystemExit(
                f"Refusing to write a patched client into a checkout of this "
                f"repository ({root}). Write it under the vault instead.")


def locate(pe):
    """(file_offset_of_row_0, stride, count) for the area table.

    Structural: `consttable` finds the table by anchor and stride and refuses
    when they disagree.

    `Table.base` IS ALREADY A FILE OFFSET -- `Table.record` indexes `pe.data`
    with it directly. The first version of this function treated it as a VA and
    ran it through `rva_to_off`, which double-converted and pointed 0x400B90
    bytes short; every rect it printed was noise, and the CONTAINMENT check
    could not catch it because containment only asks whether the bytes that
    moved were inside the range it was told to write -- not whether the range
    was the right one. `sane_rect` below is what makes a wrong base fail loudly.
    """
    t = consttable.table_for(pe, SYMBOL)
    if t.base + t.count * t.stride > len(pe.data):
        raise SystemExit(f"{SYMBOL} at 0x{t.base:X} + {t.count}x{t.stride} runs "
                         f"past the end of the file ({len(pe.data)} bytes).")
    return t.base, t.stride, t.count


# Continent grids top out at 2048 cells wide (rung S5's four 512-tile worlds),
# so a real footprint is small, non-negative and properly ordered. A rect that
# fails this is not a strange map -- it is a wrong base offset, which is the one
# failure that looks like data.
CELL_MAX = 1 << 16


def sane_rect(r):
    return (all(-CELL_MAX < v < CELL_MAX for v in r)
            and r[2] > r[0] and r[3] > r[1])


def read_rect(data, base_off, stride, row, which):
    o = base_off + row * stride + RECTS[which]
    return struct.unpack_from("<4i", data, o), o


def patch(data, base_off, stride, row, rect, which_rects):
    """Return (new_bytes, [(which, offset, old, new)]). Same length, always."""
    out = bytearray(data)
    log = []
    for which in which_rects:
        old, o = read_rect(data, base_off, stride, row, which)
        struct.pack_into("<4i", out, o, *rect)
        log.append((which, o, old, tuple(rect)))
    return bytes(out), log


def parse_rect(args, cur):
    """The rect to write: --rect wins, else --size keeps the current origin."""
    if args.rect:
        parts = [int(v, 0) for v in args.rect.replace(",", " ").split()]
        if len(parts) != 4:
            raise SystemExit("--rect wants four numbers: x0 y0 x1 y1")
        return tuple(parts)
    if args.size:
        try:
            w, h = (int(v, 0) for v in args.size.lower().split("x"))
        except ValueError:
            raise SystemExit("--size wants WxH, e.g. 64x64")
        return (cur[0], cur[1], cur[0] + w, cur[1] + h)
    raise SystemExit("give --rect or --size (or --show to read only)")


def main(argv=None):
    ap = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--exe", help="client to read; defaults to the pinned build")
    ap.add_argument("--map", type=lambda s: int(s, 0), required=True,
                    help="area row / map id whose footprint to move")
    ap.add_argument("--show", action="store_true",
                    help="print both rects and write nothing")
    ap.add_argument("--rect", help="explicit 'x0 y0 x1 y1' in terrain cells")
    ap.add_argument("--size", help="WxH in cells, keeping the current origin")
    ap.add_argument("--which", default="AB", help="which rects to write: A, B or AB")
    ap.add_argument("--out", help="where to write the patched copy (out of place)")
    a = ap.parse_args(argv)

    exe = a.exe
    if not exe:
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), "clientscan"))
        import pinned
        exe = pinned.find()[0]
    pe = maprows.PE(exe)
    print(f"client: {exe}")
    base_off, stride, count = locate(pe)
    print(f"{SYMBOL}: {count} rows, stride {stride}, row 0 at file offset "
          f"0x{base_off:X} (located structurally)")
    if not 0 <= a.map < count:
        raise SystemExit(f"map {a.map} outside 0..{count - 1}")

    bad = []
    for which in ("A", "B"):
        cur, off = read_rect(pe.data, base_off, stride, a.map, which)
        ok = sane_rect(cur)
        if not ok:
            bad.append(which)
        print(f"  {which} (+0x{RECTS[which]:02X}) at 0x{off:X}: {cur}"
              f"  size {cur[2] - cur[0]} x {cur[3] - cur[1]}"
              f"{'' if ok else '   <-- NOT A PLAUSIBLE RECT'}")
    if bad:
        raise SystemExit(
            f"REFUSING: rect(s) {bad} do not look like terrain-cell rectangles. "
            f"A real footprint is small, non-negative and ordered. This is what "
            f"a WRONG BASE OFFSET looks like, and it is the failure that reads "
            f"as data -- do not patch through it.")
    if a.show:
        return 0

    which_rects = [c for c in a.which.upper() if c in RECTS]
    if not which_rects:
        raise SystemExit("--which wants A, B or AB")
    cur, _ = read_rect(pe.data, base_off, stride, a.map, which_rects[0])
    rect = parse_rect(a, cur)
    if rect[2] <= rect[0] or rect[3] <= rect[1]:
        raise SystemExit(f"rect {rect} is empty or inverted; the crop would "
                         f"degenerate and every strip would take the fallback.")
    if not a.out:
        raise SystemExit("--out is required to write (or pass --show)")
    refuse_bad_output(exe, a.out)

    new, log = patch(pe.data, base_off, stride, a.map, rect, which_rects)

    # CONTAINMENT: exactly the bytes we meant, and no others in the whole image.
    changed = [i for i in range(len(new)) if new[i] != pe.data[i]]
    intended = set()
    for _which, off, _old, _newr in log:
        intended.update(range(off, off + 16))
    stray = [i for i in changed if i not in intended]
    if stray:
        raise SystemExit(f"REFUSING: {len(stray)} byte(s) changed outside the "
                         f"intended rect(s), first at 0x{stray[0]:X}.")
    if len(new) != len(pe.data):
        raise SystemExit("REFUSING: output length differs from input.")

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(new)

    # READ-BACK: reopen and RE-LOCATE from scratch. Trusting the buffer we just
    # wrote would test nothing -- the point is that the patched file still
    # locates structurally and reads back the intended rect.
    pe2 = maprows.PE(a.out)
    base2, stride2, count2 = locate(pe2)
    if (base2, stride2, count2) != (base_off, stride, count):
        raise SystemExit("REFUSING: the patched copy no longer locates the "
                         "table the same way; the edit moved something it "
                         "should not have.")
    print(f"\nwrote {a.out}")
    print(f"  {len(changed)} byte(s) changed, all inside the intended rect(s)")
    for which, off, old, newr in log:
        back, _ = read_rect(pe2.data, base2, stride2, a.map, which)
        ok = "OK" if back == newr else f"MISMATCH (read back {back})"
        print(f"  {which} at 0x{off:X}: {old} -> {newr}  [{ok}]")
        if back != newr:
            raise SystemExit("read-back failed")
    print("\nNOT VERIFIED HERE: that the CLIENT accepts it. This tool proves "
          "the bytes are where they should be, nothing more -- the compass is "
          "the instrument, and the run is the measurement.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
