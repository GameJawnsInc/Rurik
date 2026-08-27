"""Check the map-row spawn census against real meshes.

`spawncheck.py` answers a clause `PLAN.md` §3.2 has carried unmeasured -- how
many content map rows put a body on walkable ground -- so the thing that matters
here is whether its answer could have been different. Five sections are built to
be able to fail, and a mutation campaign on 2026-08-27 is why there are five
rather than three -- it broke the tool four ways and TWO of the breaks stayed
green. Both escapes are named at the sections that now catch them (§4, §4b).

  * §2 is the DISCRIMINATION CONTROL, and it is the one `content/maps.toml`'s
    own header specifies: Lakeside's arrival point scores in Lakeside's mesh and
    **zero** in Kamadan's, and Kamadan's scores the reverse. A `containing()`
    that accepted anything -- an unclamped y test, a mesh that loaded as one
    enormous trapezoid -- would score both, and every verdict in §1 would be
    vacuous. This runs first for that reason.

  * §3 SABOTAGES THE SEAM EXPLANATION. `spawncheck` reports maps 143 and 144 as
    SEAM rather than as a two-trapezoid overlap, and the argument is that
    `Trapezoid.contains` closes both y bounds so a point on a shared edge is in
    both neighbours. That is a claim, so it is tested as one: the section
    re-implements `contains` with a HALF-OPEN y interval and requires the same
    points to fall to exactly one trapezoid. If they do not, the seam reading is
    wrong, those rows are a real overlap, and this section goes red rather than
    the tool quietly calling a defect a pass. The control on the control: a
    genuine interior PASS row must score 1 under BOTH interval rules, so the
    sabotage is shown to move only what it claims to move.

  * §4 requires the seam hits to be VERTICALLY ADJACENT -- some trapezoid's
    y_top equal to another's y_bottom. Two trapezoids that contain one point
    while sharing no horizontal edge are overlapping geometry, and `SEAM` would
    be the wrong word for it.

  * §4b is the OVERLAP POSITIVE CONTROL, and it exists because no content row
    overlaps. With every real row landing in one trapezoid or on a seam, the
    branch that reports genuine overlap is never reached, and collapsing it into
    an unconditional `SEAM` left the whole file green. So the section builds
    overlapping geometry by hand -- two trapezoids sharing an interior region --
    and requires OVERLAP, then probes an edge-touching pair on the same shape
    and requires SEAM. A negative needs a positive control.

  * §5 pins the (0,0) ACCIDENT. Five rows carry a placeholder arrival point and
    four of them fail honestly; Sparkfly Swamp's happens to be walkable and
    scores a clean PASS. The count of rows that pass on a placeholder is
    asserted, because the failure mode this guards is somebody reading a green
    census and promoting that row.

WHAT IS DELIBERATELY NOT PINNED: the totals. `PASS=6` would go red every time
anybody adds a map row, which trains the reader to re-baseline rather than to
look. Named rows keep their verdicts (§1), the whole set keeps its invariants
(§6, no row may score OVERLAP), and the arithmetic is free to move.

    python toolkit/mapdata/test_spawncheck.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import checks  # noqa: E402
import spawncheck  # noqa: E402
from archive import Archive, DEFAULT_DAT  # noqa: E402
from pathmap import PathingMap, Trapezoid, file_id_table  # noqa: E402

# Floor from the green run of 2026-08-27, which executes 44 checks. Set from a
# real run and never from a guess: the first draft declared 36 against a body
# that could only produce 33, and the guard called the run incomplete rather
# than passing it -- which is the guard working. It reached 44 honestly once
# section 4b was added and the mutation campaign forced it to grow twice.
LEDGER = checks.Ledger("spawn census", floor=44)
check = checks.adopt(LEDGER)

LAKESIDE_FILE = 0x1B97D
KAMADAN_FILE = 0x345CC
LAKESIDE_SPAWN = (9826.0, 8077.0)
KAMADAN_SPAWN = (-9067.0, 13218.0)

# Verdicts a named row must keep. Each is a DIFFERENT cause, which is the point
# of the five-valued verdict -- if any two of these ever collapse to the same
# token the tool has stopped distinguishing things that differ.
EXPECTED = {
    "146": spawncheck.PASS,          # a measured Pre-Searing arrival point
    "148": spawncheck.PASS,          # same mesh, same point, different map id
    "449": spawncheck.PASS,          # Kamadan, the row test_pathmap already knew
    "280": spawncheck.PASS,          # the Isle, arrival read off a real load
    "143": spawncheck.SEAM,          # authored (1536,1536), exactly on a seam
    "144": spawncheck.SEAM,          # the same authored point, another mesh
    "55": spawncheck.OFF_MESH,       # (0,0) placeholder, honestly off the mesh
    "90": spawncheck.OFF_MESH,       # ditto
    "194": spawncheck.OFF_MESH,      # ditto
    "474": spawncheck.WRONG_PLANE,   # (0,0) contained, but not on plane 0
    "165": spawncheck.UNRESOLVED,    # created chain, not in the study archive
    "166": spawncheck.UNRESOLVED,
    "167": spawncheck.UNRESOLVED,
}


def half_open_contains(t, x, y):
    """`Trapezoid.contains` with the TOP y bound opened. The sabotage of §3.

    Bit-for-bit the real one apart from `y < t.y_top`, so anything it moves is
    attributable to the interval and to nothing else.
    """
    if not (t.y_bottom <= y < t.y_top):
        return False
    span = t.y_top - t.y_bottom
    f = 0.0 if span <= 0.0 else (y - t.y_bottom) / span
    left = t.x_bottom_left + f * (t.x_top_left - t.x_bottom_left)
    right = t.x_bottom_right + f * (t.x_top_right - t.x_bottom_right)
    return left <= x <= right


def main():
    print("1. The census over every content map row")
    rows = spawncheck.census()
    by_id = {r.map_id: r for r in rows}
    check(len(rows) >= 15, f"the content store yields map rows to score",
          f"{len(rows)} rows")
    for map_id, want in sorted(EXPECTED.items()):
        row = by_id.get(map_id)
        if row is None:
            LEDGER.skip(f"map {map_id} verdict",
                        "the row is no longer in the content store")
            continue
        check(row.verdict == want, f"map {map_id} scores {want}",
              f"scored {row.verdict}"
              + (f" ({row.hits} trapezoid(s))" if row.verdict != want else ""))

    print("\n2. The discrimination control -- does the test refuse anything?")
    ar = Archive(DEFAULT_DAT)
    try:
        table = file_id_table(ar)
        lake = PathingMap.load(LAKESIDE_FILE, archive=ar, table=table)
        kam = PathingMap.load(KAMADAN_FILE, archive=ar, table=table)
    finally:
        ar.close()
    check(len(lake.containing(*LAKESIDE_SPAWN)) == 1,
          "Lakeside's spawn is in exactly one Lakeside trapezoid")
    check(len(kam.containing(*LAKESIDE_SPAWN)) == 0,
          "Lakeside's spawn is in ZERO Kamadan trapezoids",
          f"{len(kam.containing(*LAKESIDE_SPAWN))} hits; nonzero here would "
          f"mean the census accepts anything and section 1 is vacuous")
    check(len(kam.containing(*KAMADAN_SPAWN)) == 1,
          "Kamadan's spawn is in exactly one Kamadan trapezoid")
    check(len(lake.containing(*KAMADAN_SPAWN)) == 0,
          "Kamadan's spawn is in ZERO Lakeside trapezoids")

    print("\n3. Sabotage: is SEAM caused by the closed y interval?")
    seams = [r for r in rows if r.verdict == spawncheck.SEAM]
    interiors = [r for r in rows if r.verdict == spawncheck.PASS
                 and r.file_id is not None]
    check(bool(seams), "there is at least one SEAM row to sabotage",
          "with none, this section proves nothing and should be a skip")
    ar = Archive(DEFAULT_DAT)
    try:
        table = file_id_table(ar)
        for r in seams:
            pm = PathingMap.load(r.file_id, archive=ar, table=table)
            closed = len(pm.containing(r.x, r.y))
            opened = sum(1 for t in pm.trapezoids
                         if half_open_contains(t, r.x, r.y))
            check(closed == 2, f"map {r.map_id}: closed interval gives 2",
                  f"gave {closed}")
            check(opened == 1,
                  f"map {r.map_id}: HALF-OPEN interval collapses it to 1",
                  f"gave {opened}; anything but 1 means the second hit is not a "
                  f"shared edge and the trapezoids genuinely overlap")
        # The control on the control: the sabotage must not move an interior row.
        moved = 0
        for r in interiors:
            pm = PathingMap.load(r.file_id, archive=ar, table=table)
            opened = sum(1 for t in pm.trapezoids
                         if half_open_contains(t, r.x, r.y))
            if opened != 1:
                moved += 1
        check(moved == 0,
              "the sabotage moves NO interior PASS row",
              f"{moved} of {len(interiors)} moved; any movement here means the "
              f"half-open rule changes more than the seam and the attribution "
              f"in section 3 is unsafe")
    finally:
        ar.close()

    print("\n4. Seam hits are vertically adjacent, not overlapping")
    ar = Archive(DEFAULT_DAT)
    try:
        table = file_id_table(ar)
        for r in seams:
            pm = PathingMap.load(r.file_id, archive=ar, table=table)
            hits = pm.containing(r.x, r.y)
            # Computed HERE and not via spawncheck._share_an_edge. Calling
            # the module's own predicate would assert it against itself: the
            # 2026-08-27 mutation campaign made that function `return True` and
            # this section stayed green, which is the "a check our decoder
            # forces true" defect in its purest form.
            shared = sorted({t.y_top for t in hits} & {t.y_bottom for t in hits})
            check(bool(shared),
                  f"map {r.map_id}: the hits share a horizontal edge",
                  f"shared y edges {shared}; with none, SEAM is the wrong word "
                  f"and this is real overlapping geometry")
            check(r.interior is not None and max(r.interior) <= 1,
                  f"map {r.map_id}: every diagonal nudge lands in one or none",
                  f"interior probe {r.interior}")
    finally:
        ar.close()

    print("\n4b. The OVERLAP positive control -- synthetic, because the corpus "
          "has none")
    # NO CONTENT ROW SCORES OVERLAP TODAY, so the branch that reports one is
    # never exercised by sections 1-4 and nothing above can tell a working
    # classifier from `return SEAM`. The 2026-08-27 mutation campaign proved
    # exactly that: collapsing the overlap branch into an unconditional SEAM
    # left the whole file green. A negative needs a positive control, so this
    # builds genuinely overlapping geometry -- two trapezoids sharing an
    # INTERIOR region rather than an edge -- and requires the tool to say so.
    both = [
        Trapezoid(0, 0, y_top=200.0, y_bottom=0.0,
                  x_top_left=0.0, x_top_right=200.0,
                  x_bottom_left=0.0, x_bottom_right=200.0),
        Trapezoid(0, 1, y_top=300.0, y_bottom=100.0,   # overlaps y 100..200
                  x_top_left=0.0, x_top_right=200.0,
                  x_bottom_left=0.0, x_bottom_right=200.0),
    ]
    fake_fid = 0xDEAD01
    synth = PathingMap(both, planes=[0])
    inside = (100.0, 150.0)                            # interior to BOTH
    check(len(synth.containing(*inside)) == 2,
          "the synthetic mesh really does double-cover its probe point",
          f"{len(synth.containing(*inside))} hits")
    row = {"name": "synthetic overlap", "file_id": fake_fid,
           "spawn_x": inside[0], "spawn_y": inside[1], "plane": 0}
    scored = spawncheck.score_row("synthetic", row, {fake_fid: 0}, None,
                                  {fake_fid: synth})
    check(scored.verdict == "OVERLAP",
          "genuine overlap is reported as OVERLAP, never as SEAM",
          f"scored {scored.verdict}; a classifier that answers SEAM here would "
          f"report real overlapping geometry as a pass")
    # And the same mesh probed ON its shared edge must still read SEAM, so the
    # control shows the tool separating the two cases rather than just failing.
    edge = {"name": "synthetic seam", "file_id": fake_fid,
            "spawn_x": 100.0, "spawn_y": 250.0, "plane": 0}
    seam_traps = [
        Trapezoid(0, 0, y_top=250.0, y_bottom=0.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
        Trapezoid(0, 1, y_top=500.0, y_bottom=250.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
    ]
    seam_scored = spawncheck.score_row("synthetic", edge, {fake_fid: 0}, None,
                                       {fake_fid: PathingMap(seam_traps,
                                                             planes=[0])})
    check(seam_scored.verdict == spawncheck.SEAM,
          "an edge-touching pair is still reported as SEAM",
          f"scored {seam_scored.verdict}")

    # A VERTICAL seam: two trapezoids in the SAME y band meeting along a shared
    # x boundary. `contains` closes the x bounds too, so a point on that line is
    # in both -- and it is walkable ground, exactly as a horizontal seam is. The
    # first draft of `_share_an_edge` tested only y and filed this as OVERLAP.
    vert = [
        Trapezoid(0, 0, y_top=200.0, y_bottom=0.0, x_top_left=0.0,
                  x_top_right=100.0, x_bottom_left=0.0, x_bottom_right=100.0),
        Trapezoid(0, 1, y_top=200.0, y_bottom=0.0, x_top_left=100.0,
                  x_top_right=200.0, x_bottom_left=100.0, x_bottom_right=200.0),
    ]
    v_scored = spawncheck.score_row(
        "synthetic", {"name": "vertical seam", "file_id": fake_fid,
                      "spawn_x": 100.0, "spawn_y": 100.0, "plane": 0},
        {fake_fid: 0}, None, {fake_fid: PathingMap(vert, planes=[0])})
    check(v_scored.verdict == spawncheck.SEAM,
          "a VERTICAL seam is SEAM, not OVERLAP",
          f"scored {v_scored.verdict}; the y-only predicate scored this OVERLAP "
          f"and would have condemned walkable ground")

    # A SUB-EPS OVERLAP, and this is the case that makes the edge test earn its
    # place. The two trapezoids genuinely overlap, but by less than SEAM_EPS --
    # so every diagonal nudge escapes the sliver and the interior probe reads a
    # clean 1. The interior probe CANNOT catch this one; only the edge test can.
    # Without this check, neutralising `_share_an_edge` to `return True` leaves
    # the suite green, which is precisely what the 2026-08-27 campaign observed.
    sliver = [
        Trapezoid(0, 0, y_top=200.4, y_bottom=0.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
        Trapezoid(0, 1, y_top=400.0, y_bottom=200.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
    ]
    sliver_pm = PathingMap(sliver, planes=[0])
    probe = (100.0, 200.2)                     # inside the 0.4u overlap band
    check(len(sliver_pm.containing(*probe)) == 2,
          "the sub-eps sliver really does double-cover its probe point",
          f"{len(sliver_pm.containing(*probe))} hits")
    nudges = [len(sliver_pm.containing(probe[0] + dx, probe[1] + dy))
              for dx in (-spawncheck.SEAM_EPS, spawncheck.SEAM_EPS)
              for dy in (-spawncheck.SEAM_EPS, spawncheck.SEAM_EPS)]
    check(max(nudges) <= 1,
          "the interior probe is BLIND to a sub-eps overlap",
          f"nudges {nudges}; if any read 2 the sliver is wider than eps and "
          f"this case no longer isolates the edge test")
    # THE MIRROR CASE, and it is what makes the INTERIOR probe load-bearing in
    # its turn. Three trapezoids meeting at y=200: two stacked (a real seam) and
    # a third straddling the line, so the point is on a shared edge AND inside a
    # genuine overlap at once. The edge test says "seam" and is right about the
    # edge; only the interior probe -- which reads 2 a unit either way -- can
    # tell that this is still an overlap. Neutralising that probe to a constant
    # [1,1,1,1] left the suite green until this case existed.
    straddle = [
        Trapezoid(0, 0, y_top=200.0, y_bottom=0.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
        Trapezoid(0, 1, y_top=400.0, y_bottom=200.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
        Trapezoid(0, 2, y_top=250.0, y_bottom=150.0, x_top_left=0.0,
                  x_top_right=200.0, x_bottom_left=0.0, x_bottom_right=200.0),
    ]
    straddle_pm = PathingMap(straddle, planes=[0])
    st_probe = (100.0, 200.0)
    st_hits = straddle_pm.containing(*st_probe)
    check(len(st_hits) == 3,
          "the straddle mesh puts the probe point in all three trapezoids",
          f"{len(st_hits)} hits")
    check(spawncheck._share_an_edge(st_hits, *st_probe),
          "the straddle point IS on a shared edge -- the edge test says seam",
          "so the edge test alone would pass this, and something else must not")
    st_nudges = [len(straddle_pm.containing(st_probe[0] + dx, st_probe[1] + dy))
                 for dx in (-spawncheck.SEAM_EPS, spawncheck.SEAM_EPS)
                 for dy in (-spawncheck.SEAM_EPS, spawncheck.SEAM_EPS)]
    check(max(st_nudges) > 1,
          "the interior probe SEES the straddle overlap",
          f"nudges {st_nudges}; this is the only term that can, and a constant "
          f"interior would report a real overlap as a seam")
    st_scored = spawncheck.score_row(
        "synthetic", {"name": "seam-touching overlap", "file_id": fake_fid,
                      "spawn_x": st_probe[0], "spawn_y": st_probe[1],
                      "plane": 0},
        {fake_fid: 0}, None, {fake_fid: straddle_pm})
    check(st_scored.verdict == "OVERLAP",
          "an overlap that also touches a seam is OVERLAP",
          f"scored {st_scored.verdict}")

    s_scored = spawncheck.score_row(
        "synthetic", {"name": "sub-eps overlap", "file_id": fake_fid,
                      "spawn_x": probe[0], "spawn_y": probe[1], "plane": 0},
        {fake_fid: 0}, None, {fake_fid: sliver_pm})
    check(s_scored.verdict == "OVERLAP",
          "a sub-eps overlap is caught by the EDGE test alone",
          f"scored {s_scored.verdict}; the interior probe read {s_scored.interior}"
          f" and cannot see this, so a permissive edge test hides real overlap")

    print("\n5. The (0,0) placeholder accident")
    origins = [r for r in rows if r.is_origin]
    accidental = [r for r in origins if r.verdict in spawncheck.WALKABLE]
    check(len(origins) >= 4, "the content store still carries (0,0) rows",
          f"{len(origins)} rows")
    check(len(accidental) == 1,
          "exactly ONE (0,0) row passes by accident",
          ", ".join(f"map {r.map_id}" for r in accidental)
          + f" ({len(accidental)} of {len(origins)} placeholder rows); if this "
            f"grows, a placeholder is being read as a measurement")
    check(any(r.map_id == "558" for r in accidental),
          "the accidental pass is Sparkfly Swamp, as recorded")

    print("\n6. Invariants over the whole set")
    known = {spawncheck.PASS, spawncheck.SEAM, spawncheck.OFF_MESH,
             spawncheck.WRONG_PLANE, spawncheck.UNRESOLVED}
    strays = [r for r in rows if r.verdict not in known]
    check(not strays, "no map row scores OVERLAP or an unknown verdict",
          f"{len(strays)} stray verdict(s)"
          + (": " + ", ".join(f"map {r.map_id}={r.verdict}" for r in strays)
             if strays else ""))
    unres = [r for r in rows if r.verdict == spawncheck.UNRESOLVED]
    if unres:
        spawncheck.find_missing(rows)
        homeless = [r for r in unres if not r.found_in]
        check(not homeless,
              "every UNRESOLVED file id resolves in SOME vault archive",
              f"{len(homeless)} of {len(unres)} resolve nowhere"
              + (": " + ", ".join(f"map {r.map_id} (0x{r.file_id:X})"
                                  for r in homeless) if homeless else "")
              + "; an id in no archive at all is a broken row rather than a "
                "wrong-archive reading")
    else:
        LEDGER.skip("UNRESOLVED rows resolve somewhere",
                    "the scored archive holds every file id")

    return LEDGER.verdict()


if __name__ == "__main__":
    raise SystemExit(main())
