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
    `0x0070A0D4`). BUILT 2026-08-29 — the `mapfindpath_ret*` rows — so a v7
    capture carries the client's own answer and the paragraph below applies.
    A v6-or-older capture is still entry-only and still scores three-valued.

So the verdicts here are deliberately three-valued, and only one of them is a claim
about the client:

    OURS-FAILED   we found no route where the client asked one. OUR BUG, located.
    BOTH-OK       we found a route. Says nothing about whether it is the SAME route.
    OFF-MESH      the query's own endpoints are not on our mesh at all — a decode
                  gap upstream of routing, and the more serious kind.

THE RET TAP EXISTS AS OF 2026-08-29, AND IT SPLITS ONE OF THOSE THREE IN HALF.
`OURS-FAILED` above bundles two opposite situations, and the bundling always ran in
the direction that flatters nothing: "we found no route where the client asked one"
assumed the CLIENT found one. When a v7 capture carries the answer, it does not have
to be assumed:

    OURS-FAILED   we found nothing, the client found a path. OUR BUG, and now
                  genuinely so rather than by assumption.
    THEIRS-FAILED we routed, the client returned pathCount == 0. The CLIENT's own
                  failure — and precisely what HANDOFF-PLANE §4.2 predicts under a
                  plane lock.
    BOTH-FAILED   neither of us found a path. NOT our bug, and the three-valued
                  scorer counted every one of these as OURS-FAILED, so its
                  decode-gap number was an over-count of unknown size.
    AGREE / DIFFER  both routed; whether the SHAPES match is a separate axis.

That over-count is the MOVECODE-Q2 headline, so the split matters more than the new
verdict names suggest. A v6-or-older capture still scores three-valued and says so —
the point is that it now says so rather than quietly meaning something narrower.

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
from readhook import RET_MAX_POINTS                           # noqa: E402


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


def answered(cap, names):
    """[(Query, ret_record)] for every query whose ANSWER is in the capture.

    Joined on (tid, esp) by `readhook._pair_mfp` -- one home for the join, so a
    consumer cannot invent a looser one. Returns (pairs, notes) where `notes`
    carries the refusals as COUNTS: nothing is silently dropped, because a low
    pairing rate makes every verdict below it a statement about a biased subset.
    """
    sbase = readhook.static_base()

    def reb(va):
        return va - cap.base + sbase if va >= cap.base else va
    pairs, orphan, esp_bad = readhook._pair_mfp(cap, names)
    out = [(Query(e, reb), r) for e, r in pairs]
    return out, {"unpaired-answer": orphan, "esp-mismatch": esp_bad}


def _seg_dist(px, py, ax, ay, bx, by):
    """Distance from a point to a segment -- polylines are lines, not vertices."""
    dx, dy = bx - ax, by - ay
    d2 = dx * dx + dy * dy
    t = 0.0 if d2 == 0.0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / d2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _poly_gap(a, b):
    """max over a's vertices of the distance to polyline b."""
    worst = 0.0
    for (px, py) in a:
        best = min(_seg_dist(px, py, b[i][0], b[i][1], b[i + 1][0], b[i + 1][1])
                   for i in range(len(b) - 1)) if len(b) > 1 else \
            math.hypot(px - b[0][0], py - b[0][1])
        worst = max(worst, best)
    return worst


def _hausdorff(a, b):
    """Symmetric Hausdorff between two polylines."""
    if not a or not b:
        return float("inf")
    return max(_poly_gap(a, b), _poly_gap(b, a))


def _their_poly(q, r, n):
    """The client's answer as a polyline, WITH the start prepended.

    `out_path` OMITS the start -- measured on r7, the client's first waypoint
    equals the query's from-point in 1 of 86 multi-point answers (p50 446 u
    away) -- so comparing the raw buffer against our route would charge us for
    an endpoint the client never claimed to include.
    """
    pts = [(_f(r["out_path"][i * 4]), _f(r["out_path"][i * 4 + 1]))
           for i in range(n)]
    return [(q.src[0], q.src[1])] + pts


def score_paired(pm, pairs, list_n=0):
    """Five-valued scoring against the CLIENT's own answer. -> (rows, tally).

    `OURS-FAILED` no longer assumes the client succeeded, and `BOTH-FAILED` --
    which the three-valued scorer counted as ours -- is now its own row. A query
    whose count could not be read is UNREADABLE rather than assumed to be zero:
    `have_out` bit 0 is what says the difference, and pathCount == 0 is the
    registered prediction, so merging the two would destroy the measurement.
    """
    rows = []
    tally = {"AGREE": 0, "DIFFER": 0, "UNCOMPARED": 0, "OURS-FAILED": 0,
             "THEIRS-FAILED": 0, "BOTH-FAILED": 0, "OFF-MESH": 0,
             "UNREADABLE": 0}
    for q, r in pairs:
        if not (r.get("have_out", 0) & 1):
            tally["UNREADABLE"] += 1
            continue
        theirs = r["out_count"]
        x0, y0, x1, y1 = q.src[0], q.src[1], q.dst[0], q.dst[1]
        a_on, b_on = pm.walkable(x0, y0), pm.walkable(x1, y1)
        if not (a_on and b_on):
            verdict = "OFF-MESH"
            detail = (f"start {'on' if a_on else 'OFF'} mesh, "
                      f"goal {'on' if b_on else 'OFF'} mesh; "
                      f"client pathCount {theirs}")
        else:
            ours = pm.route(x0, y0, x1, y1)
            if ours and theirs:
                # SHAPE is a separate axis and is only comparable when the
                # record kept the whole path: out_n < out_count means the
                # waypoints are truncated even though the COUNT is exact.
                whole = (r.get("have_out", 0) & 2) and r["out_n"] >= theirs
                if not whole:
                    # ITS OWN VERDICT, not AGREE. Scoring a NON-COMPARISON as
                    # agreement is how 13 of r7's 144 AGREE rows were rows
                    # nothing had been compared on.
                    verdict = "UNCOMPARED"
                    detail = (f"ours {len(ours)}, theirs {theirs} -- shape not "
                              f"compared (path truncated at {r.get('out_n', 0)} "
                              f"of {RET_MAX_POINTS})")
                else:
                    gap = _hausdorff(ours, _their_poly(q, r, theirs))
                    verdict = "AGREE" if gap <= 16.0 else "DIFFER"
                    detail = (f"ours {len(ours)}, theirs {theirs}, polylines "
                              f"{gap:.1f} u apart (Hausdorff)")
            elif ours and not theirs:
                verdict = "THEIRS-FAILED"
                detail = "we routed; the client returned pathCount 0"
            elif theirs and not ours:
                verdict = "OURS-FAILED"
                detail = f"the client found {theirs} point(s); route() found none"
            else:
                verdict = "BOTH-FAILED"
                detail = ("neither found a path -- NOT our decode, and the "
                          "three-valued scorer counted this as OURS-FAILED")
        tally[verdict] += 1
        if len(rows) < list_n:
            rows.append((verdict, x0, y0, x1, y1, detail))
    return rows, tally


def identify(qs):
    """Work out WHICH map a capture came from, by asking every rowed mesh.

    A capture does not record its map, so `--map` is a value a human types from
    memory -- and the wrong mesh does not error, it answers. Every point lands
    off-mesh, `pathdiff` reports OFF-MESH for all of them, and that reads exactly
    like the decode gap this tool exists to find. That is the worst possible failure
    for an instrument whose interesting answer is "our mesh is wrong".

    So: score the captured endpoints against each candidate and let the data pick.
    The right map puts nearly every point ON its mesh; a wrong one puts nearly none.
    REFUSES when the winner is not clear-cut, rather than guessing.
    """
    from pathmap import PathingMap
    from archive import Archive, file_id_table
    pts = []
    for q in qs:
        if q.src:
            pts.append((q.src[0], q.src[1]))
        if q.dst:
            pts.append((q.dst[0], q.dst[1]))
    if not pts:
        print("")
        print("cannot identify the map: no query in this capture carries "
              "coordinates.")
        return None, None
    try:
        import content as content_mod
        t = content_mod.load()
        t = t.tables if hasattr(t, "tables") else t
        fids = sorted({r["file_id"] for r in (t.get("map") or {}).values()
                       if r.get("file_id")})
    except Exception as ex:
        print("")
        print(f"cannot identify the map: no content rows ({ex})")
        return None, None

    ar = Archive()
    table = file_id_table(ar)
    scored = []
    for fid in fids:
        try:
            pm = PathingMap.load(fid, archive=ar, table=table)
        except Exception:
            continue
        on = sum(1 for x, y in pts if pm.walkable(x, y))
        scored.append((on / len(pts), fid, pm))
    scored.sort(reverse=True, key=lambda r: r[0])
    if not scored:
        print("")
        print("cannot identify the map: no candidate mesh loaded.")
        return None, None
    print("")
    print(f"identifying the map from {len(pts)} captured point(s):")
    for frac, fid, _pm in scored[:5]:
        print(f"   0x{fid:<7X} {100.0 * frac:5.1f}% on mesh")
    best, runner = scored[0], (scored[1] if len(scored) > 1 else (0.0, 0, None))
    if best[0] < 0.6 or best[0] - runner[0] < 0.2:
        print("")
        print("REFUSING to pick: no candidate is a clear winner. Pass --map "
              "explicitly if you know it, but check first -- an ambiguous result "
              "can also mean our decode is wrong for the real map.")
        return None, None
    print(f"   -> 0x{best[1]:X}")
    return best[1], best[2]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bin", default=None, help="capture file")
    ap.add_argument("--map", required=True,
                    help="map FILE id the capture was taken in, e.g. 0x1B97D, or "
                         "`auto` to identify it from the captured coordinates. "
                         "Required either way: a capture does not record the map, "
                         "and the WRONG mesh answers confidently.")
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
    if a.map.strip().lower() == "auto":
        fid, pm = identify(qs)
        if fid is None:
            return 1
    else:
        fid = int(a.map, 0)
        pm = PathingMap.load(fid)
        # CROSS-CHECK the map you were TOLD, because the wrong one does not error
        # -- it reports every point OFF-MESH, which reads exactly like the decode
        # gap this tool exists to find. `auto` alone cannot identify a map (meshes
        # overlap in coordinate space; run 2's points sit on two different maps at
        # 100%), but it can say "the one you named is not among the plausible ones",
        # and that is the half worth having.
        pts = [(q.src[0], q.src[1]) for q in qs if q.src]
        pts += [(q.dst[0], q.dst[1]) for q in qs if q.dst]
        if pts:
            on = sum(1 for x, y in pts if pm.walkable(x, y)) / len(pts)
            if on < 0.5:
                print("")
                print(f"!! WARNING: only {100.0 * on:.0f}% of this capture's points "
                      f"are on map 0x{fid:X}'s mesh.")
                print("   Either --map is wrong, or our decode of that map is badly "
                      "off. Run")
                print("   `--map auto` to see which meshes DO fit before reading "
                      "anything below")
                print("   as a finding -- a wrong map produces 100% OFF-MESH and "
                      "looks like a result.")
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

        # ---- THE CLIENT'S OWN ANSWER, when the capture carries it -----------
        if cap.version >= 7:
            pairs, notes = answered(cap, names)
            withpts = [(q, r) for q, r in pairs if q.src and q.dst]
            print(f"\nPAIRED WITH THE CLIENT'S ANSWER: {len(pairs)} of {n} "
                  f"({100.0 * len(pairs) / n:.1f}%), {len(withpts)} with "
                  f"coordinates")
            for k, v in sorted(notes.items()):
                if v:
                    print(f"   {k:16} {v}")
            if notes["esp-mismatch"]:
                print("   *** an esp mismatch REFUTES the join's own premise "
                      "(all four exits")
                print("       restore esp to the entry value). Those pairs are "
                      "NOT scored.")
            if len(pairs) < n * 0.9:
                print("   NOTE: a low pairing rate makes every verdict below a "
                      "statement")
                print("   about a BIASED SUBSET -- the ring drops questions "
                      "before answers.")
            if withpts:
                prows, ptally = score_paired(pm, withpts, a.list)
                m = sum(ptally.values())
                print(f"\nscored against the client's own answer ({m}):")
                for k in ("OURS-FAILED", "BOTH-FAILED", "THEIRS-FAILED",
                          "OFF-MESH", "DIFFER", "AGREE", "UNCOMPARED",
                          "UNREADABLE"):
                    if ptally[k] or k in ("OURS-FAILED", "BOTH-FAILED"):
                        print(f"   {k:14} {ptally[k]:6}  "
                              f"{100.0 * ptally[k] / m if m else 0:5.1f}%")
                print("")
                print("   OURS-FAILED is now a MEASUREMENT rather than an "
                      "assumption: the")
                print("   client found a path where we found none. BOTH-FAILED "
                      "is the half")
                print("   the three-valued scorer above counted as ours and is "
                      "NOT our bug.")
                if ptally["THEIRS-FAILED"]:
                    print("   THEIRS-FAILED is the client's own solver returning "
                          "pathCount 0 --")
                    print("   HANDOFF-PLANE §4.2's registered lock prediction, "
                          "if it clusters.")
                if prows:
                    print(f"\nfirst {len(prows)}:")
                    for v, x0, y0, x1, y1, d in prows:
                        print(f"   {v:14} ({x0:9.1f},{y0:9.1f}) -> "
                              f"({x1:9.1f},{y1:9.1f})  {d}")
        else:
            print("")
            print(f"   (capture v{cap.version}: no ret tap, so OURS-FAILED "
                  f"still ASSUMES the")
            print("   client succeeded. v7 splits out BOTH-FAILED, which is not "
                  "our bug.)")

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
