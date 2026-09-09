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

SECTION 10 IS A DIFFERENT KIND OF CHECK and is worth its own note, because a
router is the one thing here that can be WRONG AND LOOK RIGHT. route() runs on
the thread that owns the world, on a 50 ms tick, and before 2026-08-13 its worst
case in the band a hostile chases in was 336 ms -- 6.6 tick periods, 11 routes in
1,500 over a whole tick, and an intermittent world freeze nobody could attribute.
That is fixed, and the measurement is repeated here rather than quoted.

The trap in checking it is that a router which quietly returns None, or returns a
path through a wall, is FASTER. So the latency number is the least of what
section 10 asserts, and never appears without four things beside it:

  * every path returned passes route()'s own consecutive-clip validity gate, over
    the whole 1,500-pair set rather than a sample;
  * the None rate is measured BEFORE and AFTER on the same pairs and must be
    equal -- a smoother that gives up is the expected failure mode;
  * path length is compared before and after, mean and worst case;
  * the sabotage is BUILT AND RUN: a route() that returns the raw unsmoothed A*
    path is faster than the real one (max 11.6 ms against 17.9) and PASSES the
    timing check, so if the length check did not go red -- it does, at a mean
    ratio of 2.80 and a worst of 52.6 -- there would be no check here at all.

The pre-fix walkable(), _string_pull() and component pre-check are reconstructed
in this file so BEFORE and AFTER are two live answers in one process, the way
test_codescan.py's §8 reproduces the old grouping inline. A number copied out of
a session log is not a control.

THE THREE TIMING CHECKS ARE NORMALISED FOR MACHINE LOAD, and that is new on
2026-09-08. This file passed 120 checks alone and failed two inside
`run_suite.py`, which runs four files at once -- not a regression and not a
collision, since nothing here is shared between processes, but a wall clock
reading the box rather than the code. The 50 ms threshold did NOT move. Each run
measures how fast the machine is while it runs (a fixed arithmetic loop that
touches nothing under test) and divides; the constants, the evidence that the
probe tracks route() across three load levels, and the two guards that keep the
correction from becoming an excuse are at CALIB_REF_MS below. The load-bearing
one is a positive control in section 10 (e): the pre-fix router is pushed
through the same estimator every run and must still blow the tick.

    python toolkit/mapdata/test_pathmap.py
    python toolkit/mapdata/test_pathmap.py --sample 60
    python toolkit/mapdata/test_pathmap.py --routes 400   # a quicker section 10
    python toolkit/mapdata/test_pathmap.py --all      # every map, minutes

MEASURED VALUES ARE KAMADAN'S, on the archive our patched client has run. A
different Gw.dat is fine -- the file id is a content key -- but if that map ever
changes shape these numbers are the alarm.
"""

import argparse
import math
import os
import random
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import (Archive, ffna_chunks, file_id_table,  # noqa: E402
                     DEFAULT_DAT, FILE_ID_HIGH_BIT)
import pathmap  # noqa: E402
from pathmap import (PathingMap, PATHING_CHUNK, SIGNATURE, VERSION,  # noqa: E402
                     TRAPEZOID_SIZE, NO_NEIGHBOUR, NO_PORTAL, BAND)
import checks  # noqa: E402

KAMADAN_FILE_ID = 0x345CC
KAMADAN_ROW = 22371
KAMADAN_CHUNK_BYTES = 199130
KAMADAN_PLANES = 39
KAMADAN_TRAPEZOIDS = 1270

# OpenTyria's static spawn for Kamadan. It was never checked against anything
# until this file; section 4 is that check.
KAMADAN_SPAWN = (-9067.0, 13218.0)

# The two map file ids the archive stores with bit 31 set. An exact-match lookup
# misses both, which is why the Pre-Searing region was written off as
# unreachable; section 6 is the regression guard on that.
PRESEARING_FILE_ID = 0x1B97D
PRESEARING_ROW = 7982
PRESEARING_PLANES = 58
PRESEARING_TRAPEZOIDS = 6120
NORTHLANDS_FILE_ID = 0x1C539
NORTHLANDS_ROW = 20118
# BIT-31 REGISTRATION IS A PROPERTY OF THE ARCHIVE GENERATION, and it stopped.
# MEASURED 2026-08-27 over four archives: 38519 and 38797 each register 25
# bit-31 ids, every one paired with its masked twin; 38833 and 38849 register
# ZERO. ArenaNet dropped the dual registration between 38797 and 38833, and the
# two map heads that carried it -- Pre-Searing and The Northlands -- were both
# rewritten in that patch, their replacement rows named by a single id.
#
# So this is not a constant, it is a per-generation expectation, and a run must
# land on one of the two KNOWN states rather than on any number. An archive that
# registered, say, 7 would be a third thing nobody has seen and is worth a red.
HIGH_BIT_IDS = 25
HIGH_BIT_IDS_38833 = 0
KNOWN_HIGH_BIT_CENSUS = (HIGH_BIT_IDS, HIGH_BIT_IDS_38833)
MEASURED_ENTRY_COUNT = 177342

ROUTE_SAMPLE = 60

MAP_FLAGS = 259

# -- section 10: the chase band ------------------------------------------
# The band enemy_move_tick actually chases in, straight out of authsrv.py:
# ENEMY_MELEE_RANGE (150) is where a hostile stops walking and starts swinging,
# AGGRO_RANGE (1200) is where it notices you at all. Routes outside it are not
# the ones that can freeze the world, so measuring them would flatter the
# result. Duplicated rather than imported: toolkit/mapdata must not grow a
# dependency on the server, and if the server's numbers ever move, this file
# saying 150..1200 out loud is what makes the divergence findable.
# AND THEY MOVED (ANIMREF-RE 40, 2026-09-02): the default chase now starts
# beyond ATTACK_REACH = 144 and parks at follow_stop_radius() = 80, so the
# walked band is 80..1200; 150 is the --legacy-npc-chase arm's stop. The
# band below is left as MEASURED -- it is a timing benchmark over routes of
# these lengths, and 150..1200 remains inside what the chase walks.
CHASE_LO, CHASE_HI = 150.0, 1200.0
TICK_MS = 50.0                 # authsrv.TICK_SECONDS, the world's whole budget
TAIL_ROUTES = 1500

# The tolerances section 10 holds the smoother to. The fix as shipped is
# answer-identical, so the MEASURED values are 1.000000 and 1.000000 -- these
# are headroom for a future bounded smoother, not a description of today. They
# are set where the raw-unsmoothed sabotage (mean 2.80, worst 52.6) still goes
# red by a wide margin, because a tolerance that the sabotage slips through is
# not a tolerance.
LENGTH_MEAN_MAX = 1.01
LENGTH_WORST_MAX = 1.25

# -- the load correction, and why a wall clock alone could not stay honest --
#
# THE 50 ms TICK IS A WALL-CLOCK BUDGET, so the three checks that hold route()
# to it are wall-clock measurements -- and a wall clock on a shared box measures
# the machine as much as the code. That is not hypothetical. On 2026-09-08
# `test_pathmap.py` PASSED 120 checks run alone and FAILED under
# `run_suite.py`, which runs four files at once; it was neither a regression nor
# a collision, because nothing here is shared between processes. It was load.
# `confirmed_over_tick`'s best-of-5 was already there for exactly this and was
# not enough: a scheduling hiccup does not survive a re-time, but SUSTAINED
# contention does -- eight busy siblings raise every route by the same factor,
# so the minimum of five is inflated too.
#
# The tempting fixes are both wrong. Raising the threshold until it passes
# throws away the check (the pre-fix worst case was 336 ms, and that is what
# this is guarding); measuring CPU time instead of wall clock does not work on
# Windows, where `time.process_time()` is updated on the ~15.6 ms scheduler
# tick and these routes take 0.5 ms -- and would not have helped anyway,
# because the inflation MEASURED below happens with cores to spare, so it is
# cache and clock contention rather than being descheduled.
#
# So the run measures how fast the box is WHILE IT RUNS, and normalises. The
# probe is a fixed arithmetic loop with no dependency on anything under test:
# if route() gets slower the probe does not, so a real regression still reddens.
# The threshold never moves -- TICK_MS stays 50.0 and the numbers compared to it
# are divided by the measured factor.
#
# MEASURED 2026-09-08, 12 cores, Python 3.14.4, over the 1,500-pair chase sweep
# on Pre-Searing, against 3, 8 and 16 busy sibling processes. The probe tracks
# route() across every load level, which is the whole claim and the reason it is
# this loop rather than a dict walk (1.35x where route read 1.81x) or a bucketed
# scan (2.49x):
#
#     load          route total   route max   this probe
#     idle (twice)     0.99x        1.15x        1.01-1.08x
#     3 siblings       1.27x        1.44x        1.27-1.36x
#     8 siblings       1.69x        1.81x        1.81-1.87x
#     16 siblings      1.67x        1.79x        1.78-1.82x
#
# CALIB_REF_MS is this machine idle -- min-of-15, whose own run-to-run spread is
# 1.05..1.09x, taken at the FLOOR of five such runs (7.560, 7.681, 7.692, 7.782,
# 7.834) so the factor sits at or just above 1.0 when nothing else is running
# and the clamp, rather than a guess, absorbs the rest. It is a property of this
# box and this interpreter, not of the code under test: on another machine or a
# faster Python it will be wrong, and the two guards below are what keep that
# from mattering. Wrong LOW is the harmless direction (the factor clamps to 1.0
# and the tick is enforced as written); wrong HIGH buys leniency, which is what
# the cap bounds and the control refuses.
#
# GUARD 1, the cap. Past LOAD_FACTOR_CAP the correction is extrapolating rather
# than measuring, and the timing checks declare a SKIP instead of passing
# something meaningless. A skip is printed and counted against the floor.
# GUARD 2, and it is the load-bearing one: the pre-fix router is re-timed
# through THIS estimator every run and must still blow the tick. A normalisation
# that had gone soft enough to excuse a genuinely slow router fails that check
# first -- see section 10 (e). At the cap the budget is 150 ms and the pre-fix
# worst case is 336..700, so the control has room to convict.
CALIB_ITERATIONS = 200000
CALIB_REPEATS = 15
CALIB_REF_MS = 7.60
LOAD_FACTOR_CAP = 3.0


def old_walkable(pm, x, y):
    """walkable() as it stood before 2026-08-13: a y band of Trapezoid objects.

    Reconstructed here, not described, so "5.82 us against 1.23" and "336 ms
    against 17.9" are differences between two answers this process computed.
    """
    for t in pm._bands.get(int(y // BAND), ()):
        if t.contains(x, y):
            return True
    return False


def old_string_pull(pm, pts):
    """_string_pull() as it stood before 2026-08-13: unbounded, clip() in order."""
    out = [pts[0]]
    i = 0
    while i < len(pts) - 1:
        j = len(pts) - 1
        while j > i + 1:
            if pm.clip(*out[-1], *pts[j]) == pts[j]:
                break
            j -= 1
        out.append(pts[j])
        i = j
    return out


class as_before:
    """Context manager putting a PathingMap back to its pre-fix behaviour.

    Three instance attributes are the whole difference, which is worth saying
    out loud: route() itself gained only the component pre-check, and giving
    every trapezoid the same component root makes that branch inert rather than
    needing a second copy of the function. So the BEFORE run below exercises the
    SAME route() body -- what changed is the three primitives underneath it.
    """

    def __init__(self, pm):
        self.pm = pm

    def __enter__(self):
        pm = self.pm
        self.saved = pm._component
        pm.walkable = lambda x, y: old_walkable(pm, x, y)
        pm._string_pull = lambda pts, budget=None, planes=None: old_string_pull(pm, pts)
        pm._component = [0] * len(pm.trapezoids)
        return pm

    def __exit__(self, *exc):
        pm = self.pm
        del pm.walkable
        del pm._string_pull
        pm._component = self.saved
        return False


def chase_pairs(pm, n, seed=8):
    """n (start, goal) pairs, both walkable, CHASE_LO..CHASE_HI apart.

    Starts are trapezoid centres so a start is always inside the mesh; goals are
    thrown at a random bearing and kept only if they land on walkable ground,
    which is what makes the set a mixture of clear lines, detours around
    obstacles and goals in another component.
    """
    rng = random.Random(seed)
    pairs = []
    guard = 0
    while len(pairs) < n and guard < n * 400:
        guard += 1
        ax, ay = rng.choice(pm.trapezoids).centre
        if not pm.walkable(ax, ay):
            continue
        ang = rng.uniform(0.0, 2.0 * math.pi)
        d = rng.uniform(CHASE_LO, CHASE_HI)
        bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
        if not pm.walkable(bx, by):
            continue
        pairs.append((ax, ay, bx, by))
    return pairs


def _calibrate():
    """Milliseconds for a fixed arithmetic loop: how fast this box is RIGHT NOW.

    Deliberately touches nothing under test -- no map, no pathmap module, no
    allocation past a couple of floats -- so it answers "how loaded is the
    machine" and never "how fast is route()". That independence is what lets the
    normalisation below stay a load correction rather than a way of excusing a
    slow router. The minimum over CALIB_REPEATS is the same estimator
    `confirmed_over_tick` uses and for the same reason.
    """
    best = None
    for _ in range(CALIB_REPEATS):
        t0 = time.perf_counter()
        a, x = 0.0, 1.0000001
        for _ in range(CALIB_ITERATIONS):
            a = a * x + 0.5
            if a > 1e6:
                a *= 1e-6
        dt = (time.perf_counter() - t0) * 1000.0
        best = dt if best is None else min(best, dt)
    return best


def measure_load():
    """How many times slower than idle this box is running. Never below 1.0.

    Clamped at 1.0 on purpose: a box faster than the reference does not earn a
    TIGHTER budget than the tick, because 50 ms is a real wall-clock deadline
    wherever the server runs. The correction only ever forgives load.
    """
    return max(1.0, _calibrate() / CALIB_REF_MS)


def sweep(pm, pairs, with_planes=False):
    """Route every pair, timing each one. Returns (milliseconds, paths, load).

    `load` is measured immediately before and immediately after and averaged, so
    it describes the box that produced THESE timings rather than the box at some
    other moment of a twelve-minute suite.
    """
    lo = measure_load()
    ms, paths = [], []
    for (ax, ay, bx, by) in pairs:
        t0 = time.perf_counter()
        p = pm.route(ax, ay, bx, by, with_planes=with_planes)
        ms.append((time.perf_counter() - t0) * 1000.0)
        paths.append(p)
    return ms, paths, (lo + measure_load()) * 0.5


def pct(xs, q):
    s = sorted(xs)
    return s[min(len(s) - 1, int(round(q * (len(s) - 1))))]


def confirmed_over_tick(pm, pairs, ms, load, repeats=5, with_planes=False):
    """The routes that REALLY cost more than a tick, re-timed best of N.

    One timing on a shared machine measures the computation and whatever else
    the box was doing. That is not a hypothetical here: this file was first run
    green at max 17.9 ms and then read 52.4 ms on the same code half an hour
    later, with four other agents' suites running in the same worktree and the
    median at 0.306 ms against an idle 0.16. A check that reddens because
    another process woke up is worse than no check, because the next person
    lowers the threshold rather than reading it.

    The minimum over repeats is the standard estimator for the cost of the work
    rather than the cost of the day: a route that genuinely spends 300 ms of CPU
    spends it every time, and a scheduling hiccup does not survive a second
    look. Only the candidates are re-timed, so a run with nothing over the tick
    pays nothing at all -- and the estimator only ever moves a number DOWN, so
    it can hide a slow route only by hiding one that is not reliably slow.

    THAT WAS NOT ENOUGH, and 2026-09-08 is the record of it: a minimum survives
    a hiccup but not SUSTAINED contention, where every one of the five repeats
    is slow by the same factor. So each re-timing is divided by a load factor
    measured at the moment it is taken -- see CALIB_REF_MS above -- and the
    comparison is against an unchanged 50 ms. `load` is the factor that was in
    force when `ms` was collected and selects the candidates; the confirmation
    re-measures, because the two happen at different moments.

    Returns (index, normalised_ms, raw_ms, load_at_confirmation) per route.
    """
    out = []
    for k, v in enumerate(ms):
        if v <= TICK_MS * load:
            continue
        ax, ay, bx, by = pairs[k]
        now = measure_load()
        best = min(_time_one(pm, ax, ay, bx, by, with_planes)
                   for _ in range(repeats))
        if best / now > TICK_MS:
            out.append((k, best / now, best, now))
    return out


def _time_one(pm, ax, ay, bx, by, with_planes=False):
    t0 = time.perf_counter()
    pm.route(ax, ay, bx, by, with_planes=with_planes)
    return (time.perf_counter() - t0) * 1000.0


def latency_table(label, ms, load):
    """Print the percentile table and return how many blew a whole tick.

    Percentiles are RAW -- what the routes actually cost on this box today --
    and the tick counts beside them are normalised, so a reader can see both the
    wall clock and the claim being made about it.
    """
    over = sum(1 for v in ms if v > TICK_MS * load)
    print(f"      {label:<8} p50 {pct(ms, .5):7.3f}  p90 {pct(ms, .9):7.3f}  "
          f"p99 {pct(ms, .99):7.3f}  p99.9 {pct(ms, .999):8.3f}  "
          f"max {max(ms):8.3f} ms = {max(ms) / (TICK_MS * load):.2f} ticks at "
          f"load {load:.2f}x, {over} over a tick, "
          f"{sum(ms) / 1000.0:.2f} s total")
    return over


def path_length(p):
    return sum(math.dist(p[i], p[i + 1]) for i in range(len(p) - 1))


def length_ratios(base, other):
    """Length of `other`'s path over `base`'s, for the pairs both routed."""
    out = []
    for a, b in zip(base, other):
        if a and b and path_length(a) > 0.0:
            out.append(path_length(b) / path_length(a))
    return out


def all_valid(pm, paths):
    """How many returned paths fail route()'s own consecutive-clip gate.

    Deliberately re-run through clip() rather than through _visible(): clip()
    walks front to back and is the implementation _sightline() was derived
    FROM, so a defect in the reordering cannot hide behind itself here.
    """
    bad = 0
    for p in paths:
        if not p:
            continue
        if any(pm.clip(*p[i], *p[i + 1]) != p[i + 1] for i in range(len(p) - 1)):
            bad += 1
    return bad

# FLOOR: 62 -- the checks that run on any Gw.dat, whatever --sample, --routes or
# --all is asked for. MEASURED on the run-dir archive, 2026-08-13: a green
# default run prints 64, and the two above the floor are the "row is the
# measured one" checks in section 6, which turn into declared skips on an
# archive with a different entry count. Everything else here is unconditional:
# 6 in section 1, 5 in section 2, 3 in section 3, 4 in section 4, 1 in section 5
# (the sample size changes how many maps that one check walks, not how many
# checks run), 8 of section 6's 10, 3 in section 7, 6 in section 8, 5 in
# section 9, and 21 in section 10 (3 + 2 + 2 + 2 + 6 + 2 + 4 across its parts
# a to g) -- `--routes` likewise changes the sample, not the count.
# Was 41 against a green 43 before section 10 existed.
# If a run scores 61, a section stopped executing and the passes above it are
# not evidence of anything.
# Floor history: 62 (green 64, two archive-conditional section-6 checks may
# skip) until 2026-08-26; section 11 (ROUTER-B4 route plane preference)
# added five checks, two behind a stacked-point search that may
# skip-declare; section 12 (ROUTER-B5 nearest_walkable) added four --
# green run 73, floor 69.
# MEASURED 2026-08-27 in BOTH archive generations: 73 checks on 38797, 68 on
# 38833. The base is the LEANER one and section 6 raises it by hand when the
# richer configuration applies -- the same shape test_archive.py uses for its
# reference rows. A flat 69 was set when only 38797 existed and called a
# perfectly healthy 38833 run "incomplete".
#
# What makes 38833 leaner is not a missing check but a MISSING SUBJECT:
# ArenaNet stopped registering bit-31 file ids after 38797 (25 -> 0), so the
# three checks about raw/masked pairing have nothing to be about. They are
# declared skips there, not silent absences.
# Section 14 (2026-09-04, MOVECODE-1z-bb, the seam-aware pull) adds nine
# unconditional checks on a synthetic bridge and four behind the Pre-Searing
# load: floor 80 -> 89, green run 93 on 38833 (5 declared skips).
# 2026-09-08, the load correction: section 10 (e) gains the positive control
# that re-times the PRE-FIX router through the same estimator, so a green run
# is 121 rather than 120 and the floor goes 116 -> 117 -- the same slack of
# FOUR against a green run that this file has always carried. What uses that
# slack is different, and deliberate: THREE of these checks -- section 10's
# tick check, section 10's sabotage arm and section 14's seam-aware timing --
# turn into declared skips on a box running past LOAD_FACTOR_CAP, and the
# control declares a fourth on a `--routes` sample too small to hold a
# pathological route. 117 is therefore the worst a healthy run can score, and
# it is reached only by a small `--routes` on a very busy box. The control does
# NOT skip for load: normalising by a bigger factor makes it harder to pass,
# not easier, so it is safe at any load and it is the check that would catch a
# correction gone soft.
LEDGER = checks.Ledger("pathing map", floor=129)   # 1z-co adds sec.17 (+8); from the green run
check = checks.adopt(LEDGER)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dat", default=DEFAULT_DAT)
    ap.add_argument("--sample", type=int, default=25,
                    help="how many maps to walk in section 5")
    ap.add_argument("--routes", type=int, default=TAIL_ROUTES,
                    help="how many chase-band routes section 10 times")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    t0 = time.perf_counter()
    pre = None            # bound by section 9's load; section 14 reads it after the archive closes
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

        # -- 6. the maps behind the bit-31 ids ---------------------------
        # These fail loudly if file_id_table() ever goes back to an
        # exact-match lookup: the id a server sends is the masked form and
        # only the raw form is in the table.
        print("\n6. The file ids stored with bit 31 set")
        raw = struct.unpack_from(
            f"<{(len(ar.read(ar.entries[1])) // 8) * 2}I", ar.read(ar.entries[1]))
        stored = {raw[i * 2] for i in range(len(raw) // 2)}
        high = {f for f in stored if f & FILE_ID_HIGH_BIT}
        # THE FLOOR RISES WITH THE SUBJECT. On a generation that registers
        # bit-31 ids there are three more checks to run -- the collision
        # invariant and the two raw/masked agreements -- so requiring them is
        # what stops a 38797 run from quietly losing them.
        if high:
            LEDGER.floor += 3
        check(len(high) in KNOWN_HIGH_BIT_CENSUS,
              "the high-bit id census is one of the two states we have seen",
              f"{len(high)} ids -- 25 on 38519/38797, 0 on 38833/38849. A third "
              f"number is a format change nobody has looked at and is worth "
              f"stopping for")
        # The invariant the mask-on-miss lookup depends on: no bit-31 id's
        # masked form is also a real id, so the two can never compete. Vacuous
        # on an archive with no bit-31 ids at all, which is why it says so.
        shadowed = {f & ~FILE_ID_HIGH_BIT for f in high} & stored
        if high:
            check(not shadowed, "no masked form collides with a real file id",
                  f"{len(shadowed)} collision(s) over {len(high)} high ids")
        else:
            LEDGER.skip("the masked-form collision invariant",
                        "this archive registers NO bit-31 ids (38833 and later),"
                        " so there is nothing for a masked form to collide with"
                        " -- the mask-on-miss lookup is simply never reached")

        for label, fid, want_row in (
                ("Pre-Searing", PRESEARING_FILE_ID, PRESEARING_ROW),
                ("The Northlands", NORTHLANDS_FILE_ID, NORTHLANDS_ROW)):
            got = table.get(fid)
            check(got is not None, f"{label} id resolves at all",
                  f"0x{fid:X} -> {got}")
            if got is None:
                continue
            # ONLY MEANINGFUL WHERE THE TWIN EXISTS. On 38833+ the raw id is
            # registered alone, so `table.get(fid | BIT31)` is None and this
            # would fail on an archive that is perfectly well formed -- the
            # functional requirement is the check above (the id RESOLVES), and
            # this one is about the pairing that older generations carried.
            if high:
                check(table.get(fid | FILE_ID_HIGH_BIT) == got,
                      f"{label} raw and masked ids agree")
            else:
                LEDGER.skip(f"{label} raw/masked agreement",
                            "no bit-31 twin is registered on this generation")
            e = next(x for x in ar.entries if x.index == got)
            check(e.flags == MAP_FLAGS, f"{label} row carries map flags",
                  f"flags {e.flags}")
            if ar.entry_count == MEASURED_ENTRY_COUNT:
                check(got == want_row, f"{label} row is the measured one",
                      f"{got}")
            else:
                LEDGER.skip(f"{label} row index",
                            f"archive has {ar.entry_count} entries, "
                            f"measured on {MEASURED_ENTRY_COUNT}")

        # -- 7. the routing graph ----------------------------------------
        # The adjacency check is the strongest thing in this file. Four
        # indices read out of one 44-byte record are checked against four
        # read out of a different record, and upstream's TL/TR/BL/BR naming
        # additionally predicts WHICH of the four answers. Nothing in our
        # decoder can force that.
        print("\n7. the trapezoid routing graph")
        links = sym = opposite = oor = 0
        for t in pm.trapezoids:
            here = [x for x in pm.trapezoids if x.plane == t.plane]
            for slot, n in enumerate(t.neighbours):
                if n == NO_NEIGHBOUR:
                    continue
                links += 1
                if n >= len(here):
                    oor += 1
                    continue
                other = here[n]
                if t.index in other.neighbours:
                    sym += 1
                want = (2, 3) if slot < 2 else (0, 1)
                if t.index in (other.neighbours[want[0]],
                               other.neighbours[want[1]]):
                    opposite += 1
        check(oor == 0, "every neighbour index is in range", f"{links} links")
        check(sym == links, "adjacency is symmetric", f"{sym}/{links}")
        check(opposite == links,
              "a top-edge link is answered across the bottom edge",
              f"{opposite}/{links}")

        print("\n8. portals")
        total_portals = sum(len(r) for r in pm.portals)
        bad_plane = sum(1 for r in pm.portals for p in r
                        if p.neighbour >= len(pm.planes))
        check(bad_plane == 0, "every portal names a plane that exists",
              f"{total_portals} portals")
        partition_ok = 0
        for pi, row in enumerate(pm.portals):
            traps = pm.portal_traps[pi]
            cover = [0] * len(traps)
            for p in row:
                for k in range(p.offset, min(p.offset + p.traps, len(cover))):
                    cover[k] += 1
            if all(c == 1 for c in cover):
                partition_ok += 1
        check(partition_ok == len(pm.portals),
              "portal slices partition each plane's portalTraps exactly",
              f"{partition_ok}/{len(pm.portals)} planes")
        # Reciprocity of the plane relation, the same argument as adjacency.
        names = {pi: {p.neighbour for p in row}
                 for pi, row in enumerate(pm.portals)}
        rel = [(a, b) for a, s in names.items() for b in s]
        recip = sum(1 for a, b in rel if a in names.get(b, ()))
        check(recip == len(rel), "the plane-to-plane relation is reciprocal",
              f"{recip}/{len(rel)}")
        # The pairing, and the reason cross-plane routing is a decode rather
        # than a heuristic: exactly two portals share a pair id, never one or
        # three, and the partner is always across the boundary named.
        groups = {}
        for row in pm.portals:
            for p_ in row:
                groups.setdefault(p_.pair_id, []).append(p_)
        sizes = {len(v) for v in groups.values()}
        check(sizes == {2}, "every pair id is shared by exactly two portals",
              f"group sizes {sorted(sizes)}, {len(groups)} pairs")
        crossed = sum(1 for v in groups.values() if len(v) == 2
                      and v[0].plane == v[1].neighbour
                      and v[1].plane == v[0].neighbour)
        check(crossed == len(groups),
              "each pair spans the planes its two halves name",
              f"{crossed}/{len(groups)}")
        # ArenaNet's own assert, from PathDir.cpp.
        stray = 0
        for t in pm.trapezoids:
            n = len(pm.portals[t.plane])
            for k in (t.portal_left, t.portal_right):
                if k != NO_PORTAL and k >= n:
                    stray += 1
        check(stray == 0,
              "m_trapezoid->portalLeft/Right < pathMap.portalCount",
              "the client's own invariant")

        print("\n9. routing finds walkable paths around obstacles")
        random.seed(7)
        pool = pm.trapezoids
        blocked = routed = clean = 0
        for _ in range(60000):
            a, b = random.choice(pool), random.choice(pool)
            ax, ay = a.centre
            bx, by = b.centre
            if pm.clip(ax, ay, bx, by) == (bx, by):
                continue                      # straight line already works
            blocked += 1
            path = pm.route(ax, ay, bx, by)
            if path:
                routed += 1
                if all(pm.clip(*path[i], *path[i + 1]) == path[i + 1]
                       for i in range(len(path) - 1)):
                    clean += 1
            if blocked >= ROUTE_SAMPLE:
                break
        check(routed > blocked // 2, "most blocked pairs are routable",
              f"{routed} of {blocked} sampled")
        # The load-bearing one: a path we return must be walkable end to end.
        # Returning nothing is allowed -- planes are fragmented without the
        # cross-plane links -- but returning a path through a wall is not.
        check(clean == routed, "EVERY returned path is walkable end to end",
              f"{clean}/{routed}")

        pre = PathingMap.load(PRESEARING_FILE_ID, archive=ar, table=table)
        check(len(pre.planes) == PRESEARING_PLANES, "Pre-Searing plane count",
              f"{len(pre.planes)}")
        check(len(pre.trapezoids) == PRESEARING_TRAPEZOIDS,
              "Pre-Searing trapezoid count", f"{len(pre.trapezoids)}")
        bad = [t for t in pre.trapezoids
               if t.y_top < t.y_bottom
               or t.x_top_left > t.x_top_right
               or t.x_bottom_left > t.x_bottom_right]
        check(not bad, "Pre-Searing trapezoids are well formed",
              f"{len(bad)} malformed")

        # -- 10. the routing tail ----------------------------------------
        # Pre-Searing rather than Kamadan on purpose: 6,120 trapezoids in 15
        # components against 1,270 in 4, so it is the map where the smoother
        # blew a tick and where a failed search is expensive. Kamadan never
        # exceeded 35 ms even before the fix.
        print("\n10. route() latency in the chase band")

        # (a) the reordered line test asks EXACTLY clip()'s samples. The whole
        #     saving is that a blocked line is refused early, and the cheapest
        #     way to be "fast" would be to look at fewer points -- which would
        #     approve a path through a wall. So capture what each one asks and
        #     compare the sets, on a segment that is walkable end to end (a
        #     blocked one stops both early and proves nothing).
        seg = None
        rng10 = random.Random(21)
        for _ in range(4000):
            ax, ay = rng10.choice(pre.trapezoids).centre
            ang, d = rng10.uniform(0, 2 * math.pi), rng10.uniform(300.0, 900.0)
            bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
            if pre.clip(ax, ay, bx, by) == (bx, by):
                seg = (ax, ay, bx, by)
                break
        asked = []
        real_walkable = pre.walkable
        pre.walkable = lambda x, y: (asked.append((x, y)),
                                     real_walkable(x, y))[1]
        pre.clip(*seg)
        clip_pts = list(asked)
        asked.clear()
        pre._sightline(*seg)
        sight_pts = list(asked)
        del pre.walkable
        check(sorted(clip_pts) == sorted(sight_pts) and len(clip_pts) > 8,
              "_sightline samples exactly the points clip() samples",
              f"{len(clip_pts)} points on a {math.dist(seg[:2], seg[2:]):.0f} "
              f"unit segment")
        # ... and the comparison above is only a check if it can refuse. A
        # reordering that dropped every other sample is the fast wrong answer.
        check(sorted(clip_pts) != sorted(sight_pts[::2]),
              "that comparison refuses a line test that skips samples",
              f"{len(sight_pts[::2])} of {len(clip_pts)} would have passed")
        check(clip_pts != sight_pts,
              "and the ORDER really is different, so the saving is real",
              f"first sample {sight_pts[0] != clip_pts[0]} differs")

        # (b) the verdict, over real segments, with both answers present.
        agree = vis_yes = vis_no = 0
        for _ in range(1200):
            ax, ay = rng10.choice(pre.trapezoids).centre
            ang, d = rng10.uniform(0, 2 * math.pi), rng10.uniform(50.0, 2500.0)
            bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
            want = pre.clip(ax, ay, bx, by) == (bx, by)
            got = pre._visible(ax, ay, bx, by)
            agree += (want == got)
            vis_yes += bool(want)
            vis_no += (not want)
        check(agree == 1200, "_visible agrees with clip() on every segment",
              f"{agree}/1200")
        check(vis_yes > 50 and vis_no > 50,
              "and both answers occurred, so that was not one answer repeated",
              f"{vis_yes} visible, {vis_no} blocked")

        # (c) walkable() is now a SECOND point test, over a 2-D bucket of flat
        #     floats; containing() still runs the first one over Trapezoid
        #     objects. They must agree everywhere, which is a claim the geometry
        #     can refute -- and does, if the bucketing loses a trapezoid whose
        #     x span straddles a cell edge.
        wxs = [v for t in pre.trapezoids
               for v in (t.x_bottom_left, t.x_top_right)]
        wys = [v for t in pre.trapezoids for v in (t.y_bottom, t.y_top)]
        hit = miss = disagree = 0
        for _ in range(120000):
            x = rng10.uniform(min(wxs) - 600.0, max(wxs) + 600.0)
            y = rng10.uniform(min(wys) - 600.0, max(wys) + 600.0)
            w = pre.walkable(x, y)
            if w != bool(pre.containing(x, y)):
                disagree += 1
            hit += bool(w)
            miss += (not w)
        check(disagree == 0,
              "walkable() and containing() agree on every point",
              f"{disagree} of 120,000 disagree")
        check(hit > 1000 and miss > 1000,
              "and both answers occurred over the sample",
              f"{hit} walkable, {miss} not")

        # -- the sweep ---------------------------------------------------
        pairs = chase_pairs(pre, args.routes)
        print(f"    {len(pairs)} pairs, {CHASE_LO:.0f}..{CHASE_HI:.0f} units "
              f"apart, on a {TICK_MS:.0f} ms tick")
        # This section is the 2026-08-13 PERFORMANCE fix's own control --
        # "nothing changed an answer" -- so it runs with the seam term OFF:
        # MOVECODE-1z-bb's seam-aware pull changes answers BY DESIGN (a route
        # that used to cut through a bridge deck now goes round), and section
        # 14 owns that census. With it on here, 12 of 1,500 paths differed and
        # the None count fell 48 -> 38, which is the seam term, not the fix.
        saved10 = pathmap.SEAM_AWARE_ROUTE
        pathmap.SEAM_AWARE_ROUTE = False
        with as_before(pre):
            before_ms, before_paths, load_before = sweep(pre, pairs)
        after_ms, after_paths, load_after = sweep(pre, pairs)
        over_before = latency_table("BEFORE", before_ms, load_before)
        over_after = latency_table("AFTER", after_ms, load_after)

        # (d) the component pre-check answers None without searching. It may
        #     only do that where the search would have failed anyway, so every
        #     pair it short-circuits must be one the pre-fix code also refused.
        skipped = wrong = 0
        comp = pre._component
        for k, (ax, ay, bx, by) in enumerate(pairs):
            starts, goals = pre.containing(ax, ay), pre.containing(bx, by)
            if not starts or not goals:
                continue
            si = pre._flat_index(starts[0])
            gset = {pre._flat_index(g) for g in goals}
            if si in gset:
                continue
            if all(comp[g] != comp[si] for g in gset):
                skipped += 1
                if before_paths[k] is not None:
                    wrong += 1
        check(wrong == 0,
              "every route the component pre-check skips was already None",
              f"{skipped} skipped, {wrong} of them had a path before")
        check(skipped > 0,
              "and it skipped some, so that was not a vacuous claim",
              f"{skipped} of {len(pairs)}")

        # (e) the four claims that make a faster router safe.
        bad_after = all_valid(pre, after_paths)
        check(bad_after == 0,
              "EVERY path returned passes route()'s own clip gate",
              f"{sum(1 for p in after_paths if p)} paths, {bad_after} bad")
        none_before = sum(1 for p in before_paths if p is None)
        none_after = sum(1 for p in after_paths if p is None)
        check(none_after == none_before,
              "the None rate did not rise",
              f"{none_before} before, {none_after} after")
        differ = sum(1 for a, b in zip(before_paths, after_paths) if a != b)
        check(differ == 0,
              "and not one path differs from what the old code returned",
              f"{differ} of {len(pairs)}")
        ratios = length_ratios(before_paths, after_paths)
        mean_r = sum(ratios) / len(ratios)
        check(mean_r <= LENGTH_MEAN_MAX and max(ratios) <= LENGTH_WORST_MAX,
              f"path length within tolerance (mean <= {LENGTH_MEAN_MAX}, "
              f"worst <= {LENGTH_WORST_MAX})",
              f"mean {mean_r:.6f}, worst {max(ratios):.6f} over {len(ratios)}")
        # THE POSITIVE CONTROL FOR THE LOAD CORRECTION, and it runs first
        # because the check under it means nothing without it. Everything the
        # normalisation could get wrong shows up here as a green that should be
        # red: put the PRE-FIX router back, take the pair it was slowest on, and
        # push it through the same best-of-N-over-measured-load estimator. A
        # router that really does blow the tick has to still blow it. The
        # measured margin is wide -- 682 ms idle against a 50 ms tick, 13.6x --
        # so this is not a knife-edge control, and at LOAD_FACTOR_CAP it is
        # still 4.5x.
        worst_k = max(range(len(before_ms)), key=lambda i: before_ms[i])
        if before_ms[worst_k] < 4.0 * TICK_MS * load_before:
            # The same lesson `ratio` below is annotated with, from the other
            # side: the pathological pairs are ~1% of the set, so a small
            # `--routes` can hold none of them and the control would be asking
            # a mild route to look pathological. MEASURED: 13.4 ticks at the
            # default 1,500 pairs, 1.3 at `--routes 400`.
            LEDGER.skip("the load correction's positive control",
                        f"the pre-fix arm's worst pair only reached "
                        f"{before_ms[worst_k]:.0f} ms over {len(pairs)} routes,"
                        " which is not a pathological route to convict")
        else:
            with as_before(pre):
                ax, ay, bx, by = pairs[worst_k]
                load_ctl = measure_load()
                ctl_ms = min(_time_one(pre, ax, ay, bx, by)
                             for _ in range(3)) / load_ctl
            check(ctl_ms > TICK_MS,
                  "a genuinely slow router STILL blows the tick through this "
                  "estimator, so the load correction has not softened it away",
                  f"the pre-fix code on its worst pair ({worst_k}) reads "
                  f"{ctl_ms:.1f} ms = {ctl_ms / TICK_MS:.1f} ticks after "
                  f"normalising by a measured {load_ctl:.2f}x")

        if load_after > LOAD_FACTOR_CAP:
            # Not a pass and not a fail: on a box this busy the wall clock is
            # not measuring route(), and the correction above is extrapolating
            # rather than measuring. Declared, printed, and counted against the
            # floor -- never silent.
            LEDGER.skip("the 50 ms tick over the chase-band sweep",
                        f"the box is running {load_after:.2f}x slower than the "
                        f"idle reference, past the {LOAD_FACTOR_CAP:.1f}x this "
                        "correction is trusted to")
            confirmed = []
        else:
            confirmed = confirmed_over_tick(pre, pairs, after_ms, load_after)
            check(not confirmed,
                  "no route in the sweep blew a whole 50 ms tick",
                  f"{over_after} candidate(s) re-timed, {len(confirmed)} "
                  f"confirmed; max {max(after_ms):.1f} ms raw = "
                  f"{max(after_ms) / load_after:.1f} ms at a measured "
                  f"{load_after:.2f}x load")
        for k, best, raw, ld in confirmed[:4]:
            print(f"        pair {k}: {best:.1f} ms on the best of 5 "
                  f"({raw:.1f} raw at {ld:.2f}x)")
        # The other side of it: without this, a BEFORE reconstruction that had
        # quietly stopped reconstructing anything would make the AFTER numbers
        # look like a victory over nothing.
        #
        # It is a TOTAL rather than a maximum, and that is the whole design.
        # The first version asserted `max(before_ms) > 3 * TICK_MS` and it was
        # wrong in a way worth recording: the pathological pairs are ~1% of the
        # set, so at `--routes 400` the sample does not contain one, the pre-fix
        # worst case reads 108 ms instead of 301, and the check went red in
        # every sabotage run below -- including the one that broke nothing at
        # all, where it was the ONLY red and would have been read as the catch.
        # A check that reddens on sample size is not measuring the sabotage.
        # Totals are stable where maxima are not: MEASURED at 3.77x, 4.20x,
        # 6.14x and 5.98x over 200, 400, 800 and 1,500 pairs.
        ratio = sum(before_ms) / sum(after_ms)
        check(ratio >= 2.5,
              "the pre-fix code was materially slower over the same pairs, so "
              "the fix measured something real",
              f"{sum(before_ms) / 1000.0:.2f} s against "
              f"{sum(after_ms) / 1000.0:.2f} s, {ratio:.2f}x; "
              f"{over_before} of {len(pairs)} over a tick, worst "
              f"{max(before_ms) / TICK_MS:.1f} ticks")

        # (f) THE SABOTAGE, built and run. A router that does not smooth at all
        #     is FASTER than the real one -- so if the timing table were the
        #     whole check, this would read as a further win. It is caught by
        #     length and by nothing else in the timing half.
        real_pull = pre._string_pull
        pre._string_pull = lambda pts, budget=None, planes=None: list(pts)
        raw_ms, raw_paths, load_raw = sweep(pre, pairs)
        del pre._string_pull
        latency_table("RAW-SAB", raw_ms, load_raw)
        raw_ratios = length_ratios(after_paths, raw_paths)
        raw_mean, raw_worst = (sum(raw_ratios) / len(raw_ratios),
                               max(raw_ratios))
        if load_raw > LOAD_FACTOR_CAP:
            LEDGER.skip("SABOTAGE (no smoothing) passes the timing check",
                        f"the box is running {load_raw:.2f}x slower than the "
                        f"idle reference, past the {LOAD_FACTOR_CAP:.1f}x this "
                        "correction is trusted to")
        else:
            pre._string_pull = lambda pts, budget=None, planes=None: list(pts)
            raw_confirmed = confirmed_over_tick(pre, pairs, raw_ms, load_raw)
            del pre._string_pull
            check(not raw_confirmed,
                  "SABOTAGE (no smoothing) passes the timing check",
                  f"max {max(raw_ms):.1f} ms against the real "
                  f"{max(after_ms):.1f}, {len(raw_confirmed)} confirmed over a "
                  f"tick at a measured {load_raw:.2f}x load")
        check(raw_mean > LENGTH_MEAN_MAX and raw_worst > LENGTH_WORST_MAX,
              "and is caught by the length check, which is therefore real",
              f"mean {raw_mean:.3f} > {LENGTH_MEAN_MAX}, "
              f"worst {raw_worst:.1f} > {LENGTH_WORST_MAX}")

        # (g) PULL_SAMPLE_BUDGET. It is set above anything measured, so the
        #     sweep above never touched it -- which means the sweep says
        #     nothing about what happens when it does. Force it down and check
        #     the degradation is the one claimed: longer paths, never invalid
        #     ones.
        spend, counter = [], [0]
        real_sight = pre._sightline

        def counting_sightline(*a):
            ok, used = real_sight(*a)
            counter[0] += used
            return ok, used

        def watched_pull(pts, budget=None, planes=None):
            counter[0] = 0
            out = real_pull(pts, budget, planes)
            spend.append(counter[0])
            return out

        pre._sightline = counting_sightline
        pre._string_pull = watched_pull
        sweep(pre, pairs)              # timings unused here; (g) is about spend
        del pre._sightline
        del pre._string_pull
        check(max(spend) < pathmap.PULL_SAMPLE_BUDGET,
              "nothing in the sweep reaches PULL_SAMPLE_BUDGET",
              f"worst pull spent {max(spend)} of "
              f"{pathmap.PULL_SAMPLE_BUDGET} samples")
        saved_budget = pathmap.PULL_SAMPLE_BUDGET
        try:
            pathmap.PULL_SAMPLE_BUDGET = 20
            tight_ms, tight_paths, _ = sweep(pre, pairs)
        finally:
            pathmap.PULL_SAMPLE_BUDGET = saved_budget
        longer = sum(1 for a, b in zip(after_paths, tight_paths)
                     if a and b and path_length(b) > path_length(a) + 1e-9)
        check(longer > 0,
              "a budget of 20 really does bite, so (g) is not vacuous",
              f"{longer} paths got longer")
        check(all_valid(pre, tight_paths) == 0,
              "and a truncated smoother still returns only walkable paths",
              f"{sum(1 for p in tight_paths if p)} paths, 0 bad")
        check(pathmap.PULL_SAMPLE_BUDGET == saved_budget,
              "the budget was put back", f"{pathmap.PULL_SAMPLE_BUDGET}")

    pathmap.SEAM_AWARE_ROUTE = saved10          # section 10's control is over
    print("\n11. route() plane preference and corridor planes (ROUTER-B4)")
    # The 2026-08-26 run-2 defect: endpoint selection took containing()[0]
    # blind, and on stacked geometry that routed a click to the wrong
    # surface (a twelve-waypoint island tour to the terrain under a prop).
    # (a) with_planes agrees with the plain call and parallels the path.
    rng11 = random.Random(11)
    routed_n = 0
    agree = True
    para = True
    ends_ok = True
    tries = 0
    while routed_n < 20 and tries < 400:
        tries += 1
        a = rng11.choice(pre.trapezoids).centre
        b = rng11.choice(pre.trapezoids).centre
        plain = pre.route(a[0], a[1], b[0], b[1])
        both = pre.route(a[0], a[1], b[0], b[1], with_planes=True)
        if plain is None:
            if both is not None:
                agree = False
            continue
        if both is None:
            agree = False
            continue
        path, planes = both
        routed_n += 1
        if path != plain:
            agree = False
        if len(planes) != len(path):
            para = False
        if (planes[0] not in {t.plane for t in pre.containing(*path[0])}
                or planes[-1] not in
                {t.plane for t in pre.containing(*path[-1])}):
            ends_ok = False
    check(routed_n >= 20,
          "twenty routed pairs found for the with_planes comparison",
          f"{routed_n} in {tries} draws")
    check(agree, "with_planes returns the SAME path as the plain call",
          "the aux planes must be a decoration, never a behavior change")
    check(para and ends_ok,
          "planes parallel the path and its endpoints' planes are real",
          "each end's plane must belong to a trapezoid actually "
          "containing that point")
    # (b) preference picks the named surface on stacked ground.
    stacked = None
    for t in pre.trapezoids:
        cx, cy = t.centre
        here = pre.containing(cx, cy)
        if len({c.plane for c in here}) >= 2:
            stacked = (cx, cy, sorted({c.plane for c in here}))
            break
    if stacked is None:
        LEDGER.skip("plane preference on stacked ground",
                    "no stacked point found on Pre-Searing")
    else:
        sx, sy, splanes = stacked
        got = []
        for want in splanes[:2]:
            r = pre.route(sx, sy, sx, sy, start_plane=want,
                          goal_plane=want, with_planes=True)
            got.append(None if r is None else r[1])
        check(got[0] == [splanes[0], splanes[0]]
              and got[1] == [splanes[1], splanes[1]],
              "start/goal preference selects the named surface of a "
              "stacked point",
              f"point ({sx:.0f},{sy:.0f}) planes {splanes[:2]} -> {got}")
        # an unmatched preference falls back rather than refusing.
        bogus = max(splanes) + 1000
        r = pre.route(sx, sy, sx, sy, start_plane=bogus, goal_plane=bogus)
        check(r is not None,
              "an unmatchable preference falls back to all candidates",
              "prefer semantics, same contract as plane_at(prefer=): "
              "refusing would turn a hint into a gate")

    print("\n12. nearest_walkable (ROUTER-B5)")
    # (a) an already-walkable point comes back at zero distance.
    wt = pre.trapezoids[0].centre
    nw = pre.nearest_walkable(wt[0], wt[1], 16.0)
    check(nw is not None and nw[2] == 0.0
          and (nw[0], nw[1]) == (wt[0], wt[1]),
          "an on-mesh point is its own nearest at distance zero",
          f"{nw}")
    # (b) step off a real edge and be led back: walk outward from a
    # trapezoid centre until walkable() goes false, then ask.
    found = None
    for t in pre.trapezoids:
        cx, cy = t.centre
        for d in range(4, 13, 4):
            if not pre.walkable(cx + d, cy):
                found = (cx + d, cy, d)
                break
        if found:
            break
    check(found is not None,
          "an off-mesh probe point within the snap radius exists",
          f"{found}")
    if found:
        px, py, d0 = found
        nw = pre.nearest_walkable(px, py, 16.0)
        check(nw is not None and nw[2] <= d0
              and pre.walkable(nw[0], nw[1]),
              "the nearest point is walkable and no farther than the "
              "step off the edge", f"stepped {d0}, got {nw}")
    # (c) the middle of nowhere refuses.
    check(pre.nearest_walkable(9e6, 9e6, 16.0) is None,
          "a point with nothing in radius returns None",
          "refuse-to-guess: the caller must handle a true hole")

    # (d) THE DISTANCE IS THE EXACT EUCLIDEAN NEAREST, 2026-08-29.
    #
    # It used to clamp y into the trapezoid's span and then x into its edges
    # AT THAT Y -- an axis clamp, which is the true nearest only when the edge
    # it lands on is axis-aligned. Against a SLANTED edge it walks along y and
    # then along x instead of projecting perpendicularly, and the error is
    # unbounded in the radius: measured over r7's 67 off-mesh endpoints
    # against dense boundary sampling, it over-reported by up to 2.967x
    # (77.43 u where the truth is 26.10 u) and by 64.91 u absolute.
    # `noclipscore.py` quotes this as "how far off-mesh", so the error rode
    # into every depth an r6/r6b-era scoring pass published.
    #
    # A SYNTHETIC TRAPEZOID, because the property is geometric and a real mesh
    # cannot isolate it: one 45-degree edge, and a probe point off it.
    import pathmap as _pm
    slant = _pm.Trapezoid(plane=0, index=0, y_top=100.0, y_bottom=0.0,
                          x_top_left=100.0, x_top_right=200.0,
                          x_bottom_left=0.0, x_bottom_right=100.0)
    # P sits off the left edge, which runs (0,0) -> (100,100). The exact
    # nearest point is the perpendicular foot; the axis clamp gives the
    # horizontal hit instead, which is farther by a factor of sqrt(2).
    px, py = 0.0, 50.0
    qx, qy, d = _pm._nearest_on_trapezoid(slant, px, py)
    import math as _math
    exact = 50.0 / _math.sqrt(2.0)          # perpendicular distance to y = x
    check(abs(d - exact) < 1e-9,
          f"12d. the nearest point on a SLANTED edge is the perpendicular "
          f"foot ({exact:.3f} u)",
          f"got {d:.6f} at ({qx:.3f},{qy:.3f}) -- an axis clamp gives "
          f"50.000, which is the shipped bug")
    check(abs(qx - 25.0) < 1e-9 and abs(qy - 25.0) < 1e-9,
          "12d. and it is the foot itself, not the horizontal hit",
          f"got ({qx:.6f},{qy:.6f}), expected (25,25); the axis clamp "
          f"returns (50,50)")
    # THE KNOWN-BAD ARM, stated as the arithmetic it replaced: the old
    # expression, on this same trapezoid, must produce the WRONG answer -- or
    # this check is pinning a distinction that never existed.
    cy_old = 50.0                       # y clamped into [0,100] -- unchanged
    xl_old = slant.x_bottom_left + (cy_old / 100.0) * (
        slant.x_top_left - slant.x_bottom_left)
    d_old = abs(xl_old - px)            # x clamped to the left edge at that y
    check(abs(d_old - 50.0) < 1e-9 and d_old > d * 1.4,
          "12d. CONTROL: the OLD axis clamp reads 50.000 u here, 1.41x the "
          "truth",
          f"old {d_old:.6f} vs exact {d:.6f} -- if these agree, the fixture "
          f"no longer has a slanted edge and the check proves nothing")
    # (e) THE RETURNED DISTANCE DESCRIBES THE RETURNED POINT. The boundary
    # nudge used to move the point AFTER the distance was recorded, so a
    # caller got a post-nudge point beside a pre-nudge distance.
    # Probe from each trapezoid's OWN right edge rather than a fixed step off
    # its centre -- these trapezoids are hundreds of units wide, so centre+12
    # is still inside and the first draft of this check found ONE probe and
    # would have passed vacuously.
    bad = 0
    tried = 0
    for t in pre.trapezoids[:600]:
        my = (t.y_top + t.y_bottom) * 0.5
        span = t.y_top - t.y_bottom
        f = 0.0 if span <= 0.0 else (my - t.y_bottom) / span
        right = t.x_bottom_right + f * (t.x_top_right - t.x_bottom_right)
        for step in (0.5, 2.0, 8.0):
            px, py = right + step, my
            if pre.walkable(px, py):
                continue
            nw = pre.nearest_walkable(px, py, 16.0)
            if not nw:
                continue
            tried += 1
            if abs(math.hypot(nw[0] - px, nw[1] - py) - nw[2]) > 1e-6:
                bad += 1
            break
    check(tried >= 20,
          f"12e. enough boundary probes to score the point/distance pairing "
          f"({tried})",
          "too few off-mesh probes found -- the check below would be vacuous")
    check(bad == 0,
          "12e. every returned distance is the distance to the returned point",
          f"{bad} of {tried} disagree -- the nudge moved the point after the "
          f"distance was taken")

    print("\n13. the corner pull (MOVECODE R5's backtrack)")
    # THE DEFECT, in one sentence: _shared_edge answers the MIDPOINT of the
    # interval two trapezoids share, so a body standing near one END of a long
    # shared edge was routed to the middle of it before going on. On map 280
    # trapezoid 531 borders the corridor 1921 along x in [448, 3936]; the
    # operator, standing at x = 3367 and clicking east, was sent 1,176 units
    # WEST first -- "the second click would make me path back to the original
    # position of the first click" (R5, 2026-08-28).
    #
    # Every check here is run BOTH WAYS: with the pull on, and with
    # CORNER_PULL_ROUNDS = 0, which restores the midpoint behaviour exactly.
    # A fix whose control cannot reproduce the bug is not tested, it is
    # asserted -- and this one CAN, which is what makes the rest evidence.
    # Its OWN archive handle: `ar` is closed by the time this section runs, and
    # a closed handle raises inside load() -- which the skip path would then
    # report as "map 280 is not in this archive", a false statement about the
    # content dressed as a measurement.
    m280 = None
    try:
        with Archive() as ar13:
            m280 = pathmap.PathingMap.load(0x287B3, archive=ar13,
                                           table=file_id_table(ar13))
    except Exception as exc:                                  # noqa: BLE001
        LEDGER.skip("the corner pull",
                    f"map 280 (0x287B3) did not load from this archive: {exc}")
    if m280 is not None:
        O, D = (3367.5, 6965.5), (7404.4, 4865.1)

        def first_leg_cos(pm_, o, d):
            r = pm_.route(o[0], o[1], d[0], d[1])
            if not r or len(r) < 2:
                return None, r
            wx, wy = r[1][0] - o[0], r[1][1] - o[1]
            cx, cy = d[0] - o[0], d[1] - o[1]
            n = math.hypot(wx, wy)
            if n <= 1.0:
                return 1.0, r
            return (cx * wx + cy * wy) / (math.hypot(cx, cy) * n), r

        saved = pathmap.CORNER_PULL_ROUNDS
        try:
            pathmap.CORNER_PULL_ROUNDS = 0
            cos_mid, path_mid = first_leg_cos(m280, O, D)
            pathmap.CORNER_PULL_ROUNDS = saved
            cos_new, path_new = first_leg_cos(m280, O, D)
        finally:
            pathmap.CORNER_PULL_ROUNDS = saved
        # (a) THE CONTROL. Without the pull the specimen must still be broken,
        # or this section is measuring a map that no longer poses the question.
        check(cos_mid is not None and cos_mid < -0.5,
              "CONTROL: with the pull off, the specimen still routes BACKWARD",
              f"first-leg cos {cos_mid} (the midpoint rule; must stay < -0.5)")
        # (b) the fix.
        check(cos_new is not None and cos_new > 0.0,
              "with the pull on, the first leg points AT the click",
              f"first-leg cos {cos_new} against {cos_mid} unpulled")
        # (c) it may not buy that with length.
        if path_mid and path_new:
            lm = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                     for a, b in zip(path_mid, path_mid[1:]))
            ln = sum(math.hypot(b[0] - a[0], b[1] - a[1])
                     for a, b in zip(path_new, path_new[1:]))
            check(ln <= lm + 1.0,
                  "and the pulled path is no longer than the midpoint path",
                  f"{ln:.0f} u against {lm:.0f} u")
        # (d) every segment still walkable -- the property the whole pull is
        # allowed to risk, and the reason route() scores CANDIDATES rather than
        # replacing the midpoints outright.
        if path_new:
            bad = [(a, b) for a, b in zip(path_new, path_new[1:])
                   if m280.clip(*a, *b) != b]
            check(not bad,
                  "every segment of the pulled path is walkable end to end",
                  f"{len(path_new) - 1} segments, {len(bad)} bad")
        # (e) THE NO-LOSS GUARANTEE, over a corpus rather than the specimen:
        # the pull must never turn a path into None, and never lengthen one.
        rng = random.Random(7)
        centres = [t.centre for t in m280.trapezoids]
        lost = longer = pairs = 0
        for _ in range(120):
            a = rng.choice(centres)
            b = rng.choice(centres)
            pathmap.CORNER_PULL_ROUNDS = 0
            r0 = m280.route(a[0], a[1], b[0], b[1])
            pathmap.CORNER_PULL_ROUNDS = saved
            r1 = m280.route(a[0], a[1], b[0], b[1])
            if r0 is None:
                continue
            pairs += 1
            if r1 is None:
                lost += 1
                continue
            l0 = sum(math.hypot(q[0] - p[0], q[1] - p[1])
                     for p, q in zip(r0, r0[1:]))
            l1 = sum(math.hypot(q[0] - p[0], q[1] - p[1])
                     for p, q in zip(r1, r1[1:]))
            if l1 > l0 + 1.0:
                longer += 1
        pathmap.CORNER_PULL_ROUNDS = saved
        check(pairs >= 30,
              "the no-loss sweep actually routed something to compare",
              f"{pairs} routable pairs of 120 draws (a sweep that routed "
              f"nothing would pass (f) and (g) vacuously)")
        check(lost == 0,
              "the pull never turns a path into None",
              f"{lost} of {pairs} lost")
        check(longer == 0,
              "the pull never makes a path longer",
              f"{longer} of {pairs} longer")

    print("\n14. the seam-aware pull and gate (MOVECODE-1z-bb)")
    # THE DEFECT: route()'s string pull and final gate asked clip(), which asks
    # "inside any trapezoid, on ANY plane", so the pull could drop the
    # waypoints the A* only reached through a portal and grant a straight leg
    # across a plane change the file has no portal for. RUN-1zBA measured it
    # on a router grant, twice: the drawn body parked at a bridge deck's edge
    # for 7 s while the server's copy walked 2 km, then a 2,021 u teleport.
    #
    # The synthetic bridge below is the shape of that map's plane 18 reduced
    # to five trapezoids: a DECK (plane 1) over ground at its south end, a
    # zero-height portal LINE pair at its south edge -- the file's own shape,
    # the deck's body links to nothing -- ground continuing south of the
    # line, and an east bank the deck's side abuts with no portal. Every
    # check runs BOTH WAYS where it can: with SEAM_AWARE_ROUTE on, and off,
    # which restores the plane-blind pull exactly -- a fix whose control
    # cannot reproduce the bug is asserted, not tested.
    Tz = pathmap.Trapezoid
    NO = pathmap.NO_NEIGHBOUR
    #            plane idx  y_top  y_bot  xtl    xtr    xbl    xbr   neighbours (tl, tr, bl, br)
    T1 = Tz(0, 0,    0.0, -100.0, 100.0, 200.0, 100.0, 200.0, (NO, NO, 1, 1))   # ground under the deck
    T2 = Tz(0, 1, -100.0, -100.0, 100.0, 200.0, 100.0, 200.0, (0, 0, 2, 2))     # portal LINE, ground side
    T4 = Tz(0, 2, -100.0, -200.0, 100.0, 200.0, 100.0, 200.0, (1, 1, NO, NO))   # ground south of the line
    T3 = Tz(0, 3,  300.0,    0.0, 200.0, 300.0, 200.0, 300.0, (NO, NO, NO, NO)) # east bank, beside the deck
    D0 = Tz(1, 0,  300.0, -100.0, 100.0, 200.0, 100.0, 200.0, (NO, NO, 1, 1))   # the deck
    D1 = Tz(1, 1, -100.0, -100.0, 100.0, 200.0, 100.0, 200.0, (0, 0, NO, NO))   # portal LINE, deck side
    toy = pathmap.PathingMap([T1, T2, T4, T3, D0, D1], [{}, {}])
    LINK = {1: [5], 5: [1]}                     # T2 <-> D1, and nothing else
    toy._cross = dict(LINK)

    # (a) planes_at is the grid's answer; containing() is the band walk.
    # Two implementations of one point test, put against each other.
    dis = 0
    for gx in range(90, 311, 5):
        for gy in range(-210, 311, 5):
            if toy.planes_at(gx, gy) != {t.plane for t in toy.containing(gx, gy)}:
                dis += 1
    check(dis == 0, "planes_at agrees with containing() over the whole toy",
          f"{dis} disagreements on a 5 u lattice")

    # (b) the deck's SIDE: a body on the deck walking east onto the bank.
    side = toy.seam_clip(150.0, 150.0, 250.0, 150.0, 1)
    blind_side = toy.clip(150.0, 150.0, 250.0, 150.0, step=2.0)
    check(198.0 <= side[0] <= 200.0 and blind_side == (250.0, 150.0),
          "a body on the deck stops at its side; the plane-blind clip walks "
          "straight onto the bank",
          f"seam_clip {side}, clip {blind_side} -- RUN-1zBA's specimen in miniature")
    # (c) DIRECTIONAL: the ground under the deck ends at y = 0 for a body on
    # plane 0 (only the deck is beyond), but the deck continues for a body
    # on plane 1 over that same ground.
    under = toy.seam_clip(150.0, -50.0, 150.0, 150.0, 0)
    over = toy.seam_clip(150.0, -50.0, 150.0, 150.0, 1)
    check(-2.0 <= under[1] <= 0.0 and over == (150.0, 150.0),
          "a seam is directional: plane 0 ends under the deck's edge, plane 1 "
          "continues over the ground",
          f"on plane 0 -> {under}, on plane 1 -> {over}")
    # (d) THROUGH the line portal, and the primitive's known-bad arm.
    thru = toy.seam_clip(150.0, -50.0, 150.0, -150.0, 1)
    toy._cross = {}
    cut = toy.seam_clip(150.0, -50.0, 150.0, -150.0, 1)
    toy._cross = dict(LINK)
    check(thru == (150.0, -150.0) and -100.0 <= cut[1] <= -98.0,
          "the deck's south end is a portal (zero-height lines): linked, the "
          "walk continues; unlinked, it stops at the line",
          f"linked -> {thru}, link removed -> {cut}")
    check(toy.seam_clip(150.0, -50.0, 150.0, -150.0, 0) == (150.0, -150.0),
          "in-plane across the line trapezoid is not a seam at all")

    # (e) route(): ground under the deck -> up onto the deck. The straight line
    # is plane 0 ending at y = 0 with the deck above -- blind. The legal way is
    # the U-turn through the south-end portal.
    toy._component = None
    saved_flag = pathmap.SEAM_AWARE_ROUTE
    try:
        pathmap.SEAM_AWARE_ROUTE = True
        on = toy.route(150.0, -50.0, 150.0, 150.0, start_plane=0, goal_plane=1,
                       with_planes=True)
        pathmap.SEAM_AWARE_ROUTE = False
        off = toy.route(150.0, -50.0, 150.0, 150.0, start_plane=0, goal_plane=1,
                        with_planes=True)
        pathmap.SEAM_AWARE_ROUTE = True
        none_on = toy.route(150.0, -50.0, 250.0, 150.0)
        pathmap.SEAM_AWARE_ROUTE = False
        none_off = toy.route(150.0, -50.0, 250.0, 150.0)
    finally:
        pathmap.SEAM_AWARE_ROUTE = saved_flag
    check(on is not None and len(on[0]) == 3
          and abs(on[0][1][1] + 100.0) <= 1.0 and on[1][1] == 1 and on[1][-1] == 1,
          "seam-aware: the route U-turns through the portal (3 waypoints, the "
          "middle one on the line, then on the deck)",
          f"{on}")
    check(off is not None and len(off[0]) == 2,
          "KNOWN-BAD: with SEAM_AWARE_ROUTE off the same route is the straight "
          "line through the deck's underside -- the defect reproduces on demand",
          f"{off}")
    check(none_on is None and none_off is None,
          "a goal in another component is None in both arms (the seam term "
          "never invents a route)")
    # (f) the pull without planes is the pull as it was.
    corridor = [(150.0, -50.0), (150.0, -100.0), (150.0, -100.0), (150.0, 150.0)]
    check(toy._string_pull(corridor) == toy._string_pull(corridor, planes=[None] * 4)
          and toy._string_pull(corridor) == [(150.0, -50.0), (150.0, 150.0)],
          "planes=None (and all-None planes) is the plane-blind pull unchanged")

    # (g) the real map, where the specimen lives.
    if pre is None:
        LEDGER.skip("the seam term on Pre-Searing",
                    "the Pre-Searing mesh did not load from this archive")
    else:
        # RUN-1zBA run 4's grant: from the deck of the bridge into Ascalon
        # City toward the off-mesh click on the hills. The plane-blind clip
        # granted 2,158 u; the body parked at x = 10860.0 (the deck's west
        # edge) for 7.5 s and was teleported. The seam-aware ray must stop
        # at that edge.
        o = (10989.0, 5236.0)
        stop = pre.seam_clip(o[0], o[1], 8500.0, 4330.0, 18)
        blind = pre.clip(o[0], o[1], 8500.0, 4330.0, step=2.0)
        check(abs(stop[0] - 10860.0) <= 12.0
              and math.dist(blind, o) > 1500.0,
              "RUN-1zBA's specimen: seam_clip on plane 18 stops at the deck's "
              "west edge; the plane-blind clip runs past it by kilometres",
              f"seam_clip {tuple(round(v) for v in stop)}, clip "
              f"{tuple(round(v) for v in blind)} ({math.dist(blind, o):.0f} u)")

        def blind_by_containing(pm_, path, planes):
            """The reference walker over containing() (the band walk), not
            planes_at (the grid): a plane change with no portal on any leg."""
            for (a, b), pl in zip(zip(path, path[1:]), planes):
                dx, dy = b[0] - a[0], b[1] - a[1]
                dist = math.hypot(dx, dy)
                n = max(1, int(dist / 2.0))

                def at(f):
                    return {t.plane for t in pm_.containing(a[0] + dx * f, a[1] + dy * f)}

                carried, pf = None, 0.0
                for k in range(n + 1):
                    f = k / n
                    cp = at(f)
                    if not cp:
                        continue
                    if carried is None:
                        carried = {pl} if pl in cp else cp
                    elif carried & cp:
                        carried &= cp
                    else:
                        # bisect to the seam from both sides, as the walk under
                        # test does; a midpoint of two 2 u samples can sit a
                        # unit off a portal LINE and miss it by tolerance
                        lo, hi = pf, f
                        for _ in range(12):
                            mid = (lo + hi) * 0.5
                            if at(mid) & carried:
                                lo = mid
                            else:
                                hi = mid
                        f_old = lo
                        lo, hi = pf, f
                        for _ in range(12):
                            mid = (lo + hi) * 0.5
                            if at(mid) & cp:
                                hi = mid
                            else:
                                lo = mid
                        sf = (f_old + hi) * 0.5
                        if not pm_.portal_at(a[0] + dx * sf, a[1] + dy * sf,
                                             carried, cp):
                            return True
                        carried = cp
                    pf = f
            return False

        rng14 = random.Random(8)
        pairs14 = []
        while len(pairs14) < 300:
            ax, ay = rng14.choice(pre.trapezoids).centre
            if not pre.walkable(ax, ay):
                continue
            ang = rng14.uniform(0.0, 2.0 * math.pi)
            d = rng14.uniform(300.0, 1500.0)
            bx, by = ax + math.cos(ang) * d, ay + math.sin(ang) * d
            if pre.walkable(bx, by):
                pairs14.append((ax, ay, bx, by))
        got, load14 = {}, {}
        try:
            for flag in (False, True):
                pathmap.SEAM_AWARE_ROUTE = flag
                ms14, paths14, load14[flag] = sweep(pre, pairs14,
                                                    with_planes=True)
                got[flag] = (paths14, ms14)
        finally:
            pathmap.SEAM_AWARE_ROUTE = saved_flag
        off_p, on_p = got[False][0], got[True][0]
        changed = [i for i in range(len(pairs14))
                   if (off_p[i] is None) != (on_p[i] is None)
                   or (off_p[i] and on_p[i] and off_p[i][0] != on_p[i][0])]
        explained = sum(1 for i in changed
                        if off_p[i] and blind_by_containing(pre, *off_p[i]))
        on_blind = sum(1 for r in on_p if r and blind_by_containing(pre, *r))
        check(on_blind == 0,
              "no seam-aware route crosses a blind seam, by the containing() "
              "walker (a second point test, not the grid the pull used)",
              f"{on_blind} of {sum(1 for r in on_p if r)} routed")
        check(sum(1 for r in off_p if r is None) == sum(1 for r in on_p if r is None)
              and len(changed) - explained <= max(3, len(pairs14) // 50),
              "the seam term changes only what it should: None counts equal, "
              "and every changed path but a handful had a blind crossing before",
              f"{len(changed)} of {len(pairs14)} changed, {explained} explained "
              f"by a blind crossing in the old path; None "
              f"{sum(1 for r in off_p if r is None)} vs "
              f"{sum(1 for r in on_p if r is None)}")
        # A single-shot maximum over 300 routes was what this asserted until
        # 2026-09-08, and it is the most load-fragile shape in the file: no
        # re-timing at all, so one descheduled route decided the verdict. Same
        # treatment as section 10 -- candidates are re-timed best-of-5 and
        # divided by a load factor measured while they are re-timed. The
        # seam-aware arm is the one under test; the plane-blind arm is printed
        # beside it as the same-run comparison it always was.
        on_ms, off_ms = got[True][1], got[False][1]
        if load14[True] > LOAD_FACTOR_CAP:
            LEDGER.skip("the seam-aware route() under the 50 ms tick",
                        f"the box is running {load14[True]:.2f}x slower than "
                        f"the idle reference, past the {LOAD_FACTOR_CAP:.1f}x "
                        "this correction is trusted to")
        else:
            over14 = confirmed_over_tick(pre, pairs14, on_ms, load14[True],
                                         with_planes=True)
            check(not over14,
                  "the seam-aware route() stays under the 50 ms tick in the "
                  "chase band",
                  f"max {max(on_ms):.1f} ms raw = "
                  f"{max(on_ms) / load14[True]:.1f} at a measured "
                  f"{load14[True]:.2f}x, {len(over14)} confirmed "
                  f"over a tick (plane-blind max {max(off_ms):.1f}); p50 "
                  f"{sorted(on_ms)[150]:.2f} vs {sorted(off_ms)[150]:.2f} ms")

    print("\n15. on_mesh(): the mesh as the client resolves it at its edges (MOVECODE-1z-bf)")
    # THE DEFECT: the AgTrack guard's gate 2 asked walkable() -- exact
    # containment -- of the modelled sync copy, and every gate2-offmesh re-pin
    # in the corpus (17 fired, 19 predicted, 1,123 runs) was raised with that
    # copy standing on the client's own previous REPORT, a point exact
    # containment rejects by <= 0.5 u at the wedge tip of map 146. The client's
    # keyboard mover lays waypoints along trapezoid edges, its body reports from
    # them, and its own snap test passed the very grants we vetoed (RUN-1zBD,
    # two hooked runs). on_mesh() is containment OR within SEAM_TOL of a
    # trapezoid -- the same 1 u portal_at() uses -- and it must say YES on a
    # sub-unit sliver, NO further out, and NO where the mesh really ends.
    SQ = pathmap.Trapezoid(0, 0, 100.0, 0.0, 0.0, 100.0, 0.0, 100.0,
                           (pathmap.NO_NEIGHBOUR,) * 4)
    sq = pathmap.PathingMap([SQ], [{}])
    sq._cross = {}
    check(sq.walkable(50.0, 50.0) and sq.on_mesh(50.0, 50.0),
          "15a. inside a trapezoid: walkable() and on_mesh() agree", "")
    check(not sq.walkable(100.5, 50.0) and sq.on_mesh(100.5, 50.0),
          "15b. 0.5 u outside an edge: walkable() says off, on_mesh() says on",
          "the corpus's 17 false vetoes stood on exactly this")
    check(not sq.on_mesh(101.5, 50.0),
          "15c. 1.5 u outside: off under the default SEAM_TOL", "")
    check(sq.on_mesh(101.5, 50.0, tol=2.0) and not sq.on_mesh(103.0, 50.0, tol=2.0),
          "15d. the tolerance is the caller's, and it is a radius", "")
    check(not sq.on_mesh(150.0, 150.0),
          "15e. far off the mesh stays off", "")
    check(pathmap.SEAM_TOL == 1.0,
          "15f. SEAM_TOL is the 1 u the portal test already uses -- on_mesh adds no new constant",
          f"SEAM_TOL {pathmap.SEAM_TOL}")
    # plane_near (MOVECODE-1z-bg): the plane of a sliver point, named the way
    # plane_at names an inside one -- prefer if offered, a sole candidate, else
    # None -- and plane_at itself wherever containment has an answer.
    check(sq.plane_near(50.0, 50.0) == 0 and sq.plane_near(100.5, 50.0) == 0
          and sq.plane_near(101.5, 50.0) is None,
          "15i. plane_near: inside is plane_at; a 0.5 u sliver names the sole plane; "
          "1.5 u out names nothing", "")
    SQ1 = pathmap.Trapezoid(1, 0, 100.0, 0.0, 0.0, 100.0, 0.0, 100.0,
                            (pathmap.NO_NEIGHBOUR,) * 4)
    sq2 = pathmap.PathingMap([SQ, SQ1], [{}, {}])
    sq2._cross = {}
    check(sq2.plane_near(100.5, 50.0) is None
          and sq2.plane_near(100.5, 50.0, prefer=1) == 1
          and sq2.plane_near(100.5, 50.0, prefer=0) == 0
          and sq2.plane_near(50.0, 50.0) is None
          and sq2.plane_near(50.0, 50.0, prefer=1) == 1,
          "15j. two planes on one sliver: the report's word decides, and with no word "
          "it says nothing -- inside, the stacked case is plane_at's own", "")
    if pre is None:
        LEDGER.skip("15g/15h/15k. RUN-1zBD's report points on Pre-Searing",
                    "no archive")
    else:
        spec = [(10302.02, 8214.08), (10374.04, 8286.84), (10369.42, 8282.33)]
        got = [(pre.walkable(x, y), pre.on_mesh(x, y)) for x, y in spec]
        check(all(w is False and m is True for w, m in got),
              "15g. RUN-1zBD's three report points at the wedge tip: outside "
              "every trapezoid by exact containment, ON the mesh within 1 u",
              f"(walkable, on_mesh) = {got}")
        check(not pre.on_mesh(10441.47, 8209.68) and not pre.walkable(10441.47, 8209.68),
              "15h. and the server's legacy belief 144 u east of the report, "
              "genuinely off the mesh, stays off under the tolerance", "")
        named = [pre.plane_near(x, y, prefer=pl) for (x, y), pl in
                 zip(spec, (0, 29, 29))]
        check(named == [0, 29, 29] and pre.plane_near(10374.04, 8286.84) == 29
              and pre.plane_near(10358.17, 8286.86) == pre.plane_at(10358.17, 8286.86) == 29,
              "15k. plane_near names the three report points' planes as the client "
              "reported them (0, 29, 29), the wedge-tip sliver is unambiguous even "
              "without the word, and an inside point is plane_at",
              f"named {named}")

    print("\n16. wall_slide(): retail's next-vertex slide along a wall (MOVECODE-1z-ce)")
    # THE RULE, and where it comes from. A keyboard report whose heading ray is
    # blocked at the body is a body pressed against a wall and sliding along
    # it. ArenaNet's server grants the NEXT VERTEX of that wall in the
    # heading's slide direction -- measured on the live corpus against our own
    # decode of the same files: 62 blocked-ray report pairs, the rule within
    # 3 u of retail's grant on 49, the zero-length lead we used to send on 19
    # (studies/movecode/review/wallslide.py --check). RUN-R3's stair climb is
    # the specimen on OUR map: 15 reports along the stairs' right side, the
    # client's heading due east on every one, 15 zero leads, and the sync copy
    # 100-139 u behind the body for the climb.
    SQ16 = pathmap.Trapezoid(0, 0, 100.0, 0.0, 0.0, 100.0, 0.0, 100.0,
                             (pathmap.NO_NEIGHBOUR,) * 4)
    sq16 = pathmap.PathingMap([SQ16], [{}])
    sq16._cross = {}
    check(sq16._walls == {},
          "16a. the wall index is lazy: nothing built until the first slide, so the "
          "corpus sweep pays nothing", "")
    got, why = sq16.wall_slide(100.0, 50.0, 1.0, 1.0, 0)
    check(got == (100.0, 100.0) and why == "vertex",
          "16b. a body on the right side of a lone square, heading north-east, slides "
          "to the side's next vertex (100, 100)", f"{got} {why}")
    got, why = sq16.wall_slide(100.0, 50.0, 1.0, -1.0, 0)
    check(got == (100.0, 0.0) and why == "vertex",
          "16c. heading south-east it slides the other way, to (100, 0)", f"{got} {why}")
    got, why = sq16.wall_slide(100.0, 50.0, 1.0, 0.0, 0)
    check(got is None,
          "16d. a HEAD-ON press (due east into the side) slides nowhere: the wall "
          "press of RUN-1zBR keeps its zero lead", f"{got} {why}")
    got, why = sq16.wall_slide(100.0, 50.0, -1.0, 1.0, 0)
    check(got is None and why == "no-pressed-wall",
          "16e. a heading AWAY from the wall presses into nothing and answers None "
          "-- the caller keeps its clip", f"{got} {why}")
    got, why = sq16.wall_slide(50.0, 50.0, 1.0, 1.0, 0)
    check(got is None and why == "no-wall",
          "16f. a body with no wall within WALL_SLIDE_TOL answers None", f"{got} {why}")
    got, why = sq16.wall_slide(50.0, 100.0, 1.0, 1.0, 0)
    check(got == (100.0, 100.0) and why == "vertex",
          "16g. a HORIZONTAL wall -- the square's unshared top edge -- slides too: from "
          "(50, 100) heading north-east to (100, 100)", f"{got} {why}")
    got, why = sq16.wall_slide(100.0, 100.0, 1.0, 1.0, 0)
    check(got is None,
          "16h. standing ON the corner with the heading pressing into both walls, "
          "neither continuing wall is slid forward: None", f"{got} {why}")
    got, why = sq16.wall_slide(100.0, 100.0, -1.0, 1.0, 0)
    check(got == (0.0, 100.0) and why in ("vertex", "vertex-after-corner"),
          "16i. standing ON the corner heading north-west, the slide runs along "
          "the top edge to its far vertex (0, 100) -- whichever of the two walls "
          "meeting there is found first", f"{got} {why}")
    got, why = sq16.wall_slide(100.0, 50.0, 1.0, 1.0, 0, chord=20.0)
    check(got == (100.0, 70.0) and why == "chord",
          "16j. the chord caps the slide along the wall: 20 u of a 50 u wall", f"{got} {why}")
    check(pathmap.WALL_SLIDE_TOL == 3.0,
          "16k. WALL_SLIDE_TOL is 3 u: RUN-R3's reports sit -0.004..+0.398 u off the "
          "stairs' side and no wall in the live corpus is thinner", "")
    if pre is None:
        LEDGER.skip("16l-16p. the stairs of Pre-Searing", "no archive")
    else:
        # RUN-R3's report at 12.394 s: (10444.908, 8356.0) plane 29, the client's
        # vec2 (766.8, 0) due east, 0.003 u outside the stairs' right side. The
        # side is p29#0's, from its bottom apex (10366, 8279) to (10671.37, 8577).
        t0_ = [t for t in pre.trapezoids if t.plane == 29 and t.index == 0][0]
        got, why = pre.wall_slide(10444.908203125, 8356.0, 766.8, 0.0, 29)
        check(got == (t0_.x_top_right, t0_.y_top) and why == "vertex"
              and abs(got[0] - 10671.374) < 0.01 and got[1] == 8577.0,
              "16l. THE STAIRS: the report's due-east heading is a press into the "
              "stairs' right side, and the slide is that side's next vertex "
              "(10671.37, 8577) -- 316 u up the stairs, where the shipped lead was 0",
              f"{got} {why}")
        d16 = math.hypot(got[0] - 10444.908203125, got[1] - 8356.0)
        ang = math.degrees(math.atan2(got[1] - 8356.0, got[0] - 10444.908203125))
        check(abs(d16 - 316.4) < 0.5 and abs(ang - 44.3) < 0.2,
              "16m. 316 u at 44.3 deg -- the direction the body actually moved on the "
              "tape (reports 44.3 deg apart), not the 0 deg it reported",
              f"{d16:.1f} u at {ang:.1f} deg")
        got, why = pre.wall_slide(10444.908203125, 8356.0, -766.8, 0.0, 29)
        check(got is None,
              "16n. the same body heading WEST presses into no wall (the stairs are "
              "open to the west): None, the clip's answer stands", f"{got} {why}")
        got, why = pre.wall_slide(10668.328125, 8574.0283203125, 766.8, 0.0, 29)
        check(got == (t0_.x_top_right, t0_.y_top),
              "16o. 4 u short of that vertex the answer is still the vertex, not the "
              "wall beyond it -- the rule stops at the FIRST vertex, the "
              "decomposition's split points included, because retail does", f"{got} {why}")
        got, why = pre.wall_slide(10742.6318359375, 8646.5361328125, 766.8, 0.0, 29)
        check(got is not None and abs(got[0] - 11070.0) < 0.01 and abs(got[1] - 8966.0) < 0.01,
              "16p. past it, on p29#2's side, the next vertex is (11070, 8966): the "
              "climb is granted in vertex-long legs, 457 u here",
              f"{got} {why}")

    dt = time.perf_counter() - t0
    print(f"\nwalked the archive in {dt:.1f}s")

    # ---- 17. THE GATE'S OWN SAMPLING (MOVECODE-1z-co) ---------------------
    #
    # route() promises "walking it in straight segments never leaves the
    # navmesh". Its per-segment gate re-clips the PULLED candidate at 2 u and
    # every other candidate at 16 u, and clip() says of itself that "a gap
    # narrower than `step` can be stepped over" -- so a 2-POINT path, which the
    # NPC follow reads as "the line is clear" before sending an agent-addressed
    # 0x002A the client dead-reckons STRAIGHT, could carry a chord that leaves
    # the mesh. MEASURED on RUN-1zCG (1z-cn): three of the corpus's six bad
    # chords are this, and session 2's specimen passes the gate at 16 u, fails
    # at 2 u, and truly leaves the mesh by 2.6 u.
    #
    # WHAT SHIPPED IS THE RE-CHECK, NOT A FINER GATE EVERYWHERE. Gating every
    # candidate at 2 u was the first cut and section 14 above refused it: the
    # chase band's worst route went 24.2 -> 42.4 ms against a 50 ms tick, and
    # the pull's own candidates started failing into the RAW midpoint corridor
    # (141 waypoints where 8 would do -- sec.1z-ch's defect, back again). Only a
    # RETURNED 2-point path carries the straight-line claim, so only its single
    # segment is re-checked. These checks read the same either way: the arm is
    # what route() returns, not how it got there.
    #
    # SYNTHETIC, because the property is about the SAMPLING and a real mesh
    # cannot place the gap where it needs to be: a 6 u notch in y that no 16 u
    # sample lands in, with a narrow neck to the west so a way round exists.
    print("\n17. the route gate's sampling: a notch no 16 u sample lands in")
    Tz2 = pathmap.Trapezoid
    NO2 = pathmap.NO_NEIGHBOUR
    #          plane idx  y_top  y_bot   xtl    xtr    xbl    xbr   neighbours
    N0 = Tz2(0, 0,  46.0,   0.0,   0.0, 300.0,   0.0, 300.0, (1, 1, NO2, NO2))
    N1 = Tz2(0, 1,  52.0,  46.0,   0.0,  20.0,   0.0,  20.0, (2, 2, 0, 0))
    N2 = Tz2(0, 2, 100.0,  52.0,   0.0, 300.0,   0.0, 300.0, (NO2, NO2, 1, 1))
    notch = pathmap.PathingMap([N0, N1, N2], [{}])
    A, B = (150.0, 10.0), (150.0, 90.0)
    check(notch.walkable(*A) and notch.walkable(*B)
          and not notch.walkable(150.0, 49.0),
          "17. the fixture: both ends on the mesh, the notch between them off it",
          f"A={notch.walkable(*A)} B={notch.walkable(*B)} "
          f"notch={notch.walkable(150.0, 49.0)}")
    # The sampling itself, stated as arithmetic so the fixture cannot rot into
    # one where both steps agree and the checks below pass vacuously.
    dist = 80.0
    coarse_ys = [10.0 + dist * i / int(dist / 16.0) for i in range(int(dist / 16.0) + 1)]
    check(not any(46.0 < y < 52.0 for y in coarse_ys),
          "17. CONTROL: no 16 u sample lands inside the notch",
          f"samples {['%.0f' % y for y in coarse_ys]} against the notch 46-52")
    check(any(46.0 < 10.0 + dist * i / int(dist / 2.0) < 52.0
              for i in range(int(dist / 2.0) + 1)),
          "17. and a 2 u sample does",
          "if this fails the notch is narrower than the fine step too")
    saved_fine = pathmap.ROUTE_GATE_FINE
    try:
        # THE KNOWN-BAD ARM: the shipped-before answer, which is the defect.
        pathmap.ROUTE_GATE_FINE = False
        coarse = notch.route(A[0], A[1], B[0], B[1])
        check(coarse is not None and len(coarse) == 2,
              "17. REVERT ARM (--route-gate-coarse): route returns a 2-POINT "
              "path -- 'the line is clear'",
              f"got {None if coarse is None else len(coarse)} points: {coarse}")
        worst = 0.0
        for i in range(0, 81):
            y = 10.0 + 80.0 * i / 80.0
            if not notch.walkable(150.0, y):
                worst = max(worst, 1.0)
        check(worst > 0.0,
              "17. and that straight segment DOES leave the mesh -- the "
              "contract broken",
              "the fixture must actually carry a hole, or this proves nothing")
        # THE FIX.
        pathmap.ROUTE_GATE_FINE = True
        fine = notch.route(A[0], A[1], B[0], B[1])
        check(fine is None or len(fine) >= 3,
              "17. SHIPPED: the fine gate refuses the straight line -- a "
              "corridor, or nothing, never a false 'clear'",
              f"got {None if fine is None else len(fine)} points: {fine}")
        if fine:
            bad = 0
            for p, q in zip(fine, fine[1:]):
                n = max(1, int(((q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2) ** 0.5 / 2.0))
                for i in range(n + 1):
                    f = i / n
                    if not notch.walkable(p[0] + (q[0] - p[0]) * f,
                                          p[1] + (q[1] - p[1]) * f):
                        bad += 1
            check(bad == 0,
                  "17. and every segment of what it DOES return holds at 2 u",
                  f"{bad} off-mesh samples on the returned path {fine}")
        check(pathmap.CORNER_PULL_GATE_STEP == 2.0
              and pathmap.RAW_GATE_STEP_COARSE == 16.0,
              "17. the two steps are the named constants, not literals",
              f"pull {pathmap.CORNER_PULL_GATE_STEP}, coarse "
              f"{pathmap.RAW_GATE_STEP_COARSE}")
    finally:
        pathmap.ROUTE_GATE_FINE = saved_fine

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
