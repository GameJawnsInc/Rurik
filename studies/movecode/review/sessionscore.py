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

  PLAYER    phantom legs (1z-cr: a keyboard leg armed from the client's heading that the
            body then did not travel -- the model walks it and the follow orders from the
            result, 1z-cp; NOT RECORDED on captures before 1z-cr, which is not zero);
            0x002B->destination pairs a 0x001E split (1z-cm: retail 0 of 2,404; session 5's
            crash was one, under a due arrival); 0x002C re-pins sent (RUN-FEEL2: 1, a pre-empted budget-red snap; RUN-1zBP's
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
for sub in ("toolkit", "toolkit/clientscan", "toolkit/mapdata", "toolkit/authsrv",
            "studies/renderobj/review"):
    sys.path.insert(0, os.path.join(ROOT, sub))

import vaultpath                                   # noqa: E402
import w0score as W                                # noqa: E402
import stalepair                                   # noqa: E402
import movesync                                    # noqa: E402

# ---- bands: (ok_max, red_min) per metric; between them is WATCH ------------
REPIN_OK, REPIN_RED = 1, 4                # 0x002C sent to the player
DRIFT_P90_OK, DRIFT_P90_RED = 100.0, 200.0
ZERO_LEAD_FRAC_OK, ZERO_LEAD_FRAC_RED = 0.10, 0.34   # of fired keyboard leads
OFF_MESH_REPORT_OK = 0.5                  # u: F12's edge class
W0_MOVING_P50_OK, W0_MOVING_P50_RED = 120.0, 200.0
PLAYER_TAPE_OFF_OK, PLAYER_TAPE_OFF_RED = 1.0, 3.0
HOSTILE_TAPE_OFF_OK, HOSTILE_TAPE_OFF_RED = 2.0, 5.0
COPYSEP_P90_OK, COPYSEP_MAX_RED = 20.0, 80.0
PLANE_LAG_OK, PLANE_LAG_RED = 1.0, 2.5      # s: retail's mover-plane update after a crossing order, p50 0.64 / p90 2.08
LOCK_S = 12.0                             # a keyboard leg armed this long with no report
FLOOR_REPORTS = 20                        # a 60 s scripted run carries 23
SNAP_JUMP = 100.0                         # u: a drawn-body jump at a fence shut is a client snap
GRANT_ARRIVAL_U = 4.0                     # u: a jump landing this close to a point we granted
GRANT_ARRIVAL_S = 1.0                     # s: ...within this long is that grant's arrival teleport
FLOOR_TAPE_MOVING = 60
FAR = 2.0
FOLLOW_STOP = 80.0                        # authsrv.follow_stop_radius(): r + r + 56
ENEMY_REACH = 92.0                        # authsrv.enemy_reach(): the disc + one radius
FOLLOW_RE = None
# THE WARP ROW (DESKWORK-D10 step 2 / MOVECODE-1z-do). A hard jump in the
# CLIENT's own self-report stream (movesync's repaired two-arm bar, reused),
# attributed to the nearest preceding movement SEND and flagged for a wall-slide
# re-grant in a window before it -- SUSPECT, never a cause.
WARP_ATTRIB_S = 3.0                       # s: the send-attribution window (DESKWORK-D10 step 2)
GATE1_UNITS = 299.332591                  # u: the client's OWN separation gate (movement HANDOFF §8);
#                                           a report jump under this may be that gate, or nothing
WARP_ON_GRANT_U = 4.0                     # u: a landing this close to a point we granted...
WARP_ON_GRANT_S = 1.0                     # s: ...this recently is arrival ON our grant, not a snap


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


def _warp_send_tag(label):
    """One tag for a 0x0029 send, from its label. Re-grant detection lives here."""
    lab = str(label or "")
    if "RE-GRANT" in lab:
        return ("re-grant", "wall-slide" in lab)
    if "KILLED on click" in lab:
        return ("click-kill", False)
    if "ROUTER" in lab:
        return ("router", False)
    if "STOP-ECHO" in lab:
        return ("stop-echo", False)
    if "KBD LEAD" in lab:
        return ("kbd-lead", False)
    return ("grant", False)


def warp_rows(cap_path, rows):
    """THE WARP ROW (DESKWORK-D10 step 2 / MOVECODE-1z-do). Hard jumps in the
    CLIENT's own self-report stream, and what each sits near.

    THE BAR IS REUSED, NEVER RE-IMPLEMENTED: `movesync.wire_only` splices the
    c2s 0x003D+0x0047 stream and runs the repaired TWO-ARM hard bar (implied
    speed > 400 u/s at dt >= 0.05 s; displacement >= 520 u below that floor).
    Retail scores ZERO on both arms (movesync header), and the quiet owner days
    09-09 / 09-12 score 0, so the band is 0 = OK and any hard row is a LOOK.

    ATTRIBUTION IS A SUSPECT, NEVER A CAUSE. Each hard row carries:
      * `nearest_send` -- the nearest preceding 0x0029 we sent within
        WARP_ATTRIB_S, with its tag and age. A temporal neighbour.
      * `regrant_before` -- whether a wall-slide arrival re-grant fired in that
        same window, and how long before, because 1z-di.3's predicted failure is
        exactly a wall-slide re-grant walking the copy past the corner. This is
        SEPARATE from `nearest_send`: an ordinary lead can be nearer in time than
        the re-grant that is the reason to look.
      * `on_grant` -- the landing sits within WARP_ON_GRANT_U of a point we
        granted in the last WARP_ON_GRANT_S. A jump onto our OWN outstanding
        grant is the client obeying us, NOT a separation snap (the trap the arc
        already paid for), so it is booked and printed, never silently counted.
      * `under_gate1` -- the magnitude is under the client's own 299.33 u
        separation gate, so a "snap" reading cannot even be that gate firing.
    """
    w = movesync.wire_only(cap_path)
    hard = w["hard"]
    den = w["den"]
    grants = movesync.load_grants(cap_path)        # (t, [x, y]) from the wire bytes
    gt = [g[0] for g in grants]
    sends = []                                     # (t, tag, is_wall_slide)
    for r in rows:
        if r.get("kind") == "sent" and r.get("opcode") == 0x29:
            tag, ws = _warp_send_tag(r.get("label"))
            sends.append((r["t"], tag, ws))
    sends.sort()
    st_ = [s[0] for s in sends]
    out_rows = []
    n_regrant = n_on_grant = n_under_gate1 = 0
    for h in hard:
        t, land = h["t"], h["p"]
        # nearest preceding send within the window
        i = bisect.bisect_right(st_, t) - 1
        nearest = None
        if i >= 0 and t - sends[i][0] <= WARP_ATTRIB_S:
            nearest = {"tag": sends[i][1], "age": round(t - sends[i][0], 2),
                       "wall_slide": sends[i][2]}
        # a wall-slide re-grant anywhere in the window before it
        regrant_age = None
        for s in reversed(sends):
            if s[0] > t or t - s[0] > WARP_ATTRIB_S:
                if t - s[0] > WARP_ATTRIB_S:
                    break
                continue
            if s[1] == "re-grant" and s[2]:
                regrant_age = round(t - s[0], 2)
                break
        # landing on our own outstanding grant?
        lo = bisect.bisect_left(gt, t - WARP_ON_GRANT_S)
        hi = bisect.bisect_right(gt, t + 0.05)
        on_grant = any(math.hypot(grants[k][1][0] - land[0],
                                  grants[k][1][1] - land[1]) <= WARP_ON_GRANT_U
                       for k in range(lo, hi))
        under = h["dist"] < GATE1_UNITS
        if regrant_age is not None:
            n_regrant += 1
        if on_grant:
            n_on_grant += 1
        if under:
            n_under_gate1 += 1
        out_rows.append({
            "t": round(t, 2), "dist": round(h["dist"], 1), "dt": round(h["dt"], 3),
            "speed": round(h["speed"]), "plane_flip": bool(h.get("plane_flip")),
            "nearest_send": nearest, "regrant_before": regrant_age,
            "on_grant": on_grant, "under_gate1": under})
    span = den["span"]
    active = den["active"]
    return {
        "n": len(hard),
        "intervals": den["intervals"],
        "refuse_all": w["refuse_all"],
        "mag_p50": (movesync.magnitude(hard) or (None, None))[0],
        "mag_max": (movesync.magnitude(hard) or (None, None))[1],
        "rate_span": (60.0 * len(hard) / span) if span > 0 else None,
        "rate_active": (60.0 * len(hard) / active) if active > 0 else None,
        "n_regrant": n_regrant, "n_on_grant": n_on_grant, "n_under_gate1": n_under_gate1,
        "rows": out_rows,
    }


def score_capture(rows, mesh, cap_path=None):
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
    # 1z-cm: a 0x001E between a 0x002B and its destination is the client's
    # AgAgent.cpp:1198 assert whenever an arrival is due at that tick; retail 0 of 2,404.
    out["stale_pairs"] = stalepair.census(rows)
    # MOVECODE-1z-cr: THE PHANTOM LEG, counted at its source. Each `kbd_dest` row is a
    # keyboard leg armed from the client's own heading; the 20 Hz integrator then walks
    # state["pos"] toward it at 14.4 u per tick until the next report lands, and the NPC
    # follow orders from the result (1z-cp). Joining each arming to the NEXT accepted
    # report gives the drift that leg actually produced -- OBSERVED, where 1z-cq could
    # only reconstruct it. A capture written before 1z-cr carries no such rows, and that
    # reads as NOT RECORDED rather than as zero.
    arms = [r for r in rows if r.get("kind") == "kbd_dest" and r.get("act") == "arm"]
    if not arms:
        out["phantom"] = None
    else:
        rt2 = [r["t"] for r in reps]
        legs = []
        for a in arms:
            i = bisect.bisect_right(rt2, a["t"])
            if i >= len(reps):
                continue
            nxt = reps[i]
            d = nxt.get("drift")
            frm = a.get("frm") or [0.0, 0.0]
            travelled = math.dist(frm, nxt["reported"])
            legs.append({"t": round(a["t"], 2), "leg": a.get("leg"),
                         "mt": a.get("mt"), "clipped": bool(a.get("clipped")),
                         "drift": d if isinstance(d, (int, float)) else None,
                         "travelled": round(travelled, 1)})
        # A leg the body did not travel: the report that closed it came back within one
        # integrator step (14.4 u) of where the leg STARTED, so the client went nowhere
        # while our model walked the leg.
        stuck = [l for l in legs if l["travelled"] <= 14.4]
        out["phantom"] = {
            "armed": len(legs),
            "stuck": len(stuck),
            "worst_drift": max([l["drift"] for l in stuck
                                if l["drift"] is not None], default=0.0),
            "worst_leg": max([l["leg"] for l in stuck
                              if l["leg"] is not None], default=0.0),
            "rows": sorted([l for l in stuck if l["drift"]],
                           key=lambda z: -(z["drift"] or 0))[:4],
        }
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
    # THE WARP ROW (DESKWORK-D10 step 2 / MOVECODE-1z-do): hard jumps in the
    # client's self-report stream, from movesync's two-arm bar, each attributed
    # to the nearest preceding send and flagged for a wall-slide re-grant before
    # it. SUSPECT, never a cause. `cap_path` is optional so a caller with only
    # rows still gets everything above.
    if cap_path is not None:
        try:
            out["warp"] = warp_rows(cap_path, rows)
        except Exception as e:                    # noqa: BLE001
            out["warp"] = {"error": str(e)}
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
    # world-0 that fell behind -- the yank the owner feels (FEEL2 63.8 s: 181 u
    # into the hole above the stairs).
    #
    # ON THE LIVE PATH, NEVER THE RAW COLUMN (MOVECODE-1z-ck). agenttap's x,y is
    # the copy's last WRITTEN point, sample-and-hold: under a shut fence the body
    # walks our leads as click-orders at 288 u/s and the column stands still for
    # a second, then catches up in one sample -- which this metric read as a
    # 150-450 u teleport. Session 3 of RUN-1zCG scored 3 snaps on the raw column
    # and has 1 on the live path; FEEL2's "452 u out of the hole" was the same
    # walk. w0score.live is the client's own position_at, clamp and all.
    #
    # AND NOT EVERY JUMP IS THE GATE (RUN-1zCG session 6). Every grant we send arms the
    # client's teleport branch, so at a grant's arrival tick the body is SET to the granted
    # point (movement/FINDINGS :1147). Spam-clicking lands a grant every ~0.1 s, and session
    # 6's single "snap" -- 155 u at 81.2 s -- put the body within 0.5 u of a `ROUTER one leg`
    # point sent 0.2 s earlier. That is the client obeying us, which is the opposite of the
    # thing this metric exists to count. A jump landing on a point we granted in the last
    # GRANT_ARRIVAL_S is booked separately and both counts are printed, so the exclusion can
    # never quietly swallow a real gate snap.
    snaps = []
    grant_arrivals = []
    prev = None
    try:
        G = W.grants(W.load_gamesrv(cap_path))
    except Exception:                                  # noqa: BLE001
        G = []
    gw = [g["w"] for g in G]
    for sm in rows:
        a = (sm.get("agents") or {}).get("1")
        if not a or not a.get("async") or "x" not in a["async"]:
            continue
        f = (a.get("fence") or {}).get("fence_state")
        pt = W.live(a["async"], sm.get("clock1"))
        if prev is not None:
            j = math.dist(prev[1], pt)
            if j > SNAP_JUMP and (f == "shut" or prev[0] == "shut"):
                w = head["t0"] + sm["t"]
                lo = bisect.bisect_left(gw, w - GRANT_ARRIVAL_S)
                hi = bisect.bisect_right(gw, w + 0.10)
                on_grant = any(math.dist(g["dest"], pt) <= GRANT_ARRIVAL_U
                               for g in G[lo:hi])
                (grant_arrivals if on_grant else snaps).append(
                    (round(sm["t"], 1), round(j)))
        prev = (f, pt)
    out["snaps"] = snaps
    out["grant_arrivals"] = grant_arrivals
    # THE MID-AIR SIGNATURE (MOVECODE-1z-cl, RUN-1zCG session 4's end): the drawn
    # body PARKED on a plane word our mesh does not offer at its point -- the
    # client draws it at that plane's cached height (F11) and its keyboard
    # mover cannot resolve its own start, so it hangs there until something
    # else moves it. Episodes of consecutive parked samples; the longest is
    # the number. Moving samples are excluded: a body crossing a seam carries
    # the old word for a sample or two by the client's own lag.
    if mesh is not None:
        eps = []
        cur = None
        for sm in rows:
            a = (sm.get("agents") or {}).get("1")
            if not a or not a.get("async") or "x" not in a["async"]:
                continue
            b = a["async"]
            v = math.hypot(b.get("vx", 0.0), b.get("vy", 0.0))
            pt = W.live(b, sm.get("clock1"))
            pls = mesh.pm.planes_at(pt[0], pt[1]) if hasattr(mesh, "pm") else set()
            bad = (v <= 1.0 and bool(pls) and b.get("plane") not in pls)
            if bad and cur is None:
                cur = sm["t"]
            elif not bad and cur is not None:
                eps.append((round(cur, 1), round(sm["t"] - cur, 2)))
                cur = None
        if cur is not None:
            eps.append((round(cur, 1), round(rows[-1]["t"] - cur, 2)))
        out["midair"] = eps
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
    # THE STAIRS-ENTRY PLANE LAG (RUN-1zCG: "the Hatcher terrain walks for a
    # second entering the stairs"): a hostile's drawn body standing on
    # trapezoids of ONE plane while its client plane word names another --
    # the interval from the crossing to the order that carries the new word.
    # Retail's own update after a crossing order: p50 0.64 s, p90 2.08 (954
    # NPC orders with field 3 != field 4 on the live corpus).
    lags = []
    if mesh is not None:
        for h in hostiles:
            cur = None
            for sm in rows:
                a = (sm.get("agents") or {}).get(h)
                if not a or not a.get("async") or "x" not in a["async"]:
                    continue
                pl = a["async"].get("plane")
                mp = mesh.pm.planes_at(a["async"]["x"], a["async"]["y"])
                wrong = bool(mp) and pl is not None and pl not in mp and len(mp) == 1
                if wrong:
                    if cur is None:
                        cur = [sm["t"], sm["t"]]
                    cur[1] = sm["t"]
                elif cur is not None:
                    if sm["t"] - cur[0] >= 0.15:
                        lags.append(round(sm["t"] - cur[0], 2))
                    cur = None
    out["plane_lags"] = lags
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
    sp = c["stale_pairs"]
    line("0x002B->destination pairs split by a 0x001E", "%d of %d" % (sp["split"], sp["pairs"]),
         "OK   " if not sp["split"] else "RED  ",
         "1z-cm: retail 0 of 2,404 (same packet); under a due arrival it is AgAgent.cpp:1198"
         + ("; at t=%s" % [s[1] for s in sp["splits"]] if sp["splits"] else ""))
    if sp["bare"]:
        line("bare 0x002B (no destination within 12 sends)", "%d" % sp["bare"], "WATCH",
             "the loading-screen assert class; at t=%s" % [b[1] for b in sp["bares"]])
    ph = c.get("phantom")
    if ph is None:
        line("phantom legs (armed, then not travelled)", "NOT RECORDED", "  -  ",
             "this capture predates MOVECODE-1z-cr's kbd_dest rows -- not zero, unmeasured")
    else:
        line("phantom legs (armed, then not travelled)",
             "%d of %d armed" % (ph["stuck"], ph["armed"]),
             "OK   " if ph["worst_drift"] <= 100.0 else "RED  ",
             "1z-cp: the model walks these and the follow orders from it; worst drift "
             "%.0f u, worst leg %.0f u%s" % (
                 ph["worst_drift"], ph["worst_leg"],
                 (" at t=%s" % [r["t"] for r in ph["rows"]]) if ph["rows"] else ""))
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
    wp = c.get("warp")
    if wp is not None and "error" not in wp:
        # retail scores 0 on both arms and the quiet days 09-09/09-12 score 0,
        # so any hard row is a LOOK. The attribution is printed so the LOOK can
        # be read, never so it can be believed.
        if wp["refuse_all"]:
            line("client-report warps (hard jumps, two-arm bar)",
                 "not rated (%d intervals < %d)" % (wp["intervals"], movesync.MIN_INTERVALS),
                 "  -  ", "too few report intervals to rate")
        else:
            mag = "" if wp["mag_max"] is None else " mag p50 %.0f / max %.0f u" % (wp["mag_p50"], wp["mag_max"])
            rate = "" if wp["rate_active"] is None else "  %.2f/active-min" % wp["rate_active"]
            line("client-report warps (hard jumps, two-arm bar)",
                 "%d%s" % (wp["n"], mag),
                 "OK   " if wp["n"] == 0 else "RED  ",
                 "retail 0, quiet 09-09/09-12 0; %d re-grant-adjacent, %d ON our grant, "
                 "%d under gate-1 (%.0f u)%s" % (
                     wp["n_regrant"], wp["n_on_grant"], wp["n_under_gate1"], GATE1_UNITS, rate))
            for r in wp["rows"]:
                ns = r["nearest_send"]
                tag = ("send %s@%.2fs%s" % (ns["tag"], ns["age"], " wall-slide" if ns["wall_slide"] else "")
                       if ns else "no send within %.0fs" % WARP_ATTRIB_S)
                extra = []
                if r["regrant_before"] is not None:
                    extra.append("wall-slide re-grant %.2fs before" % r["regrant_before"])
                if r["on_grant"]:
                    extra.append("ON our grant (client obeying, not a snap)")
                if r["under_gate1"]:
                    extra.append("under gate-1")
                if r["plane_flip"]:
                    extra.append("plane flip")
                line("  warp t=%.2f %.0f u / %.3f s (%.0f u/s)" % (
                    r["t"], r["dist"], r["dt"], r["speed"]),
                    "SUSPECT", "  -  ",
                    "nearest %s%s" % (tag, ("; " + ", ".join(extra)) if extra else ""))
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
        ga = t.get("grant_arrivals") or []
        line("grant arrivals (a jump landing ON a point WE granted)",
             "%d %s" % (len(ga), ga[:4] if ga else ""), "  -  ",
             "not the gate: every grant arms the teleport branch; s6 spam-clicking made 1")
        sn = t.get("snaps") or []
        line("client snaps (fence shut + body jump > %.0f u)" % SNAP_JUMP,
             "%d %s" % (len(sn), sn[:4] if sn else ""), "OK   " if not sn else "RED  ",
             "live path: FEEL2 1 (181 u into the hole); 1zBW 5; 1zCG s3 1 (255 u); scripted runs 0")
        ma = t.get("midair")
        if ma is not None:
            longest = max((d for _t0, d in ma), default=0.0)
            line("player parked on a plane word our mesh lacks at its point (mid-air)",
                 "%d episode(s), longest %.1f s %s" % (len(ma), longest, ma[:3] if ma else ""),
                 "OK   " if longest < 1.0 else "RED  ",
                 "1z-cl: session 4 ended 12 s in mid-air at the stairs' foot; F11's cached height")
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
        pl = t.get("plane_lags") or []
        line("hostile drawn on one plane, word naming another", "%d episodes%s" % (
            len(pl), (", longest %.2f s" % max(pl)) if pl else ""),
             _v(max(pl) if pl else None, PLANE_LAG_OK, PLANE_LAG_RED),
             "retail's own update after a crossing: p50 0.64 s, p90 2.08")
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
    # EVERY connection, not just `-c1` (DESKWORK-D10 step 2). A session re-dials on
    # a map travel, so its later connections carry a DIFFERENT suffix -- and the
    # 09-13 corner regime lives in `-c4`/`-c5`, which the old `-c1` glob could not
    # even open, half of why four post-ship hard rows sat unread for eleven days.
    # Each connection is scored on its own, which is what a per-connection warp
    # census wants.
    caps = sorted(glob.glob(os.path.join(root, "authsrv-*-c*.jsonl")))
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
        c = score_capture(rows, mesh, cap)
        t = score_tape(tape, mesh, cap, c.get("_reps")) if tape and os.path.exists(tape) else None
        red, _w = report(cap, tape, mesh, mid, c, t)
        total_red += red
    if "--check" in argv:
        return 1 if total_red else 0
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
