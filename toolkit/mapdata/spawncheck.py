"""Score every content map row's arrival point against that map's own navmesh.

WHAT THIS EXISTS FOR. `PLAN.md` §3.2 grades R4c-1 partly on "map rows with
resolved file ids and arrival points that pass the spawn-in-trapezoid test", and
then says of the map figure: *"how many of the nine pass the trapezoid test has
not been re-run, so the map figure is a row count and not yet a score against
this criterion."* It was nine rows when that was written and it is fifteen now.
Nothing in the tree walked the rows and scored them -- `test_pathmap.py` §4
checks **Kamadan's** spawn, one map, hardcoded -- so the clause stayed a row
count for as long as it took someone to run this.

THE TEST ITSELF is the one `content/maps.toml`'s header describes: parse the
map's trapezoid mesh and count how many trapezoids contain the arrival point.
That header says "EXACTLY ONE is what a non-overlapping tiling gives for a point
on the ground", and **that sentence has a boundary case it does not mention.**
`Trapezoid.contains` is inclusive on both y bounds (`y_bottom <= y <= y_top`)
and on both x bounds, so a point sitting exactly on the horizontal seam between
two vertically adjacent trapezoids is contained by BOTH. Two of our own rows sit
on such a seam -- maps 143 and 144, whose authored arrival point is
`(1536, 1536)`, exactly the y at which trapezoid 2 ends and trapezoid 12 begins.
One unit either way returns 1. That is not an overlapping tiling and not a
defect in `datwrite`'s mesh; it is the closed interval doing what it says.

So the verdict is five-valued, not two, and each value has a DIFFERENT cause --
which is the whole reason not to report one number:

    PASS         exactly one trapezoid, on the plane the row declares
    SEAM         two or more, but the point is on a shared edge: nudging it
                 by EPS in each diagonal direction gives exactly one, and the
                 hits are vertically adjacent. Walkable ground, still a pass,
                 and worth its own token because a row that scores SEAM is one
                 float away from scoring PASS and its author probably meant to.
    OFF-MESH     zero trapezoids. The row's point is not on walkable ground.
    WRONG-PLANE  contained, but not on the `plane` the row declares.
    UNRESOLVED   the file id is not in the archive being scored -- so this row
                 says nothing about the map, only about which archive you
                 pointed at. `--find-missing` searches the vault for one that
                 does resolve it, because "not in the archive" and "not in THIS
                 archive" are different findings and the tool that conflates
                 them is worse than no tool.

WHY SEAM IS A PASS AND NOT A FAIL. The criterion is about whether the arrival
point puts a body on walkable ground. A seam point does. Scoring it FAIL would
condemn two rows that are correct, and scoring it PASS silently would hide that
the documented premise has an unstated case. It gets a name instead.

THE (0,0) TRAP, and it is why this file exists as a checked-in check rather than
a number pasted into a document. Five rows carry `spawn_x = spawn_y = 0.0`,
which is a placeholder and not an arrival point anybody measured. Three of them
score OFF-MESH and one scores WRONG-PLANE, which is the honest answer. But
Sparkfly Swamp's `(0,0)` lands in exactly one trapezoid on plane 0 and scores a
clean **PASS** -- by accident, because the origin of that map happens to be
walkable ground. A placeholder that passes is worse than one that fails: it
looks verified. `--flag-origin` reports it, and the test asserts the count, so
the day somebody promotes that row on the strength of a green the check says
which greens were earned.

    python toolkit/mapdata/spawncheck.py
    python toolkit/mapdata/spawncheck.py --find-missing
    python toolkit/mapdata/spawncheck.py --dat vault/run/.../Gw.dat
    python toolkit/mapdata/spawncheck.py --json

standard library only.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))

import content  # noqa: E402
import vaultpath  # noqa: E402
from archive import Archive, DEFAULT_DAT  # noqa: E402
from pathmap import PathingMap, file_id_table  # noqa: E402

# How far to nudge when asking "is this point on a seam?". One game unit: far
# enough to leave a shared edge (edges are exact float equalities, not bands),
# small enough that it cannot cross a trapezoid whose extent is meaningful. The
# smallest trapezoid in any mesh we score is hundreds of units on a side.
SEAM_EPS = 1.0

PASS = "PASS"
SEAM = "SEAM"
OFF_MESH = "OFF-MESH"
WRONG_PLANE = "WRONG-PLANE"
UNRESOLVED = "UNRESOLVED"

WALKABLE = (PASS, SEAM)


class Row:
    """One map row's verdict, with everything needed to argue with it."""

    __slots__ = ("map_id", "name", "file_id", "x", "y", "plane", "verdict",
                 "hits", "hit_planes", "interior", "adjacent", "is_origin",
                 "found_in")

    def __init__(self, **kw):
        for slot in self.__slots__:
            setattr(self, slot, kw.get(slot))

    def as_dict(self):
        return {s: getattr(self, s) for s in self.__slots__}


def _x_edges_at(t, y):
    """The left and right boundary of trapezoid `t` at height `y`.

    `Trapezoid.contains`'s own interpolation, pulled out so the seam test and
    the point test are asking the same question of the same arithmetic.
    """
    span = t.y_top - t.y_bottom
    f = 0.0 if span <= 0.0 else (y - t.y_bottom) / span
    return (t.x_bottom_left + f * (t.x_top_left - t.x_bottom_left),
            t.x_bottom_right + f * (t.x_top_right - t.x_bottom_right))


def _share_an_edge(hits, x, y):
    """Do these trapezoids meet ALONG AN EDGE at (x, y), rather than overlap?

    The seam explanation is a CLAIM about the geometry and this is what makes it
    refutable. Two trapezoids that contain one point while sharing no edge
    through it are overlapping geometry, and the caller must report OVERLAP
    rather than call a defect a pass.

    THERE ARE TWO KINDS OF SEAM and the first draft of this function knew only
    one. A HORIZONTAL seam is some trapezoid's `y_top` equal to another's
    `y_bottom` -- the stacked-band case, which is what maps 143 and 144 sit on.
    A VERTICAL seam is two trapezoids in the SAME y band meeting along a shared
    x boundary, and the point sits on it because `contains` closes the x bounds
    too. The y-only version reported that second case as OVERLAP. It was found
    by a mutation that should have been caught and was not: forcing this
    function to `return True` left the suite green, which said the predicate was
    doing no work that the interior probe did not already do -- and chasing WHY
    turned up the vertical seam it was silently misfiling.
    """
    if {t.y_top for t in hits} & {t.y_bottom for t in hits}:
        return True
    lefts, rights = set(), set()
    for t in hits:
        left, right = _x_edges_at(t, y)
        lefts.add(left)
        rights.add(right)
    return bool(lefts & rights)


def score_row(map_id, row, table, archive, cache, eps=SEAM_EPS):
    """Score one map row. `cache` maps file_id -> PathingMap across rows."""
    fid = row.get("file_id")
    x, y = row.get("spawn_x"), row.get("spawn_y")
    plane = row.get("plane", 0)
    out = dict(map_id=map_id, name=row.get("name"), file_id=fid, x=x, y=y,
               plane=plane, hits=0, hit_planes=[], interior=None,
               adjacent=None, is_origin=(x == 0.0 and y == 0.0),
               found_in=None)

    if fid not in table:
        return Row(verdict=UNRESOLVED, **out)

    if fid not in cache:
        cache[fid] = PathingMap.load(fid, archive=archive, table=table)
    pm = cache[fid]

    hits = pm.containing(x, y)
    out["hits"] = len(hits)
    out["hit_planes"] = sorted({t.plane for t in hits})

    if not hits:
        return Row(verdict=OFF_MESH, **out)

    on_plane = [t for t in hits if t.plane == plane]
    if not on_plane:
        return Row(verdict=WRONG_PLANE, **out)

    if len(hits) == 1:
        return Row(verdict=PASS, **out)

    # More than one. Either the point is on a shared edge -- in which case
    # stepping off it in every diagonal direction lands in exactly one -- or the
    # trapezoids genuinely overlap, which is a finding and not a pass.
    interior = [len(pm.containing(x + dx, y + dy))
                for dx in (-eps, eps) for dy in (-eps, eps)]
    out["interior"] = interior
    out["adjacent"] = _share_an_edge(hits, x, y)
    # BOTH terms are load-bearing and they cover different failures. The
    # interior probe catches an overlap wider than `eps`; the edge test catches
    # one NARROWER than it, where every nudge escapes the sliver and the probe
    # reads a clean 1. Neither alone is enough, which is why a mutation that
    # neutralised the edge test had to be answered with geometry rather than
    # with a deleted line.
    if max(interior) <= 1 and out["adjacent"]:
        return Row(verdict=SEAM, **out)
    return Row(verdict="OVERLAP", **out)


def census(dat=None, repo_dir=None, eps=SEAM_EPS):
    """Score every map row in the content store. Returns [Row], newest API."""
    world = content.load(repo_dir=repo_dir)
    maps = world.rows("map")
    archive = Archive(dat or DEFAULT_DAT)
    try:
        table = file_id_table(archive)
        cache = {}
        return [score_row(k, maps[k], table, archive, cache, eps)
                for k in sorted(maps, key=lambda s: int(s))]
    finally:
        archive.close()


def find_missing(rows):
    """For every UNRESOLVED row, which vault archive DOES hold its file id?

    "Not in the archive" is a claim about a map; "not in THIS archive" is a claim
    about a path. Only one of them is worth acting on, and the difference is one
    glob. Fills `found_in` in place and returns the rows it resolved.
    """
    want = {r.file_id for r in rows if r.verdict == UNRESOLVED}
    if not want:
        return []
    vault = vaultpath.require_dir()
    where = {}
    for path in sorted(glob.glob(os.path.join(vault, "**", "Gw.dat"),
                                 recursive=True)):
        try:
            ar = Archive(path)
            try:
                table = file_id_table(ar)
            finally:
                ar.close()
        except Exception:
            continue
        rel = os.path.relpath(path, vault)
        for fid in want:
            if fid in table:
                where.setdefault(fid, []).append(rel)
    resolved = []
    for r in rows:
        if r.verdict == UNRESOLVED and r.file_id in where:
            r.found_in = where[r.file_id]
            resolved.append(r)
    return resolved


def tally(rows):
    out = {}
    for r in rows:
        out[r.verdict] = out.get(r.verdict, 0) + 1
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dat", default=None,
                    help="the archive to score against (default: the study dat)")
    ap.add_argument("--find-missing", action="store_true",
                    help="search every vault Gw.dat for UNRESOLVED file ids")
    ap.add_argument("--flag-origin", action="store_true",
                    help="call out rows whose arrival point is (0,0)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    rows = census(dat=args.dat)
    if args.find_missing:
        find_missing(rows)

    if args.json:
        print(json.dumps([r.as_dict() for r in rows], indent=1))
        return 0

    print(f"{'map':>5}  {'verdict':<12} {'hits':>4} {'plane':>5}  name")
    for r in rows:
        print(f"{r.map_id:>5}  {r.verdict:<12} {r.hits:>4} {r.plane:>5}  "
              f"{(r.name or '')[:50]}")
        if r.found_in:
            print(f"{'':>5}  ...file 0x{r.file_id:X} resolves in: "
                  f"{', '.join(r.found_in)}")

    counts = tally(rows)
    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    walk = sum(counts.get(k, 0) for k in WALKABLE)
    print(f"{walk} of {len(rows)} map rows put a body on walkable ground on "
          f"the plane the row declares")

    if args.flag_origin:
        acc = [r for r in rows if r.is_origin and r.verdict in WALKABLE]
        if acc:
            print(f"\n{len(acc)} row(s) PASS on a (0,0) placeholder -- the "
                  f"origin happens to be walkable, so the green is an accident "
                  f"and not a measured arrival point:")
            for r in acc:
                print(f"  map {r.map_id}  {r.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
