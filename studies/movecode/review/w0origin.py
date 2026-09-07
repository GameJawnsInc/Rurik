#!/usr/bin/env python3
"""Retrodict a session's keyboard leads through MOVECODE-1z-cg's two doors.

    python studies/movecode/review/w0origin.py                 # RUN-FEEL2, the founding tape
    python studies/movecode/review/w0origin.py --check         # with sec.1z-cg's pins
    python studies/movecode/review/w0origin.py --tape T [--cap C]   # another session

THE QUESTION. The client bakes a grant from ITS settled world-0, not from the
report the grant answered (movement/FINDINGS 3724-3736). On RUN-FEEL2 at 63.8 s
(tape clock) a lead clear from the report crossed the hole above the stairs
from a world-0 that had stalled 230 u behind the body, gate 2 fired, and the
client snapped the body 166 u into the hole. Door B of 1z-cg re-clips every
lead from the mirror's copy of world-0; door A keeps a lead from ending inside
a hostile's disc (NPCTRACK-Q8's halt). This replays a session's fired keyboard
leads through `authsrv.a2_clip_lead` with the TAPE's world-0 (live, both
copies read through the client's own accessor) standing in for the mirror,
and the tape's hostile for the obstacle list, and prints every lead a door
changes.

WHAT MUST HOLD (--check, pinned 2026-09-07 on RUN-FEEL2):
  * the 63.8 s lead (capture clock 64.33 s, dest (11245, 9428)) becomes the
    corridor's first vertex from world-0, (11470, 8843) -- why clear+w0-route;
  * NO wall-slide lead is changed: door B is plane-blind and seam-tolerant so
    a leg along a trapezoid side holds (its first draft turned 12 confirmed
    slides into zero leads -- the known-bad draft this pins out);
  * every changed lead's new point is on our mesh.

The raw pre-clip dest is not logged, so the logged (already clipped) dest is
the ray's end here: only the doors can change it, never the clip.
Read-only. Stdlib only. Needs the vault.
"""
import bisect
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/mapdata",
            "studies/renderobj/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402
import authsrv                                     # noqa: E402

FEEL2_TAPE = ("research", "movecode", "feel2-agenttap.jsonl")
FEEL2_CAP = ("captures", "gamesrv", "authsrv-20260906T235141-c1.jsonl")
PIN_T = 64.33
PIN_DEST = (11245.0, 9428.0)
PIN_NEW = (11470.0, 8843.0)
PIN_WHY = "clear+w0-route"
CONTROLS = [("RUN-1zCE run 1", ("movecode", "1zce-agenttap.jsonl")),
            ("RUN-1zCE run 2", ("movecode", "1zce2-agenttap.jsonl")),
            ("RUN-Q9", ("npctrack", "q9-agenttap.jsonl"))]


class _Guard:
    """The mirror's world-0, as the door reads it: position(ms) and a plane."""

    def __init__(self, w0, plane):
        class _S:
            pass
        self.mirror = _S()
        self.mirror.sync = _S()
        self.mirror.sync.plane = plane
        self.mirror.sync.position = lambda ms, _w=w0: _w

    def _ms(self, now):
        return 0


def mesh_for(cap_rows):
    from meshcensus import Mesh
    import content
    mid = next((r.get("map_id") for r in cap_rows if r.get("kind") == "version"), None)
    fid = content.load().map_static_config()[int(mid)][0]
    return Mesh(fid)


def replay(tape, cap):
    head, rows = W.load(tape)
    caprows = W.load_gamesrv(cap)
    mesh = mesh_for(caprows)
    pm = mesh.pm
    tw = [head["t0"] + s["t"] for s in rows]

    def tape_at(wu):
        i = min(max(bisect.bisect_right(tw, wu) - 1, 0), len(rows) - 1)
        s = rows[i]
        a = s["agents"]["1"]
        h = s["agents"].get("10", {})
        w0 = W.live(a["sync"], s.get("clock0"))
        hat = (W.live(h["async"], s.get("clock1"))
               if h.get("async") and "x" in h["async"] else None)
        return w0, a["sync"].get("plane"), hat, s["t"]

    reps = [r for r in caprows if r.get("kind") == "position_report" and r.get("accepted")]
    rt = [r["t"] for r in reps]
    out = []
    for r in caprows:
        if r.get("kind") != "grant_verdict" or not r.get("fired") or r.get("lead_src") != "kbd":
            continue
        i = bisect.bisect_right(rt, r["t"]) - 1
        if i < 0:
            continue
        rep = reps[i]
        w0, w0pl, hat, tt = tape_at(r["wall_unix"])
        st = {"pos": tuple(rep["reported"]), "plane": rep["plane"], "pathmap": pm,
              "agtrack_guard": _Guard(w0, w0pl if w0pl is not None else rep["plane"]),
              "agents": ({10: {"pos": hat, "dead": False, "name": "hatcher", "plane": 0}}
                         if hat else {})}
        got, _c, why = authsrv.a2_clip_lead(st, rep["reported"], list(r["dest"]))
        out.append(dict(t=r["t"], tape_t=tt, rep=tuple(rep["reported"]), w0=w0,
                        sep=math.dist(w0, rep["reported"]), hat=hat, dest=tuple(r["dest"]),
                        old_why=r.get("lead_clip_why"), new=tuple(got), why=why,
                        changed="+" in why, on_mesh=mesh.off(got[0], got[1]) <= authsrv.A2_LEAD_W0_SEAM))
    return out


def main(argv):
    if "--tape" in argv:
        tape = argv[argv.index("--tape") + 1]
        cap = argv[argv.index("--cap") + 1] if "--cap" in argv else None
        if cap is None:
            head, rows = W.load(tape)
            cap = W.find_gamesrv(head, rows)
            if cap is None:
                raise SystemExit("no gamesrv capture overlaps %s" % tape)
    else:
        tape = os.path.join(vaultpath.require_dir(*FEEL2_TAPE[:-1], why="RUN-FEEL2's tape"), FEEL2_TAPE[-1])
        cap = os.path.join(vaultpath.require_dir(*FEEL2_CAP[:-1], why="RUN-FEEL2's capture"), FEEL2_CAP[-1])
    res = replay(str(tape), str(cap))
    ch = [r for r in res if r["changed"]]
    print("%s: %d fired keyboard leads, %d changed by a door" % (os.path.basename(str(cap)), len(res), len(ch)))
    for r in ch:
        print("  cap %6.2f tape %6.2f report (%.0f,%.0f) w0 (%.0f,%.0f) %3.0f u behind hatcher %s | (%.0f,%.0f) [%s] -> (%.0f,%.0f) %s%s" % (
            r["t"], r["tape_t"], r["rep"][0], r["rep"][1], r["w0"][0], r["w0"][1], r["sep"],
            None if not r["hat"] else (round(r["hat"][0]), round(r["hat"][1])),
            r["dest"][0], r["dest"][1], r["old_why"], r["new"][0], r["new"][1], r["why"],
            "" if r["on_mesh"] else "  OFF MESH"))
    if "--check" not in argv:
        return 0
    bad = 0

    def bar(ok, text):
        nonlocal bad
        print("  [%s] %s" % ("PASS" if ok else "FAIL", text))
        bad += 0 if ok else 1

    print("\n--check, sec.1z-cg's pins on RUN-FEEL2")
    pin = [r for r in res if abs(r["t"] - PIN_T) < 0.05 and math.dist(r["dest"], PIN_DEST) <= 1.0]
    bar(len(pin) == 1 and pin[0]["why"] == PIN_WHY and math.dist(pin[0]["new"], PIN_NEW) <= 1.0,
        "the 63.8 s lead to %s becomes %s, why %s" % (PIN_DEST, PIN_NEW, PIN_WHY)
        + ("" if not pin else " -- got %s %s" % (pin[0]["new"], pin[0]["why"])))
    bar(all(r["on_mesh"] for r in ch), "every changed lead's point is on our mesh (within %.0f u)" % authsrv.A2_LEAD_W0_SEAM)
    bar(len(res) >= 40, "exposure: %d fired keyboard leads >= 40" % len(res))
    # THE SCRIPTED CONTROLS: three stairs climbs the arc confirmed (RUN-1zCE x2,
    # RUN-Q9), none of which snapped -- a door that changes a lead there is
    # firing where nothing was wrong (the first draft changed the foot-of-the-
    # stairs slide on all three).
    rr = vaultpath.vault_root()
    for name, tp in CONTROLS:
        tpath = os.path.join(rr, "research", *tp)
        if not os.path.exists(tpath):
            print("  [SKIP] control %s: tape missing" % name)
            continue
        head, rows = W.load(tpath)
        cpath = W.find_gamesrv(head, rows)
        if cpath is None:
            print("  [SKIP] control %s: no overlapping capture" % name)
            continue
        cres = replay(tpath, cpath)
        cch = [r for r in cres if r["changed"]]
        bar(not cch and len(cres) >= 10, "control %s: %d leads, %d changed" % (name, len(cres), len(cch)))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
