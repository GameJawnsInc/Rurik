"""Score a movehook capture for NO-CLIP: off-mesh walking and hole-crossing chords.

Born from the obstacle dig (studies/movecode/FINDINGS.md §1x): the four earlier
no-clip detectors read zero because they scored POINT SAMPLES, and movehook's
event-driven sampling leaves 8.9-19.8 s gaps sitting exactly over the repro
windows.  The instrument that works scores the CHORD a click orders (body
position at click time -> clicked destination, walked at 25 u steps against
`containing()`) and tests body samples against carved prop-outline interiors.
On R4-A this finds 39/84 rapid-pair chords crossing genuine mesh holes (worst
19.3% covered) and the body standing 113 u inside a massif -- where the point
detectors reported nothing.

Usage:
  python toolkit/clientscan/noclipscore.py --bin <movehook.bin> [--map-fid 0x287B3]
                                           [--ecx 0x21A62D60] [--pair-ms 2000]

THE MESH IS PINNED, NEVER SELECTED. The coverage-score selector demonstrably
picks the wrong map on r4a (§1v.3: Sparkfly outscores map 280's own mesh on map
280's own capture), so --map-fid defaults to map 280's 0x287B3 and any other
map must be pinned by hand from content/maps.toml.

The local (displayed) body is auto-picked as the agent ecx with the most
bake/setter records -- printed, and overridable with --ecx, because one agent
id names TWO objects (the world-copy split) and the address is the only safe
key.  Every section prints its denominator; a section with nothing to score
says so rather than printing a reassuring zero.
"""
import argparse
import math
import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "movehook"))
sys.path.insert(0, os.path.join(_HERE, ".."))
sys.path.insert(0, os.path.join(_HERE, "..", "mapdata"))

import readhook                                        # noqa: E402
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
import mapchunks                                       # noqa: E402
import props as propmod                                # noqa: E402
import pathmap                                         # noqa: E402

_f = readhook._f

PROPS_STRIPPED_CHUNK = 0x10000004


def finite(v):
    return v == v and abs(v) != float("inf")


def load_world(map_fid):
    """(PathingMap, [(prop_index, world_outline_polygon)]) for one map file."""
    ar = Archive()
    try:
        table = file_id_table(ar)
        pm = pathmap.PathingMap.load(map_fid, archive=ar, table=table)
        partner = mapchunks.MapIndex(ar).partner(ar.row(table[map_fid]))
        data = ar.read(partner)
        blob = None
        for cid, off, size in ffna_chunks(data):
            if cid == PROPS_STRIPPED_CHUNK:
                blob = bytes(data[off:off + size])
        polys = []
        if blob is not None:
            sp = propmod.StrippedProps.decode(blob)
            for i, p in enumerate(sp.props):
                if p.points:
                    poly = [(p.x + dx, p.y + dy) for dx, dy in p.outline]
                    if poly[0] == poly[-1]:
                        poly = poly[:-1]
                    polys.append((i, poly))
        return pm, polys
    finally:
        ar.close()


def point_in_poly(x, y, poly):
    n = len(poly)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = poly[i]
        xj, yj = poly[j]
        if (yi > y) != (yj > y) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def which_outline(x, y, polys):
    for i, poly in polys:
        if point_in_poly(x, y, poly):
            return i
    return None


def pick_local(cap, names):
    """The displayed body: the agent ecx with the most bake/setter records."""
    counts = {}
    for r in cap.recs:
        if not r.get("have_agent"):
            continue
        if r["site"] < len(names) and names[r["site"]] in ("bake", "setter"):
            counts[r["ecx"]] = counts.get(r["ecx"], 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])


def body_samples(cap, names, ecx):
    """Deduped (tick, x, y) positions for one object, position-reporting sites."""
    keep = ("bake", "setter", "teleport", "setposition", "reseed", "agtrack",
            "snaptest")
    out = []
    for r in sorted(cap.recs, key=lambda r: r["seq"]):
        if not r.get("have_agent") or r["ecx"] != ecx:
            continue
        if r["site"] >= len(names) or names[r["site"]] not in keep:
            continue
        x, y = _f(r["point"][0]), _f(r["point"][1])
        if not (finite(x) and finite(y)):
            continue
        if out and out[-1][0] == r["tick"] and \
                abs(out[-1][1] - x) < 1e-6 and abs(out[-1][2] - y) < 1e-6:
            continue
        out.append((r["tick"], x, y, names[r["site"]]))
    return out


def clicks_with_dests(cap, names):
    """[(tick, dest_x, dest_y)] -- chcli_point paired 1:1 with the mapfindpath
    record at seq+1 (the click record itself carries no coordinate payload)."""
    idx = {n: i for i, n in enumerate(names)}
    ci, mi = idx.get("chcli_point"), idx.get("mapfindpath")
    if ci is None or mi is None:
        return []
    by_seq = {r["seq"]: r for r in cap.recs}
    out = []
    for r in cap.recs:
        if r["site"] != ci:
            continue
        m = by_seq.get(r["seq"] + 1)
        if m is None or m["site"] != mi or m["tick"] != r["tick"]:
            continue
        if not m.get("have_pts"):
            continue
        bx, by = _f(m["pt_b"][0]), _f(m["pt_b"][1])
        if finite(bx) and finite(by):
            out.append((r["tick"], bx, by))
    return sorted(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--bin", required=True, help="movehook.bin capture")
    ap.add_argument("--map-fid", type=lambda s: int(s, 0), default=0x287B3,
                    help="pathing-map file id, PINNED (default map 280's 0x287B3)")
    ap.add_argument("--ecx", type=lambda s: int(s, 0), default=None,
                    help="local body address; default: most bake/setter records")
    ap.add_argument("--pair-ms", type=int, default=2000,
                    help="rapid-pair click gap ceiling, ms")
    ap.add_argument("--step", type=float, default=25.0,
                    help="chord sampling step, world units")
    args = ap.parse_args(argv)

    cap = readhook.Capture(args.bin)
    names = readhook.site_names(cap)
    pm, polys = load_world(args.map_fid)
    print(f"capture: {len(cap.recs)} records; mesh 0x{args.map_fid:X}: "
          f"{len(pm.planes)} planes, {len(pm.trapezoids)} trapezoids; "
          f"{len(polys)} prop outlines")

    census = pick_local(cap, names)
    if not census:
        print("NO bake/setter agent records -- nothing to score, and that is a "
              "FAILURE of the run, not a clean result.")
        return 2
    for ecx, n in census[:4]:
        print(f"  agent 0x{ecx:08X}: {n} bake/setter records")
    ecx = args.ecx if args.ecx is not None else census[0][0]
    print(f"scoring body 0x{ecx:08X}"
          + ("" if args.ecx is None else " (pinned by --ecx)"))

    # ---- A. walked-sample census -------------------------------------
    sm = body_samples(cap, names, ecx)
    off = []
    for tick, x, y, site in sm:
        if not pm.containing(x, y):
            nw = pm.nearest_walkable(x, y, 600.0)
            depth = nw[2] if nw else 600.0
            off.append((tick, x, y, site, depth, which_outline(x, y, polys)))
    print(f"\nA. body samples: {len(sm)} deduped; OFF-MESH {len(off)}")
    deep = [o for o in off if o[4] > 1.0]
    print(f"   off-mesh deeper than 1 u (past float-boundary noise): {len(deep)}")
    for tick, x, y, site, depth, oi in deep[:20]:
        where = f"inside prop {oi}'s outline" if oi is not None else "no outline"
        print(f"     tick {tick}  ({x:8.1f},{y:8.1f})  {site:11s} "
              f"depth {depth:6.1f} u  {where}")
    if len(deep) > 20:
        print(f"     ... and {len(deep) - 20} more")

    # ---- B. rapid-pair chords ----------------------------------------
    clicks = clicks_with_dests(cap, names)
    print(f"\nB. clicks with destinations: {len(clicks)}")
    # A SECTION THAT CANNOT RUN MUST NOT TAKE THE OTHERS WITH IT. This used to
    # `return 0` here, so a capture with fewer than two clicks -- a keyboard-only
    # walk, or the synthetic fixtures in test_noclipscore.py -- printed sections
    # A and B and SILENTLY SKIPPED the plane-aware section C, which is the one
    # that can see a bridge. Say the section is unexercised and carry on.
    do_chords = len(clicks) >= 2
    if not do_chords:
        print("   fewer than 2 clicks -- chord section CANNOT RUN "
              "(not a zero; the section is unexercised)")
    ticks = [s[0] for s in sm]
    import bisect
    crossing = fully = 0
    pairs = 0
    worst = None
    for i in (range(1, len(clicks)) if do_chords else ()):
        t, dx, dy = clicks[i]
        if t - clicks[i - 1][0] > args.pair_ms:
            continue
        pairs += 1
        j = bisect.bisect_right(ticks, t) - 1
        if j < 0:
            continue
        _, ox, oy, _ = sm[j]
        L = math.hypot(dx - ox, dy - oy)
        n = max(1, int(L / args.step))
        cov = 0
        for k in range(n + 1):
            u = k / n
            if pm.containing(ox + (dx - ox) * u, oy + (dy - oy) * u):
                cov += 1
        frac = cov / (n + 1)
        if frac >= 1.0:
            fully += 1
        else:
            crossing += 1
            if worst is None or frac < worst[0]:
                worst = (frac, L, t)
    if do_chords:
        print(f"   rapid pairs (gap <= {args.pair_ms} ms): {pairs}")
        if pairs == 0:
            print("   ZERO rapid pairs -- the repro manoeuvre was not "
                  "exercised; chord verdicts cannot be read from this run")
        else:
            print(f"   chords fully covered: {fully}   crossing uncovered "
                  f"ground: {crossing}")
            if worst:
                print(f"   worst chord: {worst[0] * 100:.1f}% covered over "
                      f"{worst[1]:.0f} u at tick {worst[2]}")
    # ---- C. plane-aware: the case 2D coverage CANNOT see -------------
    #
    # THIS SECTION EXISTS BECAUSE SECTION A READ ZERO ON A CAPTURE THAT HAD
    # TWO NO-CLIPS IN IT. `containing()` unions all 68 planes, so a body on a
    # bridge DECK and a body on the ground UNDER that deck are the same (x, y)
    # and both score on-mesh. FINDINGS §1w.7 established that plane-blindness
    # is irrelevant to a carved HOLE -- true, and it made this look settled --
    # but a bridge is the other case, and there it is the whole question.
    # `m_point` has carried the plane all along: it is 16 bytes, `float x,
    # float y, int plane, int`.
    anom, stacked = [], 0
    for tick, x, y, site in sm:
        cont = pm.containing(x, y)
        if not cont:
            continue
        offer = {t.plane for t in cont}
        if len(offer) > 1:
            stacked += 1
        # The plane the body DECLARES is not one the mesh offers here.
        rec_plane = None
        for r in cap.recs:
            if r["tick"] == tick and r.get("have_agent") and r["ecx"] == ecx:
                rec_plane = r["point"][2]
                break
        if rec_plane is not None and rec_plane not in offer:
            anom.append((tick, x, y, rec_plane, sorted(offer)))
    print(f"\nC. plane-aware (the case 2D coverage cannot see)")
    print(f"   samples standing on STACKED ground (>1 plane here): {stacked}")
    print(f"   samples declaring a plane the mesh does NOT offer:  {len(anom)}")
    if not stacked and not anom:
        print("   no stacked geometry anywhere the body went -- this run had ZERO "
              "EXPOSURE to the bridge/deck case, which is not the same as a clean "
              "result")
    for tick, x, y, p, offer in anom[:20]:
        print(f"     tick {tick}  ({x:8.1f},{y:8.1f})  declares plane {p:3d}, "
              f"mesh offers {offer[:6]}")
    if len(anom) > 20:
        print(f"     ... and {len(anom) - 20} more")

    print("\nReading: under a straight-line-granting policy the crossing count "
          "is the no-clip exposure; under --router the GRANTED legs are legal "
          "by construction, so a body still crossing uncovered ground deeper "
          "than 1 u in section A indicts the display/reconcile path, not the "
          "grant content.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
