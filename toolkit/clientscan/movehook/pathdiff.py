"""Replay the client's own navmesh queries through OUR pathmap. MOVECODE-B3.

    python toolkit/clientscan/movehook/pathdiff.py --map 0x1B97D
    python toolkit/clientscan/movehook/pathdiff.py --map 0x1B97D --bin PATH --list 20

WHAT THIS IS FOR. Router run 5 ended the server-side phase on a specific failure:
with the routing origin *perfect* — 0 u error against the client's own last report —
all four clicks still routed away from their destinations through one identical
waypoint, because our decode of map 280 reads the player's open ground as a pocket.
That is MOVECODE-Q2, and until now it was an inference drawn from where our routes
came out. This makes it a measurement.

`movehook` taps `MapFindPath` (`0x00709E90`), the client's OWN navmesh query, and
records every `(from, to, range)` it asks. This file replays each of those exact
queries through `pathmap.route()` and reports where ours fails.

**THE ASYMMETRY IS THE WHOLE POINT, AND IT IS WHY AN ENTRY-ONLY TAP SUFFICES.**
`MapFindPath` is `__cdecl` with no meaningful return value — its answers go into
caller-supplied out-buffers (`arg5` = count, `arg6` = points), which at the hook's
entry still hold uninitialised caller memory. So we CANNOT see what the client
answered. We do not need to for the primary question:

  * **The client asking a query is itself evidence the query was reachable.** These
    are the queries a live client made while the operator was walking around
    successfully. If OUR router answers "no path" for a query the client made
    routinely, that is our decode being wrong, and the query names exactly where.
  * What an entry-only tap cannot do is adjudicate a DISAGREEMENT in route SHAPE —
    two different legal paths. That needs the client's own answer, which needs a
    second tap at the four `ret` sites (`0x00709F0F`, `0x00709F44`, `0x0070A0AD`,
    `0x0070A0D4`). Named in `content/movecode.toml`'s `mapfindpath` row, not built.

So the verdicts here are deliberately three-valued, and only one of them is a claim
about the client:

    OURS-FAILED   we found no route where the client asked one. OUR BUG, located.
    BOTH-OK       we found a route. Says nothing about whether it is the SAME route.
    OFF-MESH      the query's own endpoints are not on our mesh at all — a decode
                  gap upstream of routing, and the more serious kind.

REFUSES RATHER THAN GUESSES about which map. A capture does not record the map id,
and replaying map A's queries against map B's mesh produces confident nonsense — so
`--map` is REQUIRED and is checked against the archive rather than assumed.

Stdlib only. Reads the vaulted archive read-only.
"""

import argparse
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))
sys.path.insert(0, HERE)

import readhook                                                # noqa: E402


def _f(dw):
    return struct.unpack("<f", struct.pack("<I", dw))[0]


class Query:
    """One `MapFindPath` call, as the entry hook saw it.

    The client passes POINTERS for `from` and `to`, so the coordinates are not in
    the record — only the addresses. `movehook` cannot follow them at capture time
    without reading foreign memory it has not proven readable, so what a v2 record
    carries is the pointers plus whatever the agent block held. This class is the
    honest shape of that: it knows what it does NOT have.
    """

    __slots__ = ("seq", "tick", "rng", "opaque", "out_count_ptr", "out_path_ptr",
                 "retaddr", "src", "dst")

    def __init__(self, r, reb):
        self.seq = r["seq"]
        self.tick = r["tick"]
        self.rng = _f(r.get("arg3", 0))
        self.opaque = r.get("arg4", 0)
        self.out_count_ptr = r.get("arg5", 0)
        self.out_path_ptr = r.get("arg6", 0)
        self.retaddr = reb(r.get("retaddr", 0))
        # v3 follows the pointers at capture time; `have_pts` says which landed.
        # Anything older leaves these None, and None is what stops a caller
        # plotting a pointer value as a coordinate.
        hp = r.get("have_pts", 0)
        a, b = r.get("pt_a"), r.get("pt_b")
        self.src = (_f(a[0]), _f(a[1]), a[2]) if (hp & 1) and a else None
        self.dst = (_f(b[0]), _f(b[1]), b[2]) if (hp & 2) and b else None


def queries(cap, names):
    """Every mapfindpath record in the capture, as Query objects."""
    idx = {n: i for i, n in enumerate(names)}
    site = idx.get("mapfindpath")
    if site is None:
        return None
    sbase = readhook.static_base()

    def reb(va):
        return va - cap.base + sbase if va >= cap.base else va
    return [Query(r, reb) for r in cap.recs if r["site"] == site]


def score(pm, pts, list_n=0):
    """Replay `(x0,y0,x1,y1)` tuples through our router. Returns (rows, tally)."""
    rows, tally = [], {"OURS-FAILED": 0, "BOTH-OK": 0, "OFF-MESH": 0}
    for (x0, y0, x1, y1) in pts:
        a_on = pm.walkable(x0, y0)
        b_on = pm.walkable(x1, y1)
        if not (a_on and b_on):
            verdict = "OFF-MESH"
            detail = (f"start {'on' if a_on else 'OFF'} mesh, "
                      f"goal {'on' if b_on else 'OFF'} mesh")
        else:
            path = pm.route(x0, y0, x1, y1)
            if path:
                verdict = "BOTH-OK"
                detail = f"{len(path)} point(s)"
            else:
                verdict = "OURS-FAILED"
                detail = "both endpoints on our mesh, but route() found nothing"
        tally[verdict] += 1
        if len(rows) < list_n:
            rows.append((verdict, x0, y0, x1, y1, detail))
    return rows, tally


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", default=None, help="capture file")
    ap.add_argument("--map", required=True,
                    help="map FILE id the capture was taken in, e.g. 0x1B97D. "
                         "Required: a capture does not record it, and the wrong "
                         "mesh answers confidently.")
    ap.add_argument("--list", type=int, default=12,
                    help="print this many individual queries")
    a = ap.parse_args()

    path = a.bin
    if not path:
        try:
            import vaultpath
            path = os.path.join(vaultpath.vault_path("research", "movecode"),
                                "movehook.bin")
        except Exception as ex:
            return print(f"cannot locate the vault ({ex}); pass --bin") or 2
    if not os.path.isfile(path):
        return print(f"no capture at {path}") or 2

    cap = readhook.Capture(path)
    names = readhook.site_names(cap)
    qs = queries(cap, names)
    print(f"capture: {path}  (v{cap.version}, {cap.stored} record(s))")
    if qs is None:
        print("\nThis capture has no `mapfindpath` site. It was taken before "
              "MOVECODE-B3 added it -- run 1 (2026-08-27) is such a capture. "
              "Nothing to replay; this is not a failure.")
        return 1
    print(f"{len(qs)} MapFindPath quer(y|ies) captured")
    if not qs:
        print("\nZERO queries with the site armed. Either the client solved no "
              "paths while the hook was live, or the site never armed -- check "
              "`NEVER ARMED` in movehook.txt before concluding the former.")
        return 1

    from pathmap import PathingMap
    fid = int(a.map, 0)
    pm = PathingMap.load(fid)
    print(f"our mesh: map file 0x{fid:X}, {len(pm.trapezoids)} trapezoid(s), "
          f"{len(pm.planes)} plane(s)")

    usable = [q for q in qs if q.src and q.dst]
    if not usable:
        print("\n!! NO QUERY IN THIS CAPTURE CARRIES COORDINATES.")
        print("   The client passes from/to BY REFERENCE, so a v1/v2 record holds")
        print("   only the pointer VALUES -- addresses in the client's own address")
        print("   space, which are not replayable and must never be plotted as")
        print("   points. Capture v3 follows them at capture time; re-run with a")
        print("   v3-capable movehook.")
    else:
        pts = [(q.src[0], q.src[1], q.dst[0], q.dst[1]) for q in usable]
        rows, tally = score(pm, pts, a.list)
        n = len(pts)
        print(f"\nreplayed {n} quer(y|ies) carrying coordinates "
              f"({len(qs) - n} had none):")
        for k in ("OURS-FAILED", "OFF-MESH", "BOTH-OK"):
            print(f"   {k:12} {tally[k]:6}  {100.0 * tally[k] / n:5.1f}%")
        if tally["OURS-FAILED"] or tally["OFF-MESH"]:
            print("")
            print("   OURS-FAILED and OFF-MESH are OUR decode failing on a query a")
            print("   live client made while the player was moving. Each names a")
            print("   place to look. This is MOVECODE-Q2 answering.")
        else:
            print("")
            print("   Our mesh answered every query the client asked. That does NOT")
            print("   mean the routes AGREE -- scoring route SHAPE needs the")
            print("   client's own answer, which an entry-only tap cannot see.")
        if rows:
            print(f"\nfirst {len(rows)}:")
            for v, x0, y0, x1, y1, d in rows:
                print(f"   {v:12} ({x0:9.1f},{y0:9.1f}) -> "
                      f"({x1:9.1f},{y1:9.1f})  {d}")

    # Caller census -- useful regardless of whether coordinates were captured.
    import collections
    by_caller = collections.Counter(q.retaddr for q in qs)
    print(f"\n{len(by_caller)} distinct caller(s) of MapFindPath:")
    for ret, n in by_caller.most_common(12):
        print(f"   0x{ret:08X}  {n}")
    rngs = sorted(q.rng for q in qs if math.isfinite(q.rng))
    if rngs:
        print(f"\nrange argument: min {rngs[0]:.1f}  p50 {rngs[len(rngs)//2]:.1f}  "
              f"max {rngs[-1]:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
