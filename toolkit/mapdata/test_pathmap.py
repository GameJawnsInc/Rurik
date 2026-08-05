"""Check the navmesh reader against real bytes.

The layout under test came from ONE source lineage with no fixture of its own
(see the header of pathmap.py), so these checks are the only thing standing
between "GuildWarsMapBrowser says so" and a server that refuses to let a player
walk where the game allows it.

Three of them can fail for the right reason:

  * Section 2 walks 39 planes of ten sub-records through tag 8 and requires the
    walk to end on the exact final byte. Every element size participates. This
    is the same shape of argument as the chunk-table check in test_archive.py --
    an independent structure that either consumes the block exactly or does not.
  * Section 3 asks the geometry whether it is geometry. Inverted y spans and
    crossed x edges are what a misread struct produces, and the count should be
    zero, not small.
  * Section 5 runs the walk across a sample of the whole map corpus, so a layout
    that happens to fit Kamadan and nothing else is caught.

    python toolkit/mapdata/test_pathmap.py
    python toolkit/mapdata/test_pathmap.py --sample 60
    python toolkit/mapdata/test_pathmap.py --all      # every map, minutes

MEASURED VALUES ARE KAMADAN'S, on the archive our patched client has run. A
different Gw.dat is fine -- the file id is a content key -- but if that map ever
changes shape these numbers are the alarm.
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from archive import Archive, ffna_chunks, file_id_table, DEFAULT_DAT  # noqa: E402
from pathmap import (PathingMap, PATHING_CHUNK, SIGNATURE, VERSION,  # noqa: E402
                     TRAPEZOID_SIZE)

KAMADAN_FILE_ID = 0x345CC
KAMADAN_ROW = 22371
KAMADAN_CHUNK_BYTES = 199130
KAMADAN_PLANES = 39
KAMADAN_TRAPEZOIDS = 1270

# OpenTyria's static spawn for Kamadan. It was never checked against anything
# until this file; section 4 is that check.
KAMADAN_SPAWN = (-9067.0, 13218.0)

MAP_FLAGS = 259
FAILED = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILED.append(label)
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--sample", type=int, default=25,
                    help="how many maps to walk in section 5")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    t0 = time.perf_counter()
    with Archive(args.dat) as ar:
        table = file_id_table(ar)

        # -- 1. the chunk itself ----------------------------------------
        print("\n1. Kamadan's pathing chunk")
        row = table.get(KAMADAN_FILE_ID)
        check(row == KAMADAN_ROW, "file id resolves to the reference row",
              f"0x{KAMADAN_FILE_ID:X} -> {row}")
        entry = next(e for e in ar.entries if e.index == row)
        check(entry.flags == MAP_FLAGS, "the row carries map flags",
              f"flags {entry.flags}")
        data = ar.read(entry)
        blob = None
        for cid, off, size in ffna_chunks(data):
            if cid == PATHING_CHUNK:
                blob = bytes(data[off:off + size])
                break
        check(blob is not None, "map file has a pathing chunk")
        check(len(blob) == KAMADAN_CHUNK_BYTES, "chunk is the measured size",
              f"{len(blob)} bytes")
        sig, ver, _ = struct.unpack_from("<III", blob, 0)
        check(sig == SIGNATURE, "signature matches", f"0x{sig:08X}")
        check(ver == VERSION, "version matches", f"{ver}")

        # -- 2. the walk ends exactly ------------------------------------
        print("\n2. Tag walk consumes the chunk to the byte")
        pm = PathingMap.from_chunk(blob)      # raises if either walk misses
        check(True, "top-level and plane walks both landed on the end")
        check(len(pm.planes) == KAMADAN_PLANES, "plane count",
              f"{len(pm.planes)}")
        check(len(pm.trapezoids) == KAMADAN_TRAPEZOIDS, "trapezoid count",
              f"{len(pm.trapezoids)}")
        check(TRAPEZOID_SIZE == 44, "trapezoid record is 44 bytes")
        total = sum(p["trapezoids"] for p in pm.planes)
        check(total == len(pm.trapezoids),
              "header counts agree with what was decoded", f"{total}")

        # -- 3. the geometry is geometry ---------------------------------
        print("\n3. Trapezoids are well formed")
        bad_y = [t for t in pm.trapezoids if t.y_top < t.y_bottom]
        bad_x = [t for t in pm.trapezoids
                 if t.x_top_left > t.x_top_right
                 or t.x_bottom_left > t.x_bottom_right]
        check(not bad_y, "no inverted y spans", f"{len(bad_y)} bad")
        check(not bad_x, "no crossed x edges", f"{len(bad_x)} bad")
        xs = [v for t in pm.trapezoids
              for v in (t.x_top_left, t.x_top_right,
                        t.x_bottom_left, t.x_bottom_right)]
        ys = [v for t in pm.trapezoids for v in (t.y_top, t.y_bottom)]
        span = max(xs) - min(xs), max(ys) - min(ys)
        check(1000.0 < span[0] < 1e6 and 1000.0 < span[1] < 1e6,
              "extent is a plausible map size",
              f"x {min(xs):.0f}..{max(xs):.0f}  y {min(ys):.0f}..{max(ys):.0f}")

        # -- 4. the spawn point ------------------------------------------
        print("\n4. The spawn our server already used")
        hits = pm.containing(*KAMADAN_SPAWN)
        check(len(hits) == 1, "spawn is inside exactly one trapezoid",
              f"{len(hits)} hit(s)")
        far = (min(xs) - 5000.0, min(ys) - 5000.0)
        check(not pm.walkable(*far), "a point well outside the map is not walkable")
        # A clip that starts walkable and aims off the map must stop somewhere
        # short of the target, and must stay walkable.
        end = pm.clip(KAMADAN_SPAWN[0], KAMADAN_SPAWN[1], far[0], far[1])
        check(end != far, "clip refuses to reach an unwalkable target")
        check(pm.walkable(*end), "clip's stopping point is itself walkable",
              f"({end[0]:.0f}, {end[1]:.0f})")

        # -- 5. the rest of the corpus -----------------------------------
        rows = [e for e in ar.entries if e.flags == MAP_FLAGS]
        picks = rows if args.all else rows[::max(1, len(rows) // args.sample)]
        print(f"\n5. Plane walk across {len(picks)} of {len(rows)} maps")
        walked = skipped = 0
        broke = []
        for e in picks:
            try:
                d = ar.read(e)
                chunk = None
                for cid, off, size in ffna_chunks(d):
                    if cid == PATHING_CHUNK:
                        chunk = bytes(d[off:off + size])
                        break
                if chunk is None:
                    skipped += 1
                    continue
                m = PathingMap.from_chunk(chunk)
                if any(t.y_top < t.y_bottom for t in m.trapezoids):
                    broke.append((e.index, "inverted y"))
                else:
                    walked += 1
            except Exception as exc:                      # noqa: BLE001
                broke.append((e.index, str(exc)[:70]))
        check(not broke, f"every sampled map walks exactly",
              f"{walked} walked, {skipped} without a pathing chunk")
        for row_i, why in broke[:6]:
            print(f"        row {row_i}: {why}")

    dt = time.perf_counter() - t0
    print(f"\n{'ALL CHECKS PASSED' if not FAILED else str(len(FAILED)) + ' FAILED'}"
          f"  ({dt:.1f}s)")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
