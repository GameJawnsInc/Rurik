#!/usr/bin/env python3
"""Did this run actually TEST the teleport, and did it warp?

    python toolkit/authsrv/warpscan.py               # the newest gamesrv capture
    python toolkit/authsrv/warpscan.py --all         # every capture in the vault
    python toolkit/authsrv/warpscan.py --capture X   # one named file

WHY THIS EXISTS. On 2026-08-19 a run came back "I did approximately the same
thing as last time and didn't get warped" -- and the capture held ZERO granted
clicks, so there had been nothing armed to warp onto. The null was uninformative
and nothing on screen or in the log said so. An experiment whose failure mode is
"looks like a pass" needs an instrument that counts its own trials.

THE PRECONDITION, MEASURED over 918 captures, 113 grants and 4 teleports -- and
the first version of this docstring got it WRONG, which is why the wrong version
is described rather than deleted. It claimed a teleport needed a grant that was
FAR (>2000u), CROSS-PLANE, and left un-overwritten, on the strength of the two
cases I had studied hardest. Both extra terms are refuted by the other two:
20260814T100340 warped onto a grant of 206u with planes 0->0, and
20260819T113105 warped onto a grant that WAS overwritten 1.0s later (the snap
came at 0.9s, just ahead of it). Defining a class from its two best-known
members is how a hypothesis gets fitted to itself.

What survives is one term, and it is the one the disassembly already predicted:
the client clears a granted destination only by consuming it at its arrival tick
or by having a newer grant overwrite it. So a grant LEFT ALONE is a trial, and
the rate rises with how long it is left:

    grant un-overwritten for   trials   teleports   rate
                          0s      113           4    3.5%
                          2s       24           3   12.5%
                          5s       12           3   25.0%
                         10s        8           3   37.5%

A trial below is a grant with no later grant for TRIAL_QUIET seconds. At 37.5%,
six clean trials give a ~94% chance of at least one teleport if nothing is
fixed -- that is the size the next run needs, and it is about three minutes of
play.

The one hard part is getting a click GRANTED at all. authsrv refuses to answer a
click when our last position report is over 1.0s old, and the corpus maximum
staleness at a granted click is 0.95s -- so a click made while STANDING STILL is
never granted, because the client sends no position while stationary.

So a run with zero ARMED TRIALS says nothing about --stop-echo either way, and
this tool's headline is the trial count, not the warp count.
"""
import argparse
import glob
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import vaultpath  # noqa: E402

TRIAL_QUIET = 10.0    # seconds a grant must survive un-overwritten to count as
                      # a trial; 3 of 8 such grants teleported (37.5%)
IMPOSSIBLE = 320.0    # u/s; the fastest legitimate cruise step measured is 291.20
# How close a landing must be to a granted point to be ATTRIBUTED to it. NOT a
# detection gate -- the detector is the impossible step alone. This started at
# 1.0 u ("bit-exact") and missed a real teleport on run 20260819T135526: the
# client snapped to the granted point and then walked 42 u before it reported,
# which is 0.23 s at the 186 u/s it was already moving. The two bit-exact cases
# were the ones whose report happened to land on the instant of the snap.
NEAR_GRANT = 150.0
GRANT_RE = re.compile(r"\(([-\d]+),([-\d]+) on plane (\d+)->(\d+)")


def load(path):
    """(grants, reports, echoes) from one gamesrv capture."""
    grants, reports, echoes = [], [], []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            try:
                o = json.loads(line)
            except ValueError:
                continue
            k, t = o.get("kind"), o.get("t", 0.0)
            if k == "decoded" and o.get("opcode") in (61, 71):
                reports.append((t, tuple(o["values"][1]), o["values"][2]))
            elif k == "sent":
                lab = str(o.get("label") or "")
                if lab.startswith("AGENT_MOVE_TO_POINT"):
                    m = GRANT_RE.search(lab)
                    if m:
                        grants.append((t, (float(m.group(1)), float(m.group(2))),
                                       int(m.group(3)), int(m.group(4))))
                elif lab.startswith("STOP ECHO"):
                    echoes.append(t)
    return grants, reports, echoes


def scan(path):
    grants, reports, echoes = load(path)
    trials, warps = [], []
    for i, (gt, dest, p_from, p_to) in enumerate(grants):
        before = [q for t, q, _pl in reports if t <= gt]
        if not before:
            continue
        dist = math.hypot(dest[0] - before[-1][0], dest[1] - before[-1][1])
        nxt = grants[i + 1][0] - gt if i + 1 < len(grants) else float("inf")
        if nxt >= TRIAL_QUIET:
            trials.append((gt, dest, p_from, p_to, dist))
    # THE DETECTOR IS THE IMPOSSIBLE STEP, on its own. Requiring the landing to
    # sit on a granted point was a second gate, and it silently suppressed a real
    # teleport -- see NEAR_GRANT. Attribution to a grant is now reported, never
    # required, so a teleport with no grant behind it shows up as a finding
    # rather than as silence.
    for j in range(1, len(reports)):
        (t0, q0, _a), (t1, q1, _b) = reports[j - 1], reports[j]
        dt = t1 - t0
        d = math.hypot(q1[0] - q0[0], q1[1] - q0[1])
        if dt <= 0 or d <= 500 or d / dt <= IMPOSSIBLE:
            continue
        best = None
        for gt, dest, _pf, _pt in grants:
            if gt >= t1:
                continue
            sep = math.hypot(dest[0] - q1[0], dest[1] - q1[1])
            if best is None or sep < best[0]:
                best = (sep, gt)
        if best is not None and best[0] <= NEAR_GRANT:
            warps.append((t1, d / dt, d, t1 - best[1], best[0]))
        else:
            warps.append((t1, d / dt, d, None, None if best is None else best[0]))
    return grants, reports, echoes, trials, warps


def report(path):
    grants, reports, echoes, trials, warps = scan(path)
    print(f"\n{os.path.basename(path)}")
    print(f"  position reports {len(reports):4}   grants {len(grants):4}   "
          f"stop-echoes {len(echoes):4}")
    for gt, dest, pf, pt, dist in trials:
        print(f"  TRIAL at t={gt:.2f}: grant {dist:.0f}u to "
              f"({dest[0]:.0f},{dest[1]:.0f}) plane {pf}->{pt}, left alone")
    for t, v, d, lag, sep in warps:
        where = (f"{sep:.0f}u from a grant {lag:.1f}s old" if lag is not None
                 else f"NOT near any grant (nearest {sep:.0f}u)"
                 if sep is not None else "no grant in this run")
        print(f"  *** TELEPORT at t={t:.2f}: {d:.0f}u at {v:.0f} u/s -- {where}")
    if not trials:
        print("  VERDICT: 0 trials -- this run did NOT test the fix.")
        if grants:
            print(f"           ({len(grants)} grant(s), but every one was "
                  f"overwritten by a later click within "
                  f"{TRIAL_QUIET:.0f}s -- stop clicking after the grant)")
        else:
            print("           (no click was granted at all: click while still "
                  "MOVING, within 1.0s of a position report)")
    elif warps:
        print(f"  VERDICT: {len(trials)} trial(s), {len(warps)} TELEPORT(S) -- "
              f"the fix is REFUTED if --stop-echo was on.")
    else:
        n = len(trials)
        print(f"  VERDICT: {n} trial(s), no teleport. "
              f"{'Stop-echo fired, so this counts.' if echoes else 'NOTE: no stop-echo in this run.'}")
        print(f"           Under the null 37.5%/trial, {n} clean trial(s) leave "
              f"a {0.625 ** n:.0%} chance of seeing nothing anyway.")
    return len(trials), len(warps)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--capture", help="one capture file")
    ap.add_argument("--all", action="store_true", help="every gamesrv capture")
    a = ap.parse_args()
    d = vaultpath.require_dir(vaultpath.vault_path("captures", "gamesrv"))
    if a.capture:
        paths = [a.capture]
    else:
        paths = sorted(glob.glob(os.path.join(d, "*.jsonl")),
                       key=os.path.getmtime)
        paths = paths if a.all else paths[-1:]
    T = W = 0
    for p in paths:
        t, w = report(p)
        T += t
        W += w
    if len(paths) > 1:
        print(f"\n{len(paths)} captures: {T} armed trial(s), {W} teleport(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
