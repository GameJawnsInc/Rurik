"""Detect NO-CLIP offline: did the body walk ground our mesh calls blocked?

WHY. FINDINGS 1n.2 records no-clip as a harm "a displacement counter cannot see
BY CONSTRUCTION" -- it is a legal walk at 288 u/s with both m_point and its
stamp advancing -- and every arm since has deferred the row to the operator's
eyes. On 2026-08-28 that dependency failed exactly the way an unwritten
instrument fails: the operator was handed a bare command, was never told to
watch, and the B2 row came back UNSCORED.

METHOD. Take the LOCAL copy (the body the player sees, driven by the client's
own solver) and walk its sampled positions in order. For each consecutive pair
run pathmap.clip() -- the same primitive the server's own geometry gate uses --
and if the straight chord stops short, the body crossed ground our mesh calls
blocked.

FOUR THINGS THAT WOULD MAKE THIS LIE, ALL HANDLED:
  * a WARP is not a walk. Steps whose position stamp did not advance are the
    displacement signature (1i.6) and are excluded outright.
  * a LONG chord between two sparse samples cuts corners the real walk went
    around, which is a false positive with nothing to do with no-clip. Chords
    are capped at --max-chord (default 400 u) and the discard count is printed.
  * OUR MESH IS NOT THE CLIENT'S. It agrees on ~35.7% of clipped stops
    (ROUTER.md 3), so a raw count is a CANDIDATE count, not a verdict. Which is
    why this tool is calibrated against arms whose answer is already known
    rather than read absolutely.
  * a stopped body samples the same point repeatedly. Chords under 1 u are
    dropped so standing still cannot manufacture agreement.

CALIBRATION IS THE POINT. Run it on k1-treatment (shipped: clicks REFUSED, so
the body is entirely client-pathed and should be CLEAN) and on k2 (the echo,
where the operator REPORTED no-clip). A detector that cannot separate those two
is not measuring no-clip, and says so.

Read-only. Stdlib + this repo's own pathmap.
"""
import argparse
import math
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for p in ("toolkit", "toolkit/clientscan/movehook", "toolkit/mapdata"):
    sys.path.insert(0, os.path.join(r"C:/gd/Rurik", p))
import readhook                                                   # noqa: E402
_f = readhook._f


def load_mesh(fid):
    from pathmap import PathingMap
    from archive import Archive, file_id_table
    ar = Archive()
    return PathingMap.load(fid, archive=ar, table=file_id_table(ar))


def local_copy(cap, names):
    """The DENSEST object -- the client-solver-driven body, not the sync twin.

    Chosen by record count rather than by id, because one agent id names two
    objects (1i.1) and an id filter interleaves them.
    """
    best, out = -1, None
    for addr, seq in readhook._by_object(cap, names).items():
        if len(seq) > best:
            best, out = len(seq), (addr, seq)
    return out


def scan(binpath, pm, max_chord, tol):
    cap = readhook.Capture(binpath)
    names = readhook.site_names(cap)
    addr, seq = local_copy(cap, names)
    steps = blocked = skipped_warp = skipped_long = 0
    worst = 0.0
    total_short = 0.0
    path = 0.0
    prev = None
    for r in seq:
        x, y = _f(r["point"][0]), _f(r["point"][1])
        st = r["ptime"]
        if not (math.isfinite(x) and math.isfinite(y)):
            prev = None
            continue
        if prev is not None:
            ax, ay, ast = prev
            d = math.hypot(x - ax, y - ay)
            if d < 1.0:
                pass
            elif st == ast:
                skipped_warp += 1          # a displacement, not a walk
            elif d > max_chord:
                skipped_long += 1
            else:
                steps += 1
                path += d
                sx, sy = pm.clip(ax, ay, x, y)
                short = math.hypot(x - sx, y - sy)
                if short > tol:
                    blocked += 1
                    total_short += short
                    worst = max(worst, short)
        prev = (x, y, st)
    return dict(obj=addr, steps=steps, blocked=blocked, worst=worst,
                total_short=total_short, path=path,
                warp=skipped_warp, long=skipped_long)


ap = argparse.ArgumentParser()
ap.add_argument("--map", default="0x287B3")
ap.add_argument("--max-chord", type=float, default=400.0)
ap.add_argument("--tol", type=float, default=32.0)
ap.add_argument("arms", nargs="+")
a = ap.parse_args()

pm = load_mesh(int(a.map, 16))
print(f"mesh {a.map}   chord cap {a.max_chord:.0f} u   tolerance {a.tol:.0f} u\n")
print(f"{'arm':<14s} {'steps':>6s} {'blocked':>8s} {'rate':>7s} "
      f"{'worst':>8s} {'blocked u/1000u':>16s}   {'dropped(warp/long)':>18s}")
for arm in a.arms:
    b = f"C:/gd/Rurik/vault/research/movecode/{arm}/movehook.bin"
    if not os.path.exists(b):
        print(f"{arm:<14s} MISSING {b}")
        continue
    r = scan(b, pm, a.max_chord, a.tol)
    rate = (100.0 * r["blocked"] / r["steps"]) if r["steps"] else 0.0
    per = (1000.0 * r["total_short"] / r["path"]) if r["path"] else 0.0
    print(f"{arm:<14s} {r['steps']:6d} {r['blocked']:8d} {rate:6.1f}% "
          f"{r['worst']:8.0f} {per:16.1f}   {r['warp']:>8d}/{r['long']:<9d}")
