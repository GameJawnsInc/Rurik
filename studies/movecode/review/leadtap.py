#!/usr/bin/env python3
"""What the CLIENT's pathfinder said when a lead crossed a file-linked portal (MOVECODE-1z-bd).

    python studies/movecode/review/leadtap.py <harness run id> --hook <movehook.bin>

THE QUESTION (FINDINGS sec.1z-bc.3). Six leads that locked the client all crossed
a seam the pathing file links as a portal, and the body walked none of them. R7
(sec.1z-i) measured the client's own `MapFindPath` returning pathCount == 0 exactly
when the declared from-plane is impossible at the from-point -- but that was on
click walks. This joins THREE captures of one lead run with the movehook return
tap armed, and asks, per portal-crossing lead grant: did the client's pathfinder
run, what did it declare, and what did it answer, while the body did what?

THE JOIN.
  * gamesrv capture: fired keyboard leads (`grant_verdict`, lead_src=kbd), each
    with its report origin and plane and its granted point; a lead is PORTAL-
    CROSSING when it was granted at or past gate 1 (299.33 u) where 1z-ap's
    any-plane-change clip would have stopped it short of the gate -- i.e. the
    seam ray let it through a file-linked portal (--lead-seam-clip).
  * movehook capture: GetTickCount ticks, aligned to the wall clock on the
    `agapi_setdest` records -- the 0x0029 handler's entry, whose pt_a is the
    granted point -- matched by coordinate to the server's own grant rows. The
    offset is the median; its spread is printed, because a join that cannot show
    its alignment error is a guess (sec.1z-o.6 got +-8 ms on three anchors).
  * agenttap tape: the drawn body's class on the lead's leg (seamscore.score_leg,
    LIVE positions).

PER PORTAL-CROSSING LEAD: every `MapFindPath` question in [grant - 0.3 s, grant +
2.5 s] with its from-point, declared plane, to-point and pathCount (paired to its
answer on (tid, esp) by readhook._pair_mfp); the other tapped sites' hits in the
same window (setdest per world, bake, agtrack, chcli_dir, inputeval); the body's
class. Then R7's table for the whole run: pathCount == 0 against whether the
declared from-plane is one our mesh offers there.

THE THREE REGISTERED OUTCOMES (RUN-1zBD.md) are printed as counts, never
decided here:
  (a) a query at the grant, declared plane = body's plane, pathCount == 0  -- R7's class
  (b) a query at the grant with pathCount > 0 while the body PARKED       -- not the pathfinder
  (c) no query at all in the window                                       -- the keyboard mover
      parks without consulting MapFindPath; read the other sites

Read-only. Needs the vault (mesh, captures, tape). Stdlib only.
"""
import argparse
import glob
import json
import math
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "mapdata"))
sys.path.insert(0, os.path.join(HERE, "..", "..", "..", "toolkit", "clientscan", "movehook"))

GATE = 299.332591
LEAD = 520.0
STEP = 2.0
WIN_BEFORE, WIN_AFTER = 0.3, 2.5
MAP_FILE = {146: 0x1B97D}


def _f(dw):
    return struct.unpack("<f", struct.pack("<I", dw))[0]


def pt(rec, key):
    """(x, y, plane) from a 4-dword point field, or None."""
    p = rec.get(key)
    if not p:
        return None
    return (_f(p[0]), _f(p[1]), p[2])


def leads_from(R):
    """[(grant_wall, origin, plane, granted_dest, raw_dest, why)] for fired kbd leads."""
    out, reports = [], []
    for r in R:
        if r.get("kind") == "position_report" and r.get("reported"):
            reports.append((tuple(r["reported"]), r.get("plane")))
        elif (r.get("kind") == "grant_verdict" and r.get("fired")
              and r.get("lead_src") == "kbd" and reports):
            (ox, oy), plane = reports[-1]
            dest = tuple(r["dest"])
            dx, dy = dest[0] - ox, dest[1] - oy
            if math.hypot(dx, dy) < 1.0:
                if len(reports) < 2:
                    continue
                (px, py), _ = reports[-2]
                dx, dy = ox - px, oy - py
            L = math.hypot(dx, dy)
            if L < 1.0:
                continue
            raw = (ox + LEAD * dx / L, oy + LEAD * dy / L)
            out.append((r["wall_unix"], (ox, oy), plane, dest, raw, r.get("lead_clip_why")))
    return out


def align(cap, names, grants):
    """tick(ms) -> wall offset from agapi_setdest points matched to grant dests.
    -> (offset_seconds, n_anchors, spread_ms) or (None, 0, None)."""
    idx = {n: i for i, n in enumerate(names)}
    si = idx.get("agapi_setdest")
    if si is None:
        return None, 0, None
    offs = []
    for r in cap.recs:
        if r["site"] != si:
            continue
        p = pt(r, "pt_a")
        if p is None:
            continue
        # the nearest grant by coordinate, then the offset it implies
        best = None
        for g_wall, dest in grants:
            d = math.hypot(p[0] - dest[0], p[1] - dest[1])
            if d < 1.0 and (best is None or d < best[0]):
                best = (d, g_wall)
        if best is not None:
            offs.append(best[1] - r["tick"] / 1000.0)
    if not offs:
        return None, 0, None
    # TWO PASSES. The same POINT is granted many times over a run (a zero-lead
    # echo re-sends the body's own report while it stands), so a setdest can
    # match several grant rows by coordinate alone and the first-pass offsets
    # scatter by whole seconds (492 ms spread on 22 anchors, run 1 of
    # RUN-1zBD). The median of the first pass is still the true offset; the
    # second pass keeps only anchors within 0.25 s of it and reports THAT
    # spread, which is the alignment error a reader should carry.
    med = statistics.median(offs)
    kept = [o for o in offs if abs(o - med) < 0.25]
    if not kept:
        kept = offs
    med = statistics.median(kept)
    spread = (max(kept) - min(kept)) * 1000.0 if len(kept) > 1 else 0.0
    return med, len(kept), spread


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run", help="harness run id")
    ap.add_argument("--hook", required=True, help="movehook.bin for this run")
    ap.add_argument("--tape", default=None)
    ap.add_argument("--map", type=int, default=146)
    a = ap.parse_args()

    from vaultpath import require_dir
    from pathmap import PathingMap
    import readhook
    import seamscore as SC
    vault = require_dir()
    pm = PathingMap.load(MAP_FILE[a.map])
    rundir = os.path.join(vault, "captures", "harness", a.run)
    rep = json.load(open(os.path.join(rundir, "report.json")))
    cap_path = [c.replace("\\", "/") for c in rep["captures"] if "gamesrv" in c.replace("\\", "/")][0]
    R, bad = SC.load_rows(cap_path)
    t_lo = min(w["started_unix"] for w in rep["walk"]) - 120
    t_hi = max(w["ended_unix"] for w in rep["walk"]) + 60
    tapes = sorted(glob.glob(os.path.join(vault, "research", "animref", "agenttap-*.jsonl")))
    tpath = a.tape or SC.pick_tape(tapes, t_lo, t_hi)
    tape = SC.Tape(tpath)
    hook = readhook.Capture(a.hook)
    names = readhook.site_names(hook)
    ca, cb, _txt = hook.sidecar()
    print("run %s: gamesrv %s (%d rows), tape %s (%d samples%s), hook %s (v%d, %d records, "
          "%d partial; control A %s, B %s)"
          % (a.run, os.path.basename(cap_path), len(R), os.path.basename(tpath), len(tape.samples),
             "" if t_lo <= tape.t0 <= t_hi else " -- NOT IN WINDOW", os.path.basename(a.hook),
             hook.version, hook.stored, hook.partial,
             "FIRED" if ca else ca, "FIRED" if cb else cb))
    idx = {n: i for i, n in enumerate(names)}
    hits = {n: sum(1 for r in hook.recs if r["site"] == i) for n, i in idx.items()}
    print("  site hits: %s" % ", ".join("%s %d" % (n, hits[n]) for n in sorted(hits) if hits[n]))

    leads = leads_from(R)
    grants = [(g, d) for g, _o, _p, d, _raw, _w in leads]
    # every fired grant (zero-lead echoes included) is an anchor candidate
    for r in R:
        if r.get("kind") == "grant_verdict" and r.get("fired") and r.get("dest"):
            grants.append((r["wall_unix"], tuple(r["dest"])))
    off, n_anch, spread = align(hook, names, grants)
    if off is None:
        print("  CANNOT ALIGN the hook's ticks to the wall: no agapi_setdest record "
              "matched a grant point. Nothing below the R7 table is joinable.")
    else:
        print("  tick -> wall offset %.3f s from %d setdest anchors, spread %.0f ms"
              % (off, n_anch, spread))

    def wall(r):
        return None if off is None else r["tick"] / 1000.0 + off

    pairs, orphan, esp_bad = readhook._pair_mfp(hook, names)
    mfp_i = idx.get("mapfindpath")
    entries = [r for r in hook.recs if r["site"] == mfp_i] if mfp_i is not None else []
    print("  MapFindPath: %d entries, %d paired with an answer, %d unpaired answers, %d esp mismatches"
          % (len(entries), len(pairs), orphan, esp_bad))
    ret_of = {id(e): r for e, r in pairs}

    # ---- the leads ------------------------------------------------------------
    print("\nLEADS (%d fired keyboard leads):" % len(leads))
    portal = []
    for g, o, plane, dest, raw, why in leads:
        pl = pm.plane_at(o[0], o[1], prefer=plane)
        reach = math.hypot(dest[0] - o[0], dest[1] - o[1])
        pc = pm.clip(o[0], o[1], raw[0], raw[1], step=STEP, plane=pl) if pl is not None else None
        rp = math.hypot(pc[0] - o[0], pc[1] - o[1]) if pc else None
        crossing = rp is not None and reach >= GATE > rp
        if crossing:
            portal.append((g, o, plane, dest, raw, why, rp))
    print("  %d granted at/past gate 1 where the plane clip would have stopped short: PORTAL-CROSSING"
          % len(portal))
    outcomes = {"a": 0, "b": 0, "c": 0, "other": 0}
    for g, o, plane, dest, raw, why, rp in portal:
        print("\n  LEAD at +%.2fs: origin (%.0f,%.0f) plane %s -> granted (%.0f,%.0f), %.0f u "
              "(plane clip would stop at %.0f u); why=%s"
              % (g - leads[0][0], o[0], o[1], plane, dest[0], dest[1],
                 math.hypot(dest[0] - o[0], dest[1] - o[1]), rp, why))
        sc = SC.score_leg(tape, g, o, dest)
        pre = [s for s in tape.window(g - 0.4, g)]
        if pre:
            a0 = pre[-1]["agents"]["1"]
            print("    at the grant: body v %.0f u/s, fence %s, async stop=%s"
                  % (SC.speed(a0["async"]), SC.Tape.fence(pre[-1]), a0["async"].get("stop")))
        if sc:
            print("    body: %s -- moving %.0f%%, travelled %.0f u, sync %.0f u, max separation %.0f u, "
                  "largest live jump %.0f u%s%s"
                  % (sc["class"], 100 * sc["moving"], sc["body_move"], sc["sync_move"], sc["max_sep"],
                     sc["snap"], " at +%.2fs" % sc["snap_at"] if sc["snap"] >= SC.SNAP_U else "",
                     "; fence %s" % ", ".join("+%.2fs %s->%s" % f for f in sc["fences"]) if sc["fences"] else ""))
        else:
            print("    body: no tape window")
        if off is None:
            continue
        w0, w1 = g - WIN_BEFORE, g + WIN_AFTER
        win = [r for r in hook.recs if w0 <= wall(r) <= w1]
        counts = {}
        for r in win:
            n = names[r["site"]] if r["site"] < len(names) else "site%d" % r["site"]
            tag = n + ("[w%d]" % r["world"] if n in ("agapi_setdest", "bake") and "world" in r else "")
            counts[tag] = counts.get(tag, 0) + 1
        print("    hook hits in [-%.1f, +%.1f]s: %s" % (WIN_BEFORE, WIN_AFTER,
              ", ".join("%s %d" % kv for kv in sorted(counts.items())) or "none"))
        qs = [r for r in win if r["site"] == mfp_i]
        if not qs:
            outcomes["c"] += 1
            print("    MapFindPath: NO QUERY in the window  -> outcome (c)")
            continue
        for q in qs:
            src, dst = pt(q, "pt_a"), pt(q, "pt_b")
            ret = ret_of.get(id(q))
            n = ret.get("out_count") if ret else None
            at_src = sorted(pm.planes_at(src[0], src[1])) if src else None
            print("    MapFindPath +%.3fs: from (%.0f,%.0f) plane %s [mesh offers %s] -> to (%.0f,%.0f) plane %s: pathCount %s"
                  % (wall(q) - g, src[0], src[1], src[2], at_src, dst[0], dst[1], dst[2], n if ret else "UNPAIRED")
                  if src and dst else "    MapFindPath +%.3fs: points unreadable (have_pts %s)" % (wall(q) - g, q.get("have_pts")))
            if ret is None:
                outcomes["other"] += 1
            elif n == 0:
                outcomes["a"] += 1
            elif sc and sc["class"].startswith("PARKED"):
                outcomes["b"] += 1
            else:
                outcomes["other"] += 1

    # ---- R7's table for this run ---------------------------------------------------
    print("\nR7 TABLE for this run (paired MapFindPath queries):")
    rows = {"match": [0, 0], "mismatch": [0, 0], "off-mesh": [0, 0]}
    for e, r in pairs:
        src = pt(e, "pt_a")
        if src is None:
            continue
        pls = pm.planes_at(src[0], src[1])
        k = "off-mesh" if not pls else ("match" if src[2] in pls else "mismatch")
        rows[k][0] += 1
        rows[k][1] += 1 if r.get("out_count") == 0 else 0
    for k in ("match", "mismatch", "off-mesh"):
        print("  from-point %-9s n %3d   pathCount == 0: %d" % (k, rows[k][0], rows[k][1]))

    print("\nOUTCOMES over %d portal-crossing leads: (a) query, pathCount 0: %d   (b) query > 0 while parked: %d   "
          "(c) no query: %d   other/unpaired: %d"
          % (len(portal), outcomes["a"], outcomes["b"], outcomes["c"], outcomes["other"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
