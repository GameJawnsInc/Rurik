#!/usr/bin/env python3
"""Who halted the body: the client's agent-avoidance solver, per agent, joined to the tape (MOVECODE-1z-be).

    python studies/movecode/review/solverhalts.py <harness run id> --hook <movehook.bin> --press X,Y

THE QUESTION. `chcli_advance` (0x0081B580) feeds the next queued waypoint only on
notify 5 (arrival). In RUN-1zBD run 2 it never fired on the S press; the hook shows
the halt-at-point 0x006020B0 entered from 0x0060189E instead -- the agent-avoidance
solver 0x006011F0's "blocked, no sidestep" exit, which raises notify 4 and lands in
ChCliBase case 4 (ClearPath + resume_arm, hook `resume_arm` returning to 0x0081B53C).
This tool makes that reading a census rather than one window:

  1. every halt with return address 0x0060189E, by (world, agent id) -- the follower's
     async copy produces almost all of them; the PLAYER's are rare;
  2. for each PLAYER halt (world 1, id 1): the body's point, velocity and target from
     the record, and every OTHER agent's live position from the agenttap tape at that
     wall time -- distance to the body, distance to the target, and the cosine of the
     bearing against the body's velocity. The solver's own filter is closing pairs
     inside a 60-degree forward cone (cos > 0.5, [0x9458BC]) whose combined radius
     already contains the mover; the sidestep computer refuses outright when that
     radius also covers m_targetPoint (0x006005D1..0x006005DA). A halt with cos <= 0.5
     against every tapped agent means an agent the tape does not carry;
  3. dispatch counts per hold window around --press: GmWalk's silent re-entries
     (movecmd returning to 0x00535EA4, arg6 = 0) and key-edge dispatches (0x00535DF3),
     plus the server's own agtrack_repin rows -- so a parked hold can be read as
     "our 0x002C halted it and the held key never re-dispatched" or not.

Hook ticks are aligned to the wall on agapi_setdest anchors (leadtap.align); the
spread is printed. Return addresses are rebased with the capture's own base. Needs
the vault (captures, tape). Stdlib only, read-only.
"""
import argparse
import bisect
import glob
import json
import math
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "clientscan", "movehook"))

SOLVER_HALT = 0x0060189E     # 0x006011F0's notify-4 halt: call 0x006020B0 at 0x00601899
ARRIVAL_HALT = 0x00600333    # the tick's arrival: call 0x006020B0 at 0x0060032E
INSTALL_HALT = 0x00602B79    # setposition 0x00602B20's moving branch (our 0x002C lands here)
CASE4_RET = 0x0081B53C       # ChCliBase notify case 4 -> ClearPath, then resume_arm
ADVANCE_RET = 0x0081B54D     # ChCliBase notify case 5 -> chcli_advance
REENTRY_RET = 0x00535EA4     # GmWalk's silent per-frame MOVE-CMD (arg6 = 0)
KEYEDGE_RET = 0x00535DF3     # GmWalk's key-edge MOVE-CMD (arg6 = 1)


def _f(dw):
    return struct.unpack("<f", struct.pack("<I", dw))[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="harness run id")
    ap.add_argument("--hook", required=True)
    ap.add_argument("--press", default=None, help="X,Y of the client destination the hold windows are measured from")
    ap.add_argument("--tape", default=None)
    a = ap.parse_args()
    from vaultpath import require_dir
    import readhook
    import seamscore as SC
    from leadtap import align, leads_from
    vault = require_dir()
    rundir = os.path.join(vault, "captures", "harness", a.run)
    rep = json.load(open(os.path.join(rundir, "report.json")))
    cap_path = [c.replace("\\", "/") for c in rep["captures"] if "gamesrv" in c.replace("\\", "/")][0]
    R, _bad = SC.load_rows(cap_path)
    t_lo = min(w["started_unix"] for w in rep["walk"]) - 120
    t_hi = max(w["ended_unix"] for w in rep["walk"]) + 60
    tapes = sorted(glob.glob(os.path.join(vault, "research", "animref", "agenttap-*.jsonl")))
    tape = SC.Tape(a.tape or SC.pick_tape(tapes, t_lo, t_hi))
    hook = readhook.Capture(a.hook)
    names = readhook.site_names(hook)
    idx = {n: i for i, n in enumerate(names)}
    delta = hook.base - readhook.static_base()
    grants = [(g, d) for g, _o, _p, d, _raw, _w in leads_from(R)]
    for r in R:
        if r.get("kind") == "grant_verdict" and r.get("fired") and r.get("dest"):
            grants.append((r["wall_unix"], tuple(r["dest"])))
    off, n_anch, spread = align(hook, names, grants)
    if off is None:
        print("cannot align the hook to the wall; nothing below is joinable")
        return 1
    print("run %s: hook %s (v%d, %d records), tape %s, offset from %d anchors, spread %.0f ms"
          % (a.run, os.path.basename(a.hook), hook.version, hook.stored, os.path.basename(tape.path), n_anch, spread))

    def ret(r):
        return r["retaddr"] - delta

    tel = idx["teleport"]
    by = {}
    for r in hook.recs:
        if r["site"] == tel and ret(r) == SOLVER_HALT:
            k = (r.get("world"), r.get("id"))
            by[k] = by.get(k, 0) + 1
    print("solver halts (0x%08X) by (world, id): %s" % (SOLVER_HALT, ", ".join("w%s id %s: %d" % (k[0], k[1], n) for k, n in sorted(by.items()))))

    tt = [tape.t0 + s["t"] for s in tape.samples]

    def others_at(wall):
        i = bisect.bisect_left(tt, wall)
        cands = [j for j in (i - 1, i) if 0 <= j < len(tt)]
        if not cands:
            return None, {}
        j = min(cands, key=lambda j: abs(tt[j] - wall))
        s = tape.samples[j]
        out = {}
        for aid, ag in (s.get("agents") or {}).items():
            if aid == "1":
                continue
            c = ag.get("async")
            p = SC.live(c, s.get("clock1"))
            if p is not None:
                out[aid] = (p, c.get("vx") or 0.0, c.get("vy") or 0.0)
        return abs(tt[j] - wall), out

    print("PLAYER halts (world 1, id 1):")
    n_player = 0
    for r in hook.recs:
        if r["site"] != tel or ret(r) != SOLVER_HALT or r.get("world") != 1 or r.get("id") != 1:
            continue
        n_player += 1
        wall = r["tick"] / 1000.0 + off
        bx, by_ = _f(r["point"][0]), _f(r["point"][1])
        tx, ty = _f(r["target"][0]), _f(r["target"][1])
        vx, vy = _f(r["vel"][0]), _f(r["vel"][1])
        sp = math.hypot(vx, vy)
        dtap, others = others_at(wall)
        seg = math.hypot(tx - bx, ty - by_) if math.isfinite(tx) else float("nan")
        print("  wall %.3f: body (%.1f,%.1f) v(%.0f,%.0f) -> target (%.1f,%.1f), %.1f u%s"
              % (wall, bx, by_, vx, vy, tx, ty, seg, "" if dtap is not None else " (no tape sample)"))
        for aid, ((nx, ny), nvx, nvy) in sorted(others.items(), key=lambda kv: int(kv[0])):
            d_body = math.hypot(nx - bx, ny - by_)
            d_tgt = math.hypot(nx - tx, ny - ty) if math.isfinite(tx) else float("nan")
            cos = ((nx - bx) * vx + (ny - by_) * vy) / (d_body * sp) if d_body and sp else float("nan")
            print("      agent %s at (%.1f,%.1f) v(%.0f,%.0f): d_body %.1f  d_target %.1f  cos %.2f  %s (tape dt %.2f s)"
                  % (aid, nx, ny, nvx, nvy, d_body, d_tgt, cos, "IN CONE" if cos > 0.5 else "outside the cone", dtap))
    if not n_player:
        print("  none")

    if a.press:
        px, py = (float(s) for s in a.press.split(","))
        sd = idx["agapi_setdest"]
        anchor = next((r for r in hook.recs if r["site"] == sd and r.get("have_pts")
                       and abs(_f(r["pt_a"][0]) - px) < 0.6 and abs(_f(r["pt_a"][1]) - py) < 0.6), None)
        if anchor is None:
            print("no agapi_setdest within 0.6 u of --press")
            return 1
        t0 = anchor["tick"]
        press_wall = t0 / 1000.0 + off

        # ChCliBase objects: the hook records resume_arm / chcli_advance for EVERY
        # char (the follower has one too), so the player's are told by ecx -- the
        # object chcli_dir ran on, which asserts this == playerControlledChar.
        player_ecx = set(r["ecx"] for r in hook.recs if r["site"] == idx["chcli_dir"])

        def count(site, lo, hi, want=None, player_char=False, drawn_body=False):
            i = idx[site]
            return sum(1 for r in hook.recs if r["site"] == i and lo <= r["tick"] - t0 <= hi
                       and (want is None or ret(r) == want) and (not player_char or r["ecx"] in player_ecx)
                       and (not drawn_body or (r.get("world") == 1 and r.get("id") == 1)))

        # the last time our position installer HALTED the player's drawn body before
        # the press (setposition's moving branch) splits the preceding hold in two
        inst = [r["tick"] - t0 for r in hook.recs if r["site"] == tel and ret(r) == INSTALL_HALT
                and r.get("world") == 1 and r.get("id") == 1 and -6000 <= r["tick"] - t0 < -10]
        split = max(inst) if inst else -3700
        print("around the press at (%g, %g), wall %.3f; last install-halt of the drawn body at %+d ms%s:"
              % (px, py, press_wall, split, "" if inst else " (none seen; default split)"))
        for lo, hi, label in ((split - 900, split, "before the install"), (split + 1, -10, "after it, key still held"), (10, 4000, "the next hold")):
            print("  [%+5d,%+5d] ms %-26s movecmd %d (silent re-entry %d, key-edge %d)  player advances %d  player case-4 clears %d  drawn-body installs %d  inputeval %d"
                  % (lo, hi, label, count("movecmd", lo, hi), count("movecmd", lo, hi, REENTRY_RET), count("movecmd", lo, hi, KEYEDGE_RET),
                     count("chcli_advance", lo, hi, player_char=True), count("resume_arm", lo, hi, CASE4_RET, player_char=True),
                     count("teleport", lo, hi, INSTALL_HALT, drawn_body=True), count("inputeval", lo, hi)))
        print("  server agtrack_repin rows within 6 s:")
        for r in R:
            if r.get("kind") in ("agtrack_repin", "agtrack_repin_fire") and abs(r["wall_unix"] - press_wall) < 6:
                print("    %+6.2f s %-18s %s" % (r["wall_unix"] - press_wall, r["kind"],
                                                json.dumps({k: v for k, v in r.items() if k not in ("kind", "wall_unix", "wall", "t")})))
    return 0


if __name__ == "__main__":
    sys.exit(main())
