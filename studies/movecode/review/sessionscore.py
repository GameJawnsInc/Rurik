#!/usr/bin/env python3
"""ONE SCORECARD PER SESSION: the movement regression suite, run on whatever the owner played.

    python studies/movecode/review/sessionscore.py                       # the newest gamesrv capture
    python studies/movecode/review/sessionscore.py --cap C [--tape T]    # one capture (tape found by wall overlap)
    python studies/movecode/review/sessionscore.py --since 20260906      # every capture from that stamp on
    python studies/movecode/review/sessionscore.py --check               # exit 1 on any RED (for a morning check)

WHY THIS EXISTS. Every movement finding since 1z-t has been scored by a per-arc script
(slidescore, npcdrift, copysep, meshcensus, w0score) on a run registered for one question.
The owner wants gameplay, and gameplay sessions are exactly the hand-driven corpus the arc
keeps asking for -- but nothing read them unless somebody wrote a runsheet. This reads a
capture the way the arc's scorers would, joined to its agenttap tape when one overlaps,
and prints every quantity the arc has ever convicted a defect on, each against the band
its confirming run measured. A RED is "look", never a verdict; an OK is "the shipped
shape held on this session".

WHAT IT MEASURES, and where each band comes from (all OBSERVED on the named run):

  EXPOSURE  accepted reports, keyboard legs, fired leads, tape samples with the body
            moving. A session under the floor prints NOT ENOUGH and scores nothing --
            a scorecard on ten reports is the same defect as a test with no floor.

  PLAYER    0x002C re-pins sent (RUN-FEEL2: 1, a pre-empted budget-red snap; RUN-1zBP's
            known-bad arm: 3 against 0); the wire-only LOCK signature (1z-am.3, restated
            for a hand-driven session as a keyboard leg armed and never cleared for
            LOCK_S while nothing reports); zero leads (1z-ce: the climb's 15 of 15
            before the slide, 0 after); the position model's drift p90 (FEEL2 80.6 u,
            pre-1z-cf); reports the mesh refuses (F12's edge class is <= 0.5 u).

  HOSTILE   corridor legs on the wire (Q9), halts in reach, parks off our mesh (Q9:
            the model's parks are on-mesh by construction; the client's are the tape's).

  TAPE      world-0 vs the drawn body while moving (1z-t/1z-ce: scripted 14-20 u p50,
            hand-driven FEEL2 97 u); the drawn bodies off our mesh (meshcensus: player
            <= 1.0 u worst; hostile 0.15 u under Q9 against 60.3 u before it); the
            hostile's sync copy vs its drawn body (copysep pins p90 13 / max 58).

Read-only. Stdlib only. Needs the vault. Pathmap by the capture's own map id through
content/maps.toml, so a session on another map scores on that map's mesh.
"""
import bisect
import glob
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/mapdata", "studies/renderobj/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402

# ---- bands: (ok_max, red_min) per metric; between them is WATCH ------------
REPIN_OK, REPIN_RED = 1, 4                # 0x002C sent to the player
DRIFT_P90_OK, DRIFT_P90_RED = 100.0, 200.0
ZERO_LEAD_FRAC_OK, ZERO_LEAD_FRAC_RED = 0.10, 0.34   # of fired keyboard leads
OFF_MESH_REPORT_OK = 0.5                  # u: F12's edge class
W0_MOVING_P50_OK, W0_MOVING_P50_RED = 120.0, 200.0
PLAYER_TAPE_OFF_OK, PLAYER_TAPE_OFF_RED = 1.0, 3.0
HOSTILE_TAPE_OFF_OK, HOSTILE_TAPE_OFF_RED = 2.0, 5.0
COPYSEP_P90_OK, COPYSEP_MAX_RED = 20.0, 80.0
LOCK_S = 12.0                             # a keyboard leg armed this long with no report
FLOOR_REPORTS = 20                        # a 60 s scripted run carries 23
SNAP_JUMP = 100.0                         # u: a drawn-body jump at a fence shut is a client snap
FLOOR_TAPE_MOVING = 60
FAR = 2.0
FOLLOW_STOP = 80.0                        # authsrv.follow_stop_radius(): r + r + 56
ENEMY_REACH = 92.0                        # authsrv.enemy_reach(): the disc + one radius
FOLLOW_RE = None


def _v(x, ok, red, lower_is_better=True):
    if x is None:
        return "  -  "
    if lower_is_better:
        return "OK   " if x <= ok else ("RED  " if x >= red else "WATCH")
    return "OK   " if x >= ok else ("RED  " if x <= red else "WATCH")


def q(vals, f):
    v = sorted(vals)
    return v[int(f * (len(v) - 1))] if v else None


def load_cap(path):
    rows = W.load_gamesrv(path)
    return rows


def mesh_for(rows):
    """The capture's own map, through content/maps.toml -> file id -> the pathmap."""
    import content
    from meshcensus import Mesh
    mid = None
    for r in rows:
        if r.get("kind") == "version":
            mid = r.get("map_id")
            break
    if mid is None:
        return None, None
    try:
        world = content.load()
        fid = world.map_static_config()[int(mid)][0]
        return Mesh(fid), mid
    except Exception as e:                        # noqa: BLE001
        print("  [mesh] map %s: %s" % (mid, e))
        return None, mid


def find_tape(rows):
    """The agenttap tape whose wall span overlaps this capture, newest wins."""
    wu = [r["wall_unix"] for r in rows if isinstance(r.get("wall_unix"), (int, float))]
    if not wu:
        return None
    lo, hi = min(wu), max(wu)
    rr = vaultpath.vault_root()
    best = None
    for p in sorted(glob.glob(os.path.join(rr, "research", "*", "*-agenttap.jsonl"))):
        try:
            head, srows = W.load(p)
        except Exception:                          # noqa: BLE001
            continue
        if not srows:
            continue
        t0, t1 = head["t0"], head["t0"] + srows[-1]["t"]
        if t1 < lo or t0 > hi:
            continue
        best = p
    return best


def score_capture(rows, mesh):
    out = {}
    reps = [r for r in rows if r.get("kind") == "position_report" and r.get("accepted")]
    out["reports"] = len(reps)
    out["span_s"] = (rows[-1].get("t") or 0.0) if rows else 0.0
    gv = [r for r in rows if r.get("kind") == "grant_verdict"]
    fired = [r for r in gv if r.get("fired")]
    out["fired"] = len(fired)
    # zero lead: a fired keyboard lead whose destination is the report it came from.
    rt = [r["t"] for r in reps]
    zero = 0
    why = {}
    for g in fired:
        why[g.get("lead_clip_why")] = why.get(g.get("lead_clip_why"), 0) + 1
        if g.get("lead_clip_why") == "fence-shut":
            continue                    # policy: no lead into the window (1z-aa), not a clip
        i = bisect.bisect_right(rt, g["t"]) - 1
        if i >= 0 and g.get("dest"):
            p = reps[i]["reported"]
            if math.hypot(g["dest"][0] - p[0], g["dest"][1] - p[1]) < 4.0:
                zero += 1
    out["zero_leads"] = zero
    out["zero_frac"] = (zero / len(fired)) if fired else None
    out["clip_why"] = why
    out["repins"] = sum(1 for r in rows if r.get("kind") == "sent" and r.get("opcode") == 0x2C)
    out["repin_why"] = [r.get("why") for r in rows if r.get("kind") == "agtrack_repin_fire"]
    drifts = [r["drift"] for r in reps if isinstance(r.get("drift"), (int, float))]
    out["drift_p50"], out["drift_p90"] = q(drifts, 0.5), q(drifts, 0.9)
    # the lock signature: an armed keyboard leg with no clear and no report for LOCK_S
    legs = [r for r in rows if r.get("kind") == "kbd_leg"]
    out["legs"] = sum(1 for r in legs if r.get("act") == "arm")
    end = out["span_s"]
    locks = []
    armed = None
    for r in legs:
        if r.get("act") == "arm":
            armed = r["t"]
        elif r.get("act") == "clear" and armed is not None:
            armed = None
    if armed is not None and end - armed >= LOCK_S:
        i = bisect.bisect_right(rt, armed)
        if i >= len(rt) or rt[i] - armed >= LOCK_S:
            locks.append(round(armed, 1))
    # and any armed stretch mid-session with no report for LOCK_S
    armed = None
    for r in legs:
        if r.get("act") == "arm":
            armed = r["t"]
        elif r.get("act") == "clear" and armed is not None:
            if r["t"] - armed >= LOCK_S:
                i = bisect.bisect_right(rt, armed)
                if i >= len(rt) or rt[i] - armed >= LOCK_S:
                    locks.append(round(armed, 1))
            armed = None
    out["locks"] = sorted(set(locks))
    # reports our mesh refuses, beyond the edge class
    off = []
    if mesh is not None:
        for r in reps:
            p = r.get("reported")
            if p:
                d = mesh.off(p[0], p[1])
                if d > OFF_MESH_REPORT_OK:
                    off.append(round(d, 1))
    out["reports_off_mesh"] = off
    out["_reps"] = reps
    # the hostile, from the wire
    sent = [r for r in rows if r.get("kind") == "sent"]
    out["follow_orders"] = sum(1 for r in sent if str(r.get("label", "")).startswith("FOLLOW"))
    out["corridor_legs"] = sum(1 for r in sent if " leg: agent " in str(r.get("label", "")))
    halts = []
    for r in sent:
        lab = str(r.get("label", ""))
        if lab.startswith("agent ") and " halts at (" in lab:
            try:
                xy = lab.split("halts at (")[1].split(")")[0].split(",")
                halts.append((r["t"], float(xy[0]), float(xy[1])))
            except (IndexError, ValueError):
                continue
    inreach = 0
    parks_off = []
    for t, x, y in halts:
        i = bisect.bisect_right(rt, t) - 1
        if i >= 0:
            p = reps[i]["reported"]
            if math.hypot(x - p[0], y - p[1]) <= ENEMY_REACH + 20.0:
                inreach += 1
        if mesh is not None:
            d = mesh.off(x, y)
            if d > FAR:
                parks_off.append(round(d, 1))
    out["halts"] = len(halts)
    out["halts_in_reach"] = inreach
    out["parks_off_mesh"] = parks_off
    out["plane_corrections"] = sum(1 for r in sent if str(r.get("label", "")).startswith("PLANE CORRECT"))
    return out


def score_tape(tape, mesh, cap_path, cap_reps=None):
    out = {"tape": os.path.relpath(tape, ROOT)}
    head, rows = W.load(tape)
    p1 = W.series(head, rows, 1)
    moving = [r for r in p1 if r["vbody"] > 1.0]
    out["tape_moving"] = len(moving)
    out["tape_samples"] = len(p1)
    sep = [math.dist(r["w0"], r["body"]) for r in moving]
    out["w0_moving_p50"], out["w0_moving_p90"] = q(sep, 0.5), q(sep, 0.9)
    try:
        per, ens = W.enslavement(head, rows, W.grants(W.load_gamesrv(cap_path)))
        out["enslaved"] = ens.get("verdict") if ens else None
        out["enslaved_frac"] = ens.get("frac") if ens else None
    except Exception as e:                        # noqa: BLE001
        out["enslaved"] = "not measured (%s)" % e
        out["enslaved_frac"] = None
    # THE CLIENT'S OWN SNAP: the fence shuts (a 0x002C, ours or the client's own
    # separation gate) and the drawn body JUMPS. Ours land on the body by design
    # (harm 0 u, 1z-ak); a jump is the client's gate teleporting the body onto a
    # world-0 that fell behind -- the yank the owner feels (FEEL2 63.8 s: 166 u
    # into the hole above the stairs, then 452 u out of it).
    snaps = []
    prev = None
    for sm in rows:
        a = (sm.get("agents") or {}).get("1")
        if not a or not a.get("async") or "x" not in a["async"]:
            continue
        f = (a.get("fence") or {}).get("fence_state")
        pt = (a["async"]["x"], a["async"]["y"])
        if prev is not None:
            j = math.dist(prev[1], pt)
            if j > SNAP_JUMP and (f == "shut" or prev[0] == "shut"):
                snaps.append((round(sm["t"], 1), round(j)))
        prev = (f, pt)
    out["snaps"] = snaps
    if mesh is not None:
        # The drawn body off our mesh, split by whether the client's OWN report at
        # that instant was on it: off with the report on-mesh is a body put somewhere
        # the client never reported standing (a snap, a grant); off with the report
        # off too is ground our mesh lacks (F11's terrace) and only a WATCH.
        reps = cap_reps or []
        rw = [r["wall_unix"] for r in reps]
        for agent, key in (("1", "player_off"), ("10", "hostile_off")):
            n = far = 0
            worst = worst_uncovered = 0.0
            for sm in rows:
                a = (sm.get("agents") or {}).get(agent)
                if not a or not a.get("async") or "x" not in a["async"]:
                    continue
                n += 1
                d = mesh.off(a["async"]["x"], a["async"]["y"])
                if d <= FAR:
                    continue
                w = head["t0"] + sm["t"]
                i = bisect.bisect_right(rw, w) - 1
                rep_off = mesh.off(*reps[i]["reported"]) if i >= 0 else 0.0
                if rep_off > OFF_MESH_REPORT_OK:
                    worst_uncovered = max(worst_uncovered, d)
                else:
                    far += 1
                    worst = max(worst, d)
            out[key] = (n, worst, far, worst_uncovered)
    # EVERY hostile on the tape (agenttap --agents 1,10,11,...): the copy
    # separation pooled, and the off-mesh census per hostile above reads 10
    # only -- extended here to the worst over all of them.
    hostiles = sorted({a for sm in rows for a in (sm.get("agents") or {}) if a != "1"}, key=int)
    out["hostiles"] = hostiles
    d10 = []
    for h in hostiles:
        for r in W.series(head, rows, int(h)):
            d10.append(math.dist(r["w0"], r["body"]))
    out["copysep_p90"], out["copysep_max"] = q(d10, 0.9), q(d10, 1.0)
    if mesh is not None and len(hostiles) > 1 and "hostile_off" in out:
        reps = cap_reps or []
        rw = [r["wall_unix"] for r in reps]
        n = far = 0
        worst = worst_unc = 0.0
        for h in hostiles:
            for sm in rows:
                a = (sm.get("agents") or {}).get(h)
                if not a or not a.get("async") or "x" not in a["async"]:
                    continue
                n += 1
                d = mesh.off(a["async"]["x"], a["async"]["y"])
                if d <= FAR:
                    continue
                i = bisect.bisect_right(rw, head["t0"] + sm["t"]) - 1
                rep_off = mesh.off(*reps[i]["reported"]) if i >= 0 else 0.0
                if rep_off > OFF_MESH_REPORT_OK:
                    worst_unc = max(worst_unc, d)
                else:
                    far += 1
                    worst = max(worst, d)
        out["hostile_off"] = (n, worst, far, worst_unc)
    return out


def report(cap_path, tape, mesh, mid, c, t):
    print("=" * 96)
    print("SESSION  %s   map %s   %.0f s" % (os.path.basename(cap_path), mid, c["span_s"]))
    print("         tape %s" % (t["tape"] if t else "NONE overlapping -- tape metrics not measured"))
    red = 0
    watch = 0

    def line(name, value, verdict, note=""):
        nonlocal red, watch
        if verdict.startswith("RED"):
            red += 1
        elif verdict.startswith("WATCH"):
            watch += 1
        print("  %s %-44s %-28s %s" % (verdict, name, value, note))

    print("EXPOSURE")
    enough = c["reports"] >= FLOOR_REPORTS
    line("accepted reports", "%d" % c["reports"], "OK   " if enough else "RED  ",
         "" if enough else "under the floor of %d: NOT ENOUGH SESSION, nothing below is a verdict" % FLOOR_REPORTS)
    line("keyboard legs armed / leads fired", "%d / %d" % (c["legs"], c["fired"]), "  -  ")
    if t:
        tm = t["tape_moving"] >= FLOOR_TAPE_MOVING
        line("tape samples, body moving", "%d of %d" % (t["tape_moving"], t["tape_samples"]),
             "OK   " if tm else "WATCH", "" if tm else "under %d: tape bands are not verdicts" % FLOOR_TAPE_MOVING)
    if not enough:
        return red, watch
    print("PLAYER")
    line("0x002C re-pins sent", "%d %s" % (c["repins"], c["repin_why"] or ""),
         _v(c["repins"], REPIN_OK, REPIN_RED), "FEEL2 1 (pre-empted); known-bad arm 3")
    line("lock signature (armed leg, no report, >= %.0f s)" % LOCK_S,
         "none" if not c["locks"] else "at t=%s" % c["locks"],
         "OK   " if not c["locks"] else "RED  ", "1z-am.3 restated for a hand-driven session")
    zf = c["zero_frac"]
    line("zero leads / fired", "%d / %d" % (c["zero_leads"], c["fired"]),
         _v(zf, ZERO_LEAD_FRAC_OK, ZERO_LEAD_FRAC_RED) if c["fired"] >= 5 else "  -  ",
         "clip: %s" % {k: v for k, v in sorted(c["clip_why"].items(), key=lambda kv: -kv[1])})
    line("position model drift p50 / p90", "%s / %s u" % (
        None if c["drift_p50"] is None else round(c["drift_p50"], 1),
        None if c["drift_p90"] is None else round(c["drift_p90"], 1)),
         _v(c["drift_p90"], DRIFT_P90_OK, DRIFT_P90_RED), "FEEL2 19 / 81 (before 1z-cf)")
    off = c["reports_off_mesh"]
    line("reports off our mesh beyond %.1f u" % OFF_MESH_REPORT_OK,
         "%d%s" % (len(off), (" worst %.1f u" % max(off)) if off else ""),
         "OK   " if not off else ("WATCH" if max(off) < 10 else "RED  "),
         "F12: the edge class is <= 0.5 u; beyond it is a grant, a jump or a hole")
    print("HOSTILE")
    line("follow orders / corridor legs on the wire", "%d / %d" % (c["follow_orders"], c["corridor_legs"]), "  -  ",
         "Q9: legs appear only where geometry intervenes")
    line("halts, and halts within reach of the player", "%d / %d" % (c["halts"], c["halts_in_reach"]), "  -  ",
         "the rest park in the client's frame while the player walks (Q6)")
    po = c["parks_off_mesh"]
    line("halt points off our mesh beyond %.0f u" % FAR, "%d%s" % (len(po), (" worst %.1f u" % max(po)) if po else ""),
         "OK   " if not po else "RED  ", "the copy is the client's (Q1): off-mesh = walked through (Q9) or ordered off (1z-cf)")
    line("plane corrections sent", "%d" % c["plane_corrections"], "  -  ", "GROUNDZ-Q5/F11")
    if t:
        print("TAPE")
        tm = t["tape_moving"] >= FLOOR_TAPE_MOVING
        line("world-0 vs drawn body, moving, p50 / p90", "%s / %s u" % (
            None if t["w0_moving_p50"] is None else round(t["w0_moving_p50"], 1),
            None if t["w0_moving_p90"] is None else round(t["w0_moving_p90"], 1)),
             _v(t["w0_moving_p50"], W0_MOVING_P50_OK, W0_MOVING_P50_RED) if tm else "  -  ",
             "scripted 14-20, hand-driven FEEL2 97")
        line("enslavement (body following a server grant)", "%s (%s)" % (
            t.get("enslaved"), None if t.get("enslaved_frac") is None else "%.1f%%" % (100 * t["enslaved_frac"])),
             "  -  ", "a wall slide reads ~32% here by design (w0score note)")
        sn = t.get("snaps") or []
        line("client snaps (fence shut + body jump > %.0f u)" % SNAP_JUMP,
             "%d %s" % (len(sn), sn[:4] if sn else ""), "OK   " if not sn else "RED  ",
             "FEEL2 2 (166 u into the hole, 452 out); 1zBW 6+; scripted runs 0")
        if "player_off" in t:
            n, worst, far, unc = t["player_off"]
            line("player drawn body off our mesh, worst / > 2 u", "%.2f u / %d of %d%s" % (
                worst, far, n, ("  (+ %.1f u on ground our mesh lacks)" % unc) if unc > FAR else ""),
                 _v(worst, PLAYER_TAPE_OFF_OK, PLAYER_TAPE_OFF_RED), "with the client's report ON mesh; FEEL2 60 u = the snap")
        if "hostile_off" in t:
            n, worst, far, unc = t["hostile_off"]
            line("hostile drawn body off our mesh, worst / > 2 u", "%.2f u / %d of %d%s" % (
                worst, far, n, ("  (+ %.1f u beside a player on uncovered ground)" % unc) if unc > FAR else ""),
                 _v(worst, HOSTILE_TAPE_OFF_OK, HOSTILE_TAPE_OFF_RED), "Q9 0.15; before it 12.8-93.8")
        if len(t.get("hostiles") or []) != 1:
            line("hostiles on the tape", "%s" % (t.get("hostiles") or []), "  -  ", "the hostile rows pool every one of them")
        line("hostile sync copy vs drawn body, p90 / max", "%s / %s u" % (
            None if t["copysep_p90"] is None else round(t["copysep_p90"], 1),
            None if t["copysep_max"] is None else round(t["copysep_max"], 1)),
             "OK   " if (t["copysep_p90"] or 0) <= COPYSEP_P90_OK and (t["copysep_max"] or 0) < COPYSEP_MAX_RED
             else ("RED  " if (t["copysep_max"] or 0) >= COPYSEP_MAX_RED else "WATCH"),
             "copysep pins p90 13 / max 58")
    print("VERDICT  %s  (%d RED, %d WATCH)" % ("LOOK" if red else ("WATCH" if watch else "HELD"), red, watch))
    return red, watch


def captures(argv):
    root = vaultpath.require_dir("captures", "gamesrv", why="the session scorer reads our own captures")
    caps = sorted(glob.glob(os.path.join(root, "authsrv-*-c1.jsonl")))
    if "--cap" in argv:
        return [argv[argv.index("--cap") + 1]]
    if "--since" in argv:
        s = argv[argv.index("--since") + 1]
        return [c for c in caps if os.path.basename(c)[8:8 + len(s)] >= s]
    return caps[-1:]


def main(argv):
    total_red = 0
    for cap in captures(argv):
        rows = load_cap(cap)
        mesh, mid = mesh_for(rows)
        tape = argv[argv.index("--tape") + 1] if "--tape" in argv else find_tape(rows)
        c = score_capture(rows, mesh)
        t = score_tape(tape, mesh, cap, c.get("_reps")) if tape and os.path.exists(tape) else None
        red, _w = report(cap, tape, mesh, mid, c, t)
        total_red += red
    if "--check" in argv:
        return 1 if total_red else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
