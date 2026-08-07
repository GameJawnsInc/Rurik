"""Score our movement simulation against the only oracle we have: the client.

There is no reference server. ArenaNet's is gone, we are forbidden from touching
what remains, and every public reimplementation is a reconstruction of unknown
quality -- studies/movement/FINDINGS.md spends a section on exactly how much of
OpenTyria is guesswork. So "is our movement faithful?" cannot be answered by
comparison against a correct implementation, because we do not have one.

What we do have is the retail client. It is the genuine article, it implements
these rules, and it tells us continuously where it thinks it is. Anywhere our
simulation and the client's disagree, at least one of us is wrong -- and it is
almost certainly us. That makes disagreement a measurable fidelity score rather
than a matter of opinion.

Three measurements, in decreasing order of how much they tell us:

  1. RUN SPEED. During a straight unbroken run, the client's own successive
     position reports are a speed measurement. DEFAULT_RUN_SPEED = 288.0 had two
     independent lineages agreeing on it and not one measurement behind it; this
     is the measurement. Turn-only reports must be excluded or the figure comes
     out ~40% low, which is what first made us suspect a mismatch that was not
     there.

  2. DRIFT AT STOP. How far apart the two simulations had wandered by the time
     the player stopped. A perfect model drifts zero. This is the headline score.

  3. CORRECTION RATE. How often we had to overrule the client with a teleport.
     Every one of those is a visible glitch.

  4. COLLISION FIRING, and 5. MESH COVERAGE. Added 2026-08-06, and they are here
     because they are R3's acceptance criterion -- "you walk to a wall and are
     stopped" -- which was landed at `a97c7c4` and then assumed by every run
     afterwards rather than asserted by any of them. `clipped` is the server
     refusing a destination the navmesh does not contain; `on_mesh` is whether the
     client's own stop lands in our trapezoids. Mesh coverage is deliberately not
     required to be 100%: the client stops against collision geometry we have never
     read, so the misses are gaps in OUR data and are the ones worth studying.

Scored over every game-channel capture in the vault:

    python toolkit/authsrv/test_movement_fidelity.py
    python toolkit/authsrv/test_movement_fidelity.py --latest   # newest session only

WHY THE CORPUS AND NOT THE LAST SESSION, changed 2026-08-06. The default used to be
the newest capture alone, and on 2026-08-06 that capture contained zero straight runs
and two stops. The test skipped its speed section, scored its headline number over
n=2, printed a "not measured this run" list, and then printed ALL CHECKS PASSED and
exited 0. A fidelity score is a property of the corpus, not of whichever session
happened to be last, and a single session is free to contain no movement at all.
Pooled, the same vault gives n=678 speed samples and n=527 stops.

Both halves of that failure are now closed: the run is scored against a declared floor
of CHECK_FLOOR checks via `toolkit/checks.py`, so skipping a section reddens the run
instead of being a footnote under a green banner; and captures are selected by the
channel each file declares rather than by a filename convention that had already
drifted twice -- see `game_channel_captures`.
"""

import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import vaultpath  # noqa: E402
import checks  # noqa: E402
import origin  # noqa: E402

TURN_TO_DIRECTION = 0x003D
DEFAULT_RUN_SPEED = 288.0
MAXIMUM_ALLOWED_CORRECTION = 100.0

# A segment counts as "straight running" only if the player did not turn, was
# moving forward, and the two reports are close enough in time to interpolate
# between honestly. These bounds are ours, chosen to exclude noise rather than
# to flatter the result -- widening them makes the answer worse, not better.
STRAIGHT_MAX_TURN_DEG = 3.0
SEGMENT_MIN_SECONDS = 0.15
SEGMENT_MAX_SECONDS = 0.75
SEGMENT_MIN_UNITS = 5.0
MOVEMENT_TYPE_FORWARD = 1

# Thresholds. Set from what we have actually observed working, and deliberately
# loose: this is a regression guard, not a target to tune against.
SPEED_TOLERANCE = 0.10          # p75 within 10% of DEFAULT_RUN_SPEED
DRIFT_P50_LIMIT = 60.0          # median disagreement at a stop, in units
ACCEPT_RATE_FLOOR = 0.75        # fraction of stops needing no teleport
ON_MESH_FLOOR = 0.80            # fraction of stops landing in our own trapezoids

# Five checks: one speed, two drift, and two that gate R3 -- collision firing at all,
# and the client's stops landing on our own mesh. Both sections must run for this test
# to mean what its name says; it used to skip either one and still print ALL CHECKS
# PASSED. Measured from a real green run over the whole corpus on 2026-08-06.
CHECK_FLOOR = 5

LEDGER = checks.Ledger("movement fidelity", floor=CHECK_FLOOR)
check = checks.adopt(LEDGER)


def game_channel_captures():
    """Every capture of the GAME channel, selected by what the file says it is.

    Not by filename. The convention drifted twice and the glob never followed:
    before the host split the game channel was the second connection on the
    authsrv host (`-c2`), after `3e86af3` it is the first on its own host
    (`captures/gamesrv/`, `-c1`), and the oldest captures carry no suffix at all.

    Measured against the vault on 2026-08-06, the old `authsrv-*-c2.jsonl` glob
    was wrong in both directions at once: it MISSED 36 game-channel captures (24
    with no suffix, 12 under gamesrv/) and WRONGLY INCLUDED 8 auth-channel files
    that happen to be named `-c2`. Every capture opens with a version record
    carrying `"channel"`, so read that instead and the question stops depending
    on where we happened to put the socket that month.
    """
    root = vaultpath.require_dir(
        "captures",
        why="the client's position reports -- this test has no other oracle")
    out = []
    for sub in ("authsrv", "gamesrv"):
        d = os.path.join(root, sub)
        if not os.path.isdir(d):
            continue
        for p in glob.glob(os.path.join(d, "*.jsonl")):
            if channel_of(p) == "game":
                out.append(p)
    # And they must all be OUR server's. This test scores our simulation against the
    # client's, pooled over the whole corpus -- a capture of ArenaNet's server in that
    # pool would silently blend two different oracles into one number that is about
    # neither. There are no live captures today (MEASURED: 113 of 113 game-channel
    # files classify as ours), so this refuses nothing yet and refuses the first one
    # that appears, which is the only moment it could matter.
    out = origin.require_single(out, origin.OURS, what="the movement fidelity score")
    return sorted(out, key=os.path.getmtime, reverse=True)


def channel_of(path):
    """The channel a capture records, read from its version line. None if absent."""
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"channel"' not in line:
                continue
            try:
                return json.loads(line).get("channel")
            except json.JSONDecodeError:
                return None
    return None


def load(path):
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def percentile(xs, p):
    if not xs:
        return None
    s = sorted(xs)
    return s[min(len(s) - 1, int(p * len(s)))]


def straight_run_speeds(turns):
    """Speeds from segments where the player ran straight without turning."""
    out = []
    for a, b in zip(turns, turns[1:]):
        ha, hb = a["values"][3], b["values"][3]
        mags = math.hypot(*ha) * math.hypot(*hb)
        if mags <= 0:
            continue
        dot = (ha[0] * hb[0] + ha[1] * hb[1]) / mags
        turn = math.degrees(math.acos(max(-1.0, min(1.0, dot))))
        dt = b.get("t", 0) - a.get("t", 0)
        pa, pb = a["values"][1], b["values"][1]
        dist = math.hypot(pb[0] - pa[0], pb[1] - pa[1])
        if (turn < STRAIGHT_MAX_TURN_DEG
                and a["values"][4] == MOVEMENT_TYPE_FORWARD
                and b["values"][4] == MOVEMENT_TYPE_FORWARD
                and SEGMENT_MIN_SECONDS < dt < SEGMENT_MAX_SECONDS
                and dist > SEGMENT_MIN_UNITS):
            out.append(dist / dt)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--latest", action="store_true",
                    help="only the newest session, rather than the whole corpus")
    ap.add_argument("--all", action="store_true",
                    help=argparse.SUPPRESS)  # accepted; pooling is now the default
    args = ap.parse_args()

    paths = game_channel_captures()
    if not paths:
        print("no game-channel captures in the vault")
        return 1

    used, turns, reports = [], [], []
    for p in paths:
        evs = load(p)
        t = [e for e in evs if e.get("kind") == "decoded"
             and e.get("opcode") == TURN_TO_DIRECTION]
        if not t:
            continue
        used.append(os.path.basename(p))
        turns.extend(t)
        reports.extend(e for e in evs if e.get("kind") == "position_report")
        if args.latest:
            break

    if not turns:
        print("no capture contains movement. Walk around, then re-run.")
        return 1

    print(f"sessions: {len(used)}")
    for u in used:
        print(f"  {u}")
    print()

    print("1. run speed, measured from the client's own position reports")
    speeds = straight_run_speeds(turns)
    if len(speeds) < 10:
        LEDGER.skip("run speed",
                    f"only {len(speeds)} straight-run samples; need 10")
    else:
        p50, p75 = percentile(speeds, 0.50), percentile(speeds, 0.75)
        print(f"  n={len(speeds)}  p50={p50:.1f}  p75={p75:.1f} units/sec"
              f"   ours={DEFAULT_RUN_SPEED}")
        err = abs(p75 - DEFAULT_RUN_SPEED) / DEFAULT_RUN_SPEED
        check(err <= SPEED_TOLERANCE,
              f"client's straight-run speed is within "
              f"{SPEED_TOLERANCE:.0%} of ours (off by {err:.1%})")
        print("     p75 rather than p50: segments that begin from a standing")
        print("     start are still accelerating and drag the median down.")

    print("\n2. drift between our simulation and the client's, at each stop")
    if not reports:
        LEDGER.skip("drift at stops",
                    "no position_report events -- capture predates the"
                    " instrumentation")
    else:
        drifts = [r["drift"] for r in reports]
        p50 = percentile(drifts, 0.50)
        p90 = percentile(drifts, 0.90)
        accepted = sum(1 for r in reports if r.get("accepted"))
        rate = accepted / len(reports)
        print(f"  n={len(reports)}  p50={p50:.1f}  p90={p90:.1f}  "
              f"max={max(drifts):.1f} units")
        check(p50 <= DRIFT_P50_LIMIT,
              f"median disagreement at a stop is under {DRIFT_P50_LIMIT:.0f} "
              f"units (got {p50:.1f})")
        check(rate >= ACCEPT_RATE_FLOOR,
              f"at least {ACCEPT_RATE_FLOOR:.0%} of stops need no teleport "
              f"(got {rate:.0%}, {accepted}/{len(reports)})")
        # R3's own acceptance criterion -- "you walk to a wall and are stopped" --
        # had no gate anywhere until 2026-08-06. It was landed at a97c7c4 and
        # thereafter assumed. These two checks are that gate, and they are scored
        # from the same corpus rather than needing a walk to be driven live.
        #
        # `clipped` is the server refusing a destination the navmesh does not
        # contain; `on_mesh` is whether the client's own reported stop lands in our
        # trapezoids. Both must be read only over reports that actually recorded the
        # field -- older captures predate it and carry None, and counting those as
        # False would quietly turn a missing measurement into a passing one.
        clip = [r["clipped"] for r in reports if r.get("clipped") is not None]
        mesh = [r["on_mesh"] for r in reports if r.get("on_mesh") is not None]
        if clip:
            fired = sum(1 for c in clip if c)
            check(fired > 0,
                  f"collision fired: the navmesh refused at least one destination "
                  f"({fired} of {len(clip)} stops clipped)")
        else:
            LEDGER.skip("collision", "no capture recorded the `clipped` field")
        if mesh:
            on = sum(1 for m in mesh if m)
            check(on / len(mesh) >= ON_MESH_FLOOR,
                  f"at least {ON_MESH_FLOOR:.0%} of stops land on our own mesh "
                  f"(got {on / len(mesh):.0%}, {on}/{len(mesh)})")
            print("     Not 100%, and it should not be: the client stops against")
            print("     collision geometry we have never read, so the misses are")
            print("     gaps in OUR trapezoids and are the ones worth studying.")
        else:
            LEDGER.skip("mesh coverage", "no capture recorded the `on_mesh` field")

        over = sum(1 for d in drifts if d > MAXIMUM_ALLOWED_CORRECTION)
        if over:
            print(f"     {over} stop(s) exceeded the {MAXIMUM_ALLOWED_CORRECTION:.0f}"
                  f"-unit tolerance and were corrected. Walking into geometry")
            print("     does this: the client stops at a wall, we keep going.")

    print("\n3. what this does and does not tell us")
    print("  The client is the oracle here, not a reference server -- there is")
    print("  no reference server. These numbers say our simulation agrees with")
    print("  the retail client's. They say nothing about whether either matches")
    print("  what ArenaNet's server did, and nothing at all about collision,")
    print("  which neither we nor OpenTyria implement.")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
