#!/usr/bin/env python3
"""Replay the six fatal-lead runs through the fixed guard and join them to their tapes (MOVECODE-1z-bi).

    python studies/movecode/review/leadreplay.py                 # the six locked runs + the healthy lead-ON control
    python studies/movecode/review/leadreplay.py 20260903T191246  # one harness run
    python studies/movecode/review/leadreplay.py --no-control

THE QUESTION. The keyboard lead (KBD_SYNC_LEAD, 520 u) ships OFF because sec.1z-ad
found it armed the lock on five of eight legs. sec.1z-be.4 then found the park at the
wedge tip was OUR gate2-offmesh 0x002C halting a drawn body walking under a held W,
after which GmWalk never re-dispatches the held key; sec.1z-ao.2 shows the lock is the
S press's lead maturing on a body that did not move for 3.0 s (arrival snap 520 u,
fence shut for good); sec.1z-bf removed that gate-2 veto (19 -> 0, control exact).
Nobody joined the three. This script does, per locked run, in one table:

  1. the gate2-offmesh 0x002C fired during the hold before the LOCK LEG's press (the
     run's first silent leg per sec.1z-am's signature -- leg 2 (S) for five locks, leg 4
     (Q) for two), and whether the fixed guard (agtrack_mirror.GATE2_SEAM_TOL) still
     licenses it -- guardretro's replay, both arms, the stock arm as the positive control;
  2. the drawn body's tape velocity before and after that 0x002C (the halt), and until
     the press;
  3. the kbd grant at the press (its reach and clip reason; full-length is >= 299 u) and
     the body's distance from the halt point when it was granted;
  4. the lead's arrival: the first >= 300 u drawn-body step after the grant inside the
     leg, and the fence state (the 09-03 tapes predate the fence column);
  5. the control contrast: did the body move after the press, and where was the
     follower (agent 10) and how far into the body's backpedal cone -- the sec.1z-be.2
     branch.

The pre-registered predictions (P1-P4, C1) are in FINDINGS sec.1z-bi; this script
prints the per-run rows and the tally against them and decides nothing itself.

Read-only. Needs the vault (captures/harness, captures/gamesrv, research/animref).
Stdlib only. Map 146 only.
"""
import argparse
import datetime as dt
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "authsrv"))

import guardretro  # noqa: E402  (events, replay, MAP146)

LOCKED = ["20260903T191246", "20260903T195857", "20260903T200549",
          "20260903T202051", "20260903T214957", "20260904T105954",   # sec.1z-ap.3, harness ids
          "20260903T073055"]   # the seventh lock, "no lead armed on its silent leg" per sec.1z-ap.3
GATE1 = 299.332591
LEAD_MIN = 299.0
MOVING = 50.0          # u/s: "the body is moving" for P2/P3/C1
PARKED = 1.0           # u/s: "parked"
S_SPEED = 190.08       # backpedal speed the lead's ETA uses (sec.1z-ao.2)
W_SPEED = 288.0


def stamp_dt(s):
    return dt.datetime.strptime(s, "%Y%m%dT%H%M%S")


def load_json_rows(path):
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out


def find_tape(vault, harness_id):
    """The agenttap tape started within [-5, +120] s of the harness launch."""
    h = stamp_dt(harness_id)
    best = None
    for p in glob.glob(os.path.join(vault, "research", "animref", "agenttap-*.jsonl")):
        s = os.path.basename(p)[9:24]
        try:
            d = (stamp_dt(s) - h).total_seconds()
        except ValueError:
            continue
        if -5 <= d <= 120 and (best is None or d < best[0]):
            best = (d, p)
    return None if best is None else best[1]


def tape_samples(path):
    rows = load_json_rows(path)
    if not rows or rows[0].get("kind") != "head":
        return None, []
    t0 = rows[0]["t0"]
    out = []
    for r in rows[1:]:
        if r.get("kind") != "sample":
            continue
        a1 = (r.get("agents") or {}).get("1") or {}
        a10 = (r.get("agents") or {}).get("10") or {}
        b = a1.get("async") or {}
        s = a1.get("sync") or {}
        f = (a1.get("fence") or {}).get("fence_state")
        fb = a10.get("async") or {}
        out.append({
            "w": t0 + r["t"],
            "body": (b.get("x"), b.get("y")),
            "v": math.hypot(b.get("vx", 0.0) or 0.0, b.get("vy", 0.0) or 0.0),
            "vel": (b.get("vx", 0.0) or 0.0, b.get("vy", 0.0) or 0.0),
            "sync": (s.get("x"), s.get("y")),
            "fence": f,
            "fol": (fb.get("x"), fb.get("y")) if fb else None,
        })
    return t0, out


def at(samples, w):
    """The sample nearest wall time w (None if the tape does not cover it)."""
    if not samples:
        return None
    best = min(samples, key=lambda s: abs(s["w"] - w))
    return best if abs(best["w"] - w) <= 0.25 else None


def window(samples, w0, w1):
    return [s for s in samples if w0 <= s["w"] <= w1]


def dist(a, b):
    if a is None or b is None or a[0] is None or b[0] is None:
        return None
    return math.hypot(a[0] - b[0], a[1] - b[1])


def analyse(vault, pm, harness_id, tol):
    rp = os.path.join(vault, "captures", "harness", harness_id, "report.json")
    rep = json.load(open(rp, encoding="utf-8"))
    caps = [c.replace("\\", "/") for c in rep.get("captures", []) if "gamesrv" in c.replace("\\", "/")]
    if not caps or not os.path.isfile(caps[0]):
        return {"id": harness_id, "skip": "no gamesrv capture"}
    rows = load_json_rows(caps[0])
    flags = next((r for r in rows if r.get("kind") == "flags"), {})
    legs = [w for w in (rep.get("walk") or []) if w.get("kind") == "key"]
    s_legs = [w for w in legs if w.get("key") == "S"]
    if not s_legs:
        return {"id": harness_id, "skip": "no S leg"}
    reports = [r for r in rows if r.get("kind") == "position_report"]

    # --- the lock signature (sec.1z-am: trailing legs with no 0x0047) ------------------
    stops = [r["wall_unix"] for r in reports if r.get("source") == "0x0047"]
    sig = "".join("Y" if any(w["ended_unix"] - 0.2 <= s <= w["ended_unix"] + 1.5 for s in stops) else "."
                  for w in legs)
    trailing = len(sig) - len(sig.rstrip("."))
    lock = trailing >= 2
    # THE ANCHOR is the run's first silent leg (the leg whose stop never arrived), not
    # the first S press: two of the six locked runs lock on the fourth leg (Q).
    idx = sig.find(".") if lock else legs.index(s_legs[0])
    if idx <= 0:
        idx = legs.index(s_legs[0])
    S1 = legs[idx]["started_unix"]
    S1_end = legs[idx]["ended_unix"]
    W1 = legs[idx - 1]["started_unix"]
    leg_name = f"{idx + 1}{legs[idx]['key']}"

    # --- 1. the gate-2 re-pin during the preceding hold, both guard arms --------------
    evs = guardretro.events(rows)
    sv, sdue, _ = guardretro.replay(evs, pm, 0.0)
    fv, fdue, _ = guardretro.replay(evs, pm, tol)
    logged_fires = [r["wall_unix"] for r in rows
                    if r.get("kind") == "agtrack_repin_fire" and r.get("why") == "gate2-offmesh"]
    pre_fires = [t for t in logged_fires if W1 - 1.0 <= t <= S1]
    fire = pre_fires[-1] if pre_fires else None
    # positive control: the stock arm's gate2-offmesh VETO verdict at the grant that
    # preceded the fire (the fire follows the due window by up to the 2 Hz sample)
    stock_vetoes = [t for t, c, w in sv if c == "veto" and w == "gate2-offmesh"]
    fix_vetoes = [t for t, c, w in fv if c == "veto" and w == "gate2-offmesh"]
    stock_reproduces = fire is not None and any(fire - 2.5 <= t <= fire + 0.3 for t in stock_vetoes)
    fix_removes = fire is not None and not any(fire - 2.5 <= t <= fire + 0.3 for t in fix_vetoes)

    # --- 2. the halt on the tape -------------------------------------------------------
    tape = find_tape(vault, harness_id)
    t0, samples = tape_samples(tape) if tape else (None, [])
    v_before = v_after = v_at_S = None
    parked_frac = None
    halt_pt = None
    if fire is not None and samples:
        b = at(samples, fire - 0.1)
        a = window(samples, fire, fire + 0.3)
        v_before = None if b is None else b["v"]
        v_after = None if not a else min(s["v"] for s in a)
        hold = window(samples, fire + 0.3, S1)
        parked_frac = None if not hold else sum(1 for s in hold if s["v"] < PARKED) / len(hold)
        hp = at(samples, fire + 0.3)
        halt_pt = None if hp is None else hp["body"]
    sS = at(samples, S1 - 0.1) if samples else None
    v_at_S = None if sS is None else sS["v"]
    body_at_S = None if sS is None else sS["body"]

    # --- 3. the lead granted at the press (any reach; full-length is >= LEAD_MIN) ------
    lead = None
    for r in rows:
        if r.get("kind") != "grant_verdict" or not r.get("fired") or r.get("lead_src") != "kbd":
            continue
        t = r["wall_unix"]
        if t < S1 - 0.5 or t > S1_end + 0.5:
            continue
        prior = [p for p in reports if p["wall_unix"] <= t]
        if not prior:
            continue
        px, py = prior[-1]["reported"]
        reach = math.hypot(r["dest"][0] - px, r["dest"][1] - py)
        lead = {"t": t, "dest": tuple(r["dest"]), "reach": reach, "origin": (px, py),
                "why": r.get("lead_clip_why"), "full": reach >= LEAD_MIN}
        break
    body_at_lead = None
    d_body_halt = None
    if lead is not None and samples:
        sl = at(samples, lead["t"])
        body_at_lead = None if sl is None else sl["body"]
        d_body_halt = dist(body_at_lead, halt_pt)

    # --- 4. the arrival: the first >= 300 u drawn-body step after the grant, anywhere
    #        in the leg (the bake's ETA depends on which speed the copy carried) ---------
    eta = jump = jump_rel = sep_at_eta = fence_shut = fence_rel = None
    if lead is not None:
        speed = S_SPEED if legs[idx]["key"] == "S" else W_SPEED
        eta = lead["t"] + lead["reach"] / speed
        if samples:
            se = at(samples, eta - 0.05)
            sep_at_eta = None if se is None else dist(se["body"], lead["dest"])
            win = window(samples, lead["t"], S1_end + 1.5)
            jump = 0.0
            for i in range(1, len(win)):
                j = dist(win[i]["body"], win[i - 1]["body"])
                if j is not None and win[i]["w"] - win[i - 1]["w"] <= 0.25 and j >= 300:
                    jump, jump_rel = j, win[i]["w"] - S1
                    break
            has_fence = any(s["fence"] is not None for s in win)
            shut = [s for s in win if s["fence"] == "shut"]
            fence_shut = None if not has_fence else bool(shut)   # the 09-03 tapes predate the fence column (1z-an)
            fence_rel = None if not shut else shut[0]["w"] - S1

    # --- 5. the control contrast: motion after S, and the follower -------------------
    moved_after_S = fol_d = fol_cos = None
    if samples:
        after = window(samples, S1 + 0.2, S1 + 1.5)
        moved_after_S = None if not after else max(s["v"] for s in after) > MOVING
        s2 = at(samples, S1 + 0.1)
        if s2 is not None and s2["fol"] is not None and s2["body"][0] is not None:
            fol_d = dist(s2["fol"], s2["body"])
            # the backpedal direction: opposite of the last W velocity before the press
            wv = [s for s in window(samples, W1, S1) if s["v"] > MOVING]
            if wv and fol_d:
                vx, vy = wv[-1]["vel"]
                n = math.hypot(vx, vy) or 1.0
                ux, uy = -vx / n, -vy / n
                rx, ry = s2["fol"][0] - s2["body"][0], s2["fol"][1] - s2["body"][1]
                fol_cos = (ux * rx + uy * ry) / fol_d

    return {
        "id": harness_id, "lead_on": bool(flags.get("KBD_SYNC_LEAD_ON")), "tape": bool(tape),
        "leg": leg_name, "jump_rel": jump_rel, "fence_rel": fence_rel,
        "S1": S1, "fire": fire, "fire_rel": None if fire is None else fire - S1,
        "stock_reproduces": stock_reproduces, "fix_removes": fix_removes,
        "v_before": v_before, "v_after": v_after, "parked_frac": parked_frac, "v_at_S": v_at_S,
        "halt_pt": halt_pt, "body_at_S": body_at_S,
        "lead": lead, "lead_rel": None if lead is None else lead["t"] - S1,
        "d_body_halt": d_body_halt,
        "eta_rel": None if eta is None else eta - S1, "sep_at_eta": sep_at_eta, "jump": jump,
        "fence_shut": fence_shut,
        "moved_after_S": moved_after_S, "fol_d": fol_d, "fol_cos": fol_cos,
        "sig": sig, "lock": lock,
    }


def f(v, w=6, p=1):
    return "   -  ".rjust(w) if v is None else (f"{v:{w}.{p}f}" if isinstance(v, float) else str(v).rjust(w))


def show(r):
    if "skip" in r:
        print(f"{r['id']}  SKIP: {r['skip']}")
        return
    lead = r["lead"]
    lead_s = "      -          " if lead is None else "%+5.2fs %4.0fu %-7s" % (r["lead_rel"], lead["reach"], (lead["why"] or "?")[:7])
    fix_s = "REMOVED" if r["fix_removes"] else ("kept" if r["fire"] else "  -  ")
    fence_s = ("SHUT %+5.2f" % r["fence_rel"]) if r["fence_shut"] else ("open      " if r["fence_shut"] is False else " -        ")
    jump_s = ("%4.0f %+5.2f" % (r["jump"], r["jump_rel"])) if r["jump"] else ("  none    " if r["jump"] is not None else "   -      ")
    after_s = "MOVED" if r["moved_after_S"] else ("still" if r["moved_after_S"] is False else "  -  ")
    parked = None if r["parked_frac"] is None else 100 * r["parked_frac"]
    print(f"{r['id']} {r['leg']} lead={'ON ' if r['lead_on'] else 'off'} tape={'y' if r['tape'] else 'n'} sig={r['sig']:8s} {'LOCK' if r['lock'] else 'ok  '}"
          f" | g2 {f(r['fire_rel'])}s stock:{'rep' if r['stock_reproduces'] else '---'} fix:{fix_s}"
          f" | v {f(r['v_before'],4,0)}->{f(r['v_after'],3,0)} parked {f(parked,4,0)}% v@P {f(r['v_at_S'],4,0)}"
          f" | lead {lead_s} halt-d {f(r['d_body_halt'],6,1)}"
          f" | sep@eta {f(r['sep_at_eta'],4,0)} jump {jump_s} fence {fence_s}"
          f" | after {after_s} fol {f(r['fol_d'],4,0)}u cos {f(r['fol_cos'],5,2)}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs", nargs="*", help="harness ids (default: the six locked runs of sec.1z-ap.3)")
    ap.add_argument("--no-control", action="store_true", help="skip the healthy lead-ON runs")
    ap.add_argument("--tol", type=float, default=None)
    a = ap.parse_args()
    from vaultpath import require_dir
    from pathmap import PathingMap
    import agtrack_mirror as am
    vault = require_dir()
    tol = am.GATE2_SEAM_TOL if a.tol is None else a.tol
    pm = PathingMap.load(guardretro.MAP146)
    runs = a.runs or LOCKED
    print(f"guard fix arm tol = {tol} u. Anchor = the run's first silent leg (its press = P). Columns: g2 = gate2-offmesh 0x002C rel. P, with the stock/fix guard replay; "
          f"v = drawn-body u/s before -> after that 0x002C, parked = share of the hold parked after it, v@P = at the press; lead = the kbd grant at the press (reach, clip why), "
          f"halt-d = body distance from the halt point when granted; sep@eta = body to lead dest at the bake ETA; jump = first >= 300 u drawn-body step after the grant (rel. P); "
          f"fence = first shut after the grant (09-03 tapes have no column); after = body moved > {MOVING:.0f} u/s within 1.5 s of P; fol = follower distance / cosine into the backpedal at P+0.1")
    print()
    print("LOCKED RUNS (sec.1z-ap.3)")
    locked = [analyse(vault, pm, r, tol) for r in runs]
    for r in locked:
        show(r)
    ctrl = []
    if not a.no_control and not a.runs:
        print()
        print("CONTROL: every other lead-ON harness run on 09-03/04 with an S leg and a tape")
        for rp in sorted(glob.glob(os.path.join(vault, "captures", "harness", "2026090[34]T*", "report.json"))):
            rid = os.path.basename(os.path.dirname(rp))
            if rid in runs:
                continue
            try:
                r = analyse(vault, pm, rid, tol)
            except Exception as e:  # a run whose capture the loader cannot read is printed, not hidden
                print(f"{rid}  SKIP: {type(e).__name__}: {e}")
                continue
            if "skip" in r or not r["lead_on"] or not r["tape"]:
                continue
            ctrl.append(r)
            show(r)

    # --- the tally against the registration ------------------------------------------
    L = [r for r in locked if "skip" not in r]
    print()
    print("TALLY vs the registration (FINDINGS sec.1z-bi); the anchor is each run's first silent leg")
    p1 = [r for r in L if r["fire"] is not None]
    print(f"  P1 gate-2 fire in the hold before the lock leg's press: {len(p1)} of {len(L)}; stock arm reproduces {sum(1 for r in p1 if r['stock_reproduces'])}, fix arm removes {sum(1 for r in p1 if r['fix_removes'])}")
    p2 = [r for r in p1 if r["v_before"] is not None and r["v_before"] > 150 and r["v_after"] is not None and r["v_after"] < PARKED]
    p2s = [r for r in p1 if r["v_at_S"] is not None and r["v_at_S"] < MOVING]
    print(f"  P2 halt (v > 150 before, < {PARKED:.0f} within 0.3 s): {len(p2)} of {len(p1)}; still parked at the press: {len(p2s)} of {len(p1)}")
    p3 = [r for r in p1 if r["lead"] is not None and r["lead"]["full"]]
    p3n = [r for r in p3 if r["d_body_halt"] is not None and r["d_body_halt"] <= 5.0]
    print(f"  P3 full-length lead granted at the press onto the halted body (<= 5 u): {len(p3n)} of {len(p3)} with a full-length lead")
    p4 = [r for r in p3 if (r["jump"] or 0) >= 300]
    print(f"  P4 a >= 300 u drawn-body jump after the lead within the leg: {len(p4)} of {len(p3)}; fence shut after it: {sum(1 for r in p3 if r['fence_shut'])}")
    lm = [r for r in L if r["moved_after_S"] is not None]
    print(f"  C1 locked runs where the body moved after the press: {sum(1 for r in lm if r['moved_after_S'])} of {len(lm)}")
    if ctrl:
        cf = [r for r in ctrl if r["fire"] is not None]
        cn = [r for r in ctrl if r["fire"] is None]
        print(f"  C1 control: {len(ctrl)} healthy lead-ON runs; with a gate-2 fire before S1: {len(cf)} "
              f"(body moved after S: {sum(1 for r in cf if r['moved_after_S'])}, locked: {sum(1 for r in cf if r['lock'])}); "
              f"without: {len(cn)} (moved after S: {sum(1 for r in cn if r['moved_after_S'])}, locked: {sum(1 for r in cn if r['lock'])})")
        def med(xs):
            xs = sorted(x for x in xs if x is not None)
            return None if not xs else xs[len(xs) // 2]
        print(f"  follower distance at S+0.1: locked p50 {f(med([r['fol_d'] for r in L]),5,0)} u, healthy-with-fire p50 {f(med([r['fol_d'] for r in cf]),5,0)} u, healthy-no-fire p50 {f(med([r['fol_d'] for r in cn]),5,0)} u")
        print(f"  cosine into the backpedal at S+0.1: locked p50 {f(med([r['fol_cos'] for r in L]),5,2)}, healthy-with-fire p50 {f(med([r['fol_cos'] for r in cf]),5,2)}, healthy-no-fire p50 {f(med([r['fol_cos'] for r in cn]),5,2)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
