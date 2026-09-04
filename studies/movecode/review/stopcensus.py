#!/usr/bin/env python3
"""The SWALLOWED 0x0047: which key legs went unclosed, and does the arc's
explanation predict them?

    python studies/movecode/review/stopcensus.py
    python studies/movecode/review/stopcensus.py --all-runs

WHAT IT IS FOR. FINDINGS sec.1z-ad recorded that a keyboard release "was
swallowed" -- no `0x0047` reached the wire -- and named the cause: a 520 u lead
MATURED 0.26 s before the player let go. That reading became the arc's leading
account of the lock. This scores it against every scripted run in the vault.

THE DENOMINATOR IS THE KEY LEG, NOT THE MESSAGE. A first pass compared `0x0047`
counts against `0x003D` counts and read a 0.15 baseline ratio -- meaningless,
because `0x003D` fires on every heading change, not once per leg. The harness
walk spec records each key's own press and release instant, so the honest unit
is "did a `0x0047` arrive within 1.5 s of THIS release". Two controls the first
pass also lacked: a leg whose capture ENDED before a stop could arrive is scored
`?` and excluded (it is not a miss), and the rate is broken out per key, because
A and D turn in place and never report a stop at all.

THE SIGNATURE IS TERMINAL, NOT A RATE. Healthy runs miss a leg here and there
and recover; a locked run reports a PREFIX and then never again. So the readout
is trailing silence -- legs after the last closed one -- and >= 2 is the lock.
Baseline runs never reach 2; they show at most 1, which is the capture ending.

THE REGISTERED TEST, and it FAILED. Prediction: the runs that go terminally
silent are exactly those where a clear-clipped lead's maturation instant
(`t_arm + 520/speed`, both from the server's own `kbd_leg` row -- no free
parameter) falls before that leg's release. REFUTED: six healthy runs carry
exactly that event, and one locked run carries none. Maturation-before-release
is neither necessary nor sufficient. That is consistent with REALFIX sec.0.11,
which says the lock needs TWO stages and "neither alone suffices" -- it refutes
sec.1z-ad's framing of the maturation as "the door", not sec.0.11.

A DISCRIMINATOR THAT LOOKS PERFECT AND IS CIRCULAR, printed with its warning
because it would otherwise be re-discovered and believed: `lead_clip_why ==
"fence-shut"` separates the two groups almost exactly. It cannot be evidence.
`fence_shut_at` is OUR flag, cleared by a client walk-start report; when the
client stops reporting, the flag stops clearing. It is the same silence read
from the server's side, not an independent cause.

Read-only over the harness reports and gamesrv captures already in the vault.
"""
import argparse
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))

LEAD = 520.0            # authsrv.KBD_SYNC_LEAD
WINDOW = 1.5            # seconds after a release in which a stop must land
TAIL_LOCK = 2           # trailing silent legs that mean a lock


def runs():
    import vaultpath
    har = vaultpath.vault_path("captures", "harness")
    for rp in sorted(glob.glob(os.path.join(har, "*", "report.json"))):
        try:
            rep = json.load(open(rp, encoding="utf-8"))
        except (OSError, ValueError):
            continue
        walk = [w for w in (rep.get("walk") or [])
                if w.get("kind") == "key" and w.get("ended_unix")]
        caps = [c.replace("\\", "/") for c in (rep.get("captures") or [])
                if "gamesrv" in c.replace("\\", "/")]
        if not walk or not caps or not os.path.exists(caps[0]):
            continue
        try:
            rows = [json.loads(l) for l in open(caps[0], encoding="utf-8") if l.strip()]
        except (OSError, ValueError):
            continue
        if rows:
            yield os.path.basename(os.path.dirname(rp)), walk, rows


def score(walk, rows):
    end = rows[-1]["wall_unix"]
    flags = next((r for r in rows if r.get("kind") == "flags"), {})
    lead_on = flags.get("KBD_SYNC_LEAD_ON")
    stops = [r["wall_unix"] for r in rows if r.get("kind") == "decoded"
             and r.get("name") == "MOVE_CANCEL_REPORT_POSITION"]
    arms = [r for r in rows if r.get("kind") == "kbd_leg" and r.get("act") == "arm"]
    grants = [r for r in rows if r.get("kind") == "grant_verdict"]

    def clip_at(w):
        hit = None
        for g in grants:
            if abs(g["wall_unix"] - w) < 0.05:
                hit = g.get("lead_clip_why")
        return hit

    legs = []
    for w in walk:
        s, e = w["started_unix"], w["ended_unix"]
        closed = (None if end < e + WINDOW
                  else (1 if any(e - 0.2 <= x <= e + WINDOW for x in stops) else 0))
        early = []
        for a in arms:
            if s - 0.05 <= a["wall_unix"] <= e and clip_at(a["wall_unix"]) == "clear":
                mat = a["wall_unix"] + LEAD / (a.get("speed") or 288.0)
                if mat < e:
                    early.append(mat)
        legs.append({"key": w["key"], "closed": closed, "early": early, "rel": e})
    fence_shut = sum(1 for g in grants if g.get("lead_clip_why") == "fence-shut")
    return lead_on, legs, fence_shut


def trailing(legs):
    sc = [l["closed"] for l in legs if l["closed"] is not None]
    if not sc or sum(sc) == 0:
        return None
    last = max(i for i, h in enumerate(sc) if h == 1)
    return len(sc) - 1 - last


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--all-runs", action="store_true",
                    help="print every scripted run, not just the lead ones")
    a = ap.parse_args()

    table = []
    for name, walk, rows in runs():
        lead_on, legs, fshut = score(walk, rows)
        table.append((name, lead_on, legs, fshut))
    if not table:
        print("no scripted harness runs in the vault -- nothing measured, which is "
              "not a result. This needs a vault machine.")
        return 1

    perkey = {}
    for _n, _l, legs, _f in table:
        for l in legs:
            if l["closed"] is None:
                continue
            n, h = perkey.get(l["key"], (0, 0))
            perkey[l["key"]] = (n + 1, h + l["closed"])
    print("PER-KEY closure (legs whose capture ran >= %.1f s past the release):" % WINDOW)
    for k in sorted(perkey):
        n, h = perkey[k]
        print("   key %-3s n=%-4d closed %-4d (%3.0f%%)" % (k, n, h, 100.0 * h / n))
    print("   A and D TURN IN PLACE and report no stop; digits are skill keys.\n")

    for want, label in ((True, "KBD_LEAD ON"), (None, "lead flag absent")):
        s = [l["closed"] for _n, lo, legs, _f in table if lo is want
             for l in legs if l["closed"] is not None and l["key"] in ("W", "S")]
        if s:
            print("W/S legs only, %-17s %3d legs, %3d closed (%.0f%%)"
                  % (label, len(s), sum(s), 100.0 * sum(s) / len(s)))

    print("\n%-18s %-6s %-16s %-9s %-10s %s"
          % ("run", "lead", "pattern", "trailing", "LOCK", "early maturation?"))
    tp = fp = fn = tn = 0
    for name, lead_on, legs, fshut in table:
        tr = trailing(legs)
        if tr is None:
            continue
        if not a.all_runs and lead_on is not True and tr < TAIL_LOCK:
            continue
        pat = "".join("Y" if l["closed"] == 1 else ("." if l["closed"] == 0 else "?")
                      for l in legs)
        lock = tr >= TAIL_LOCK
        early = any(l["early"] for l in legs)
        if lead_on is True:
            if lock and early: tp += 1
            elif lock: fn += 1
            elif early: fp += 1
            else: tn += 1
        print("%-18s %-6s %-16s %-9d %-10s %s"
              % (name, str(lead_on), pat, tr, "YES" if lock else "no",
                 "yes" if early else "no"))

    print("\nTHE REGISTERED TEST (lead runs only): does 'a clear lead matured before")
    print("the release' pick out the locked runs?")
    print("   locked WITH an early maturation   : %d" % tp)
    print("   healthy with NONE                 : %d" % tn)
    print("   locked with NO early maturation   : %d   <- refutes if > 0" % fn)
    print("   healthy WITH an early maturation  : %d   <- refutes if > 0" % fp)
    if fn or fp:
        print("\n   REFUTED. Maturation-before-release is neither necessary nor")
        print("   sufficient for the swallowed stop. REALFIX sec.0.11 says the lock")
        print("   needs TWO stages and 'neither alone suffices'; this refutes")
        print("   sec.1z-ad's framing of the maturation as 'the door', not sec.0.11.")
    else:
        print("\n   CONFIRMED -- but check the corpus has grown before quoting it.")

    print("\nCIRCULAR, printed so it is not re-discovered and believed:")
    for want in (True, False):
        g = [f for _n, lo, legs, f in table
             if lo is True and ((trailing(legs) or 0) >= TAIL_LOCK) is want]
        if g:
            print("   LOCK=%-5s fence-shut lead counts: %s" % (want, g))
    print("   `fence_shut_at` is OUR flag and a client walk-start clears it. When the")
    print("   client stops reporting, the flag stops clearing -- the same silence read")
    print("   from the server's side. NOT an independent cause.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
