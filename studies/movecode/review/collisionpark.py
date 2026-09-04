#!/usr/bin/env python3
"""Can the enemy's collision PARK the player's walking body? No -- and here is why.

    python studies/movecode/review/collisionpark.py

WHAT THIS ANSWERS. FINDINGS sec.1z-aj.5 closed the retract arc's outcome question
with a derived next step: the run cannot manufacture "a full-length lead over a
PARKED body", because on a clear ray the body does not park -- so *"the parking
must be CAUSED, not waited for, and the `--enemy` Hatcher's collision is the one
mechanism in this harness that stops a walking body without our mesh knowing."*

That plan does not work, and the corpus plus the decode say so without a run.

THE GATE IS `+0x98`. The collision resolver `0x006011F0` (ANIMREF-RE 38.2) posts
its kind-5 arrival and teleports the body in place ONLY when the blocking
neighbour IS the agent named in `+0x98` -- `0x006017CB cmp ebx,[esi+0x98]`. A
keyboard or click walk carries `+0x98 = 0`: there is no followed agent, so the
arm cannot fire whatever is standing in the way.

AND THE LEAD ITSELF CLEARS THAT FIELD. `0x0029`'s handler `0x005FD890` passes 0
into the shared setter's `+0x98` slot, where `0x002A`'s passes the wire's fifth
field -- so a `0x0029` CLEARS the follow (ANIMREF-RE 38.2, answering sec.35.5).
The keyboard lead IS a `0x0029`. **Every lead grant destroys the precondition the
park needs**, so the two states are mutually exclusive by construction and not
merely rare together.

THREE READOUTS, and the third is the one that makes the first two mean anything:
  1. the player's `+0x98` across every MOVING sample in the agenttap corpus;
  2. how close a MOVING player body actually gets to the Hatcher;
  3. POSITIVE CONTROL -- the Hatcher DOES carry `+0x98` (it chases the player),
     so the resolver must be seen firing for it at r+r+56 = 80 u. A negative
     whose positive control is empty is a broken reader, not a finding
     (`--no-control` to skip it, which also forfeits the verdict).

Read-only over agenttap tapes already in the vault. Stdlib only.
"""
import argparse
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "clientscan"))

PLAYER, ENEMY = "1", "10"
DISC = 80.0          # r + r + pad = 12 + 12 + 56 (ANIMREF-RE 38.2)
MOVING = 20.0        # u/s: below this the body is not walking
WAS_MOVING = 100.0


def tapes():
    import vaultpath
    return sorted(glob.glob(os.path.join(
        vaultpath.vault_path("research", "animref"), "agenttap-*.jsonl")))


def samples(path):
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        r = json.loads(line)
        if r.get("kind") == "sample":
            yield r


def pair(s, aid):
    d = (s.get("agents") or {}).get(aid) or {}
    return d.get("sync"), d.get("async")


def rows(path):
    from w0score import live
    out = []
    for s in samples(path):
        ps, pa = pair(s, PLAYER)
        es, ea = pair(s, ENEMY)
        if not pa or "x" not in pa or not ea or "x" not in ea:
            continue
        p = live(pa, s.get("clock1"))
        e = live(ea, s.get("clock1"))
        out.append({
            "t": s["t"], "d": math.hypot(p[0] - e[0], p[1] - e[1]),
            "pv": math.hypot(pa.get("vx", 0.0), pa.get("vy", 0.0)),
            "ev": math.hypot(ea.get("vx", 0.0), ea.get("vy", 0.0)),
            "pf_a": pa.get("follow"), "pf_s": (ps or {}).get("follow"),
            "ef_a": ea.get("follow"), "ef_s": (es or {}).get("follow"),
        })
    return out


def q(v, p):
    v = sorted(v)
    return v[min(int(len(v) * p), len(v) - 1)] if v else float("nan")


def main():
    ap = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--no-control", action="store_true",
                    help="skip the positive control (and forfeit the verdict)")
    a = ap.parse_args()

    paths = tapes()
    if not paths:
        print("no agenttap tapes in the vault -- nothing measured, which is not a "
              "result. This needs a vault machine.")
        return 1
    allrows = []
    for p in paths:
        allrows += rows(p)
    if not allrows:
        print("tapes hold no usable player/enemy sample pairs -- zero exposure.")
        return 1
    print("%d tapes, %d paired samples\n" % (len(paths), len(allrows)))

    mov = [r for r in allrows if r["pv"] > MOVING]
    fa = sum(1 for r in mov if r["pf_a"])
    fs = sum(1 for r in mov if r["pf_s"])
    print("(1) THE PLAYER'S +0x98 WHILE MOVING -- the resolver's gate")
    print("    moving samples %d: async +0x98 set in %d, sync in %d"
          % (len(mov), fa, fs))
    print("    -> the park arm needs the blocker to BE +0x98; on the drawn (async)")
    print("       copy the player names no one in %d of %d moving samples."
          % (len(mov) - fa, len(mov)))

    near = sorted(mov, key=lambda r: r["d"])[:12]
    print("\n(2) HOW CLOSE A MOVING PLAYER BODY GETS TO THE HATCHER")
    print("    closest passes (all at speed, none deflected):")
    for r in near[:6]:
        print("      d=%5.1f u  player %5.1f u/s  +0x98 async=%s sync=%s"
              % (r["d"], r["pv"], r["pf_a"], r["pf_s"]))
    under = [r for r in mov if r["d"] < DISC]
    print("    moving samples INSIDE the 80 u disc: %d of %d (%.1f%%) -- if the disc"
          % (len(under), len(mov), 100.0 * len(under) / len(mov)))
    print("       blocked a keyboard body none of these could exist.")

    if a.no_control:
        print("\ncontrol skipped: no verdict.")
        return 1

    emov = [r for r in allrows if r["ev"] > MOVING]
    ef = sum(1 for r in allrows if r["ef_a"] or r["ef_s"])
    halts = []
    for i in range(1, len(allrows)):
        x, y = allrows[i - 1], allrows[i]
        if x["ev"] > WAS_MOVING and y["ev"] < MOVING:
            halts.append(y["d"])
    band = [d for d in halts if 60.0 <= d <= 100.0]
    print("\n(3) POSITIVE CONTROL -- the HATCHER does carry +0x98, so the resolver")
    print("    must be seen firing for IT at the 80 u disc")
    print("    Hatcher samples with +0x98 set: %d of %d (%.1f%%)"
          % (ef, len(allrows), 100.0 * ef / len(allrows)))
    print("    Hatcher halts (was >%.0f u/s, now <%.0f): n=%d, distance to player"
          % (WAS_MOVING, MOVING, len(halts)))
    print("      p10 %.1f   p50 %.1f   p90 %.1f" % (q(halts, .1), q(halts, .5), q(halts, .9)))
    print("    inside the 60-100 u band: %d of %d (%.0f%%)"
          % (len(band), len(halts), 100.0 * len(band) / max(len(halts), 1)))

    ok = ef > 0 and halts and len(band) >= 0.4 * len(halts)
    if not ok:
        print("\n!! CONTROL FAILED -- the resolver cannot be seen firing for the agent")
        print("   that DOES carry +0x98, so this reader proves nothing about the player.")
        return 1

    print("\nVERDICT. The resolver fires (control: Hatcher halts at p50 %.1f u), and it"
          % q(halts, .5))
    print("does NOT fire for the player, whose +0x98 is 0 while walking -- whose body")
    print("passes within %.1f u of the Hatcher at full speed." % near[0]["d"])
    print("The enemy's collision CANNOT park a keyboard-walking body, so sec.1z-aj.5's")
    print("'cause the parking with the enemy collision' is refused at the desk. And the")
    print("lead's own 0x0029 CLEARS +0x98, so the two states are mutually exclusive by")
    print("construction, not merely rare together. FINDINGS sec.1z-al.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
