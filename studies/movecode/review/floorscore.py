#!/usr/bin/env python3
"""Score RUN-1zCW arms: one line per tape, the capture found by the tape's own wall span.

    python studies/movecode/review/floorscore.py T2 C2 T3 C3

Per arm: the capture's header floor, the heading-verdict census, how many reports arrived
inside 0.5 s of the previous grant (`since_last`, the floor's own operand), the tape's rate,
the moving span, and world-0 vs the drawn body while moving (p50 / p90). Then the sheet's
P1-P4 per arm and the T/C pairing. Read-only; needs the vault.
"""
import collections
import glob
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "studies/movecode/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))
import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402

FLOOR_S = 20.0        # s of moving samples (the harness tape runs ~11 Hz)
FLOOR_EVAL = 40


def cap_for(tape):
    head, rows = W.load(tape)
    lo, hi = head["t0"], head["t0"] + rows[-1]["t"]
    d = vaultpath.require_dir("captures", "gamesrv")
    for p in sorted(glob.glob(os.path.join(d, "authsrv-*-c1.jsonl")))[-40:]:
        wu = [r["wall_unix"] for r in W.load_gamesrv(p)
              if isinstance(r.get("wall_unix"), (int, float))]
        if wu and min(wu) <= hi and max(wu) >= lo:
            return p
    return None


def score(arm):
    tape = vaultpath.vault_path("research", "movecode", f"1zcw-{arm}-agenttap.jsonl")
    cap = cap_for(tape)
    if cap is None:
        return {"arm": arm, "error": "no capture overlaps the tape"}
    rows = W.load_gamesrv(cap)
    fl = next((r for r in rows if r.get("kind") == "flags"), {})
    gv = [r for r in rows if r.get("kind") == "grant_verdict" and r.get("arm") == "zero-lead"]
    c = collections.Counter(("deferred" if r.get("deferred") else
                             ("fired" if r.get("fired") else r.get("reason"))) for r in gv)
    since = [r["since_last"] for r in gv if r.get("since_last") is not None]
    head, trows = W.load(tape)
    p1 = W.series(head, trows, 1)
    mv = [r for r in p1 if r["vbody"] > 1.0]
    hz = len(trows) / max(1e-9, trows[-1]["t"] - trows[0]["t"])
    sep = sorted(math.dist(r["w0"], r["body"]) for r in mv)
    return {"arm": arm, "cap": os.path.basename(cap), "floor": fl.get("KBD_GRANT_FLOOR"),
            "n": len(gv), "fired": c.get("fired", 0), "refused": c.get("heading-rate", 0),
            "deferred": c.get("deferred", 0),
            "inside": sum(1 for x in since if x < 0.5), "since_n": len(since),
            "hz": hz, "moving_s": len(mv) / hz if hz else 0.0,
            "p50": sep[len(sep) // 2] if sep else float("nan"),
            "p90": sep[int(0.9 * len(sep))] if sep else float("nan")}


def main(argv):
    out = {}
    print("arm  floor  capture            evals fired refused deferred  inside<0.5s   tape Hz  moving s   w0-body p50 / p90")
    for arm in argv:
        r = score(arm)
        out[arm] = r
        if "error" in r:
            print(f"{arm:4} {r['error']}")
            continue
        print(f"{arm:4}  {r['floor']!s:5}  {r['cap'][8:23]:17} {r['n']:5} {r['fired']:5} {r['refused']:7} "
              f"{r['deferred']:8}  {r['inside']:4} of {r['since_n']:3}   {r['hz']:5.1f}   {r['moving_s']:6.1f}"
              f"   {r['p50']:6.1f} / {r['p90']:6.1f}")
    print("\nP1 exposure (>= %d evaluations, >= %.0f s moving):" % (FLOOR_EVAL, FLOOR_S))
    for arm, r in out.items():
        if "error" in r:
            continue
        ok = r["n"] >= FLOOR_EVAL and r["moving_s"] >= FLOOR_S
        print(f"   {arm}: {'MET' if ok else 'UNDER'}")
    ts = [a for a in out if a.startswith("T") and "error" not in out[a]]
    cs = [a for a in out if a.startswith("C") and "error" not in out[a]]
    for c in cs:
        r = out[c]
        frac = r["refused"] / max(1, r["n"])
        print(f"P2 {c}: refused {100 * frac:.1f}% ({'MET' if frac >= 0.4 else 'UNDER'} 40%), "
              f"w0-body p50 {r['p50']:.1f} ({'MET' if r['p50'] >= 80 else 'UNDER'} 80 u)")
    for t in ts:
        r = out[t]
        print(f"P3 {t}: refused {r['refused']} deferred {r['deferred']} "
              f"({'MET' if r['refused'] == 0 and r['deferred'] == 0 else 'FAILED'} zero), "
              f"w0-body p50 {r['p50']:.1f} ({'MET' if r['p50'] < 60 else 'FAILED'} < 60 u)")
    for t, c in zip(ts, cs):
        rt, rc = out[t], out[c]
        ratio = rt["p50"] / rc["p50"] if rc["p50"] else float("nan")
        print(f"PAIR {t}/{c}: T p50 {rt['p50']:.1f} vs C {rc['p50']:.1f} = {ratio:.2f} "
              f"({'MET' if ratio < 0.5 else 'FAILED'} < 0.5; refuted-if bar is >= 0.75: "
              f"{'REFUTED' if ratio >= 0.75 else 'not refuted'})")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
