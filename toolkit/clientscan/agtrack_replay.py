"""agtrack_replay.py -- MOVECODE-1z-q step 2: replay the AgTrack mirror
against gamesrv captures and require it to predict the snaps that happened.

THE QUESTION.  agtrack_mirror.py (toolkit/authsrv/) maintains the client's
own history chain and reprieve test from events the server already emits or
observes.  A mirror that cannot reproduce the corpus's observed warps is
wrong and must say so; one that can is the derived basis for a grant policy
that keeps the client's own test at MATCH.  This tool is the check, run over
data that already exists -- no client run, no operator.

WHAT IS COMPARED.  For every capture:
  * the mirror is driven by the capture's own event stream -- our grants
    (0x0029/0x002A), hard-sets (0x002C), speed changes (0x002B), and the
    client's c2s command stream (0x003E clicks, 0x003D headings, 0x0047
    stops), plus synthetic 100 ms ticks for the client's arrival consumption
    and keep-alive sweep;
  * ground truth is the client's own report stream scored by movesync's
    two-arm hard bar (>400 u/s at dt >= 0.05 s, or >= 520 u below the dt
    floor) -- the arc's standing warp definition, not a new one.

SCORING, and the asymmetry that matters.  A MATCH is sufficient for no-snap
in the client (it jumps clean over all three gates), so the KILLING CELL is
an observed hard step whose window contains ONLY MATCH verdicts -- the
mirror flatly contradicted by the client.  A window with a NOMATCH-PASS is
"gates-blind" (gate 3 is unmodelled, the async estimate is interpolated);
a window with a predicted SNAP is covered; a window with no evaluation at
all names a dispatch source we did not model.  Two vacuity guards travel
with every score: the MATCH rate over all evaluations (an always-MISS
mirror covers every warp trivially), and --known-bad, which shrinks the
match radius to 10 u and must visibly degrade the score, or the metric is
measuring nothing (feedback: run the known-bad arm).

Usage:
  python toolkit/clientscan/agtrack_replay.py <capture.jsonl> [...]
  python toolkit/clientscan/agtrack_replay.py --latest N     # newest scoreable
  python toolkit/clientscan/agtrack_replay.py --all          # whole corpus
  add --no-mesh to skip navmesh loading (walkable conjunct degrades to
  straight-line-only, labelled); --known-bad for the control arm; --json for
  machine-readable output.
"""

import argparse
import bisect
import json
import math
import os
import re
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLKIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, TOOLKIT)
sys.path.insert(0, os.path.join(TOOLKIT, "authsrv"))
sys.path.insert(0, os.path.join(TOOLKIT, "mapdata"))

import vaultpath                     # noqa: E402
import planecensus as pc             # noqa: E402
import movesync                      # noqa: E402
import agtrack_mirror as am          # noqa: E402

OP_GRANT = 41            # 0x0029 AGENT_MOVE_TO_POINT
OP_DEST = 42             # 0x002A AGENT_UPDATE_DESTINATION
OP_SPEED = 43            # 0x002B AGENT_UPDATE_SPEED
OP_SETPOS = 44           # 0x002C AGENT_UPDATE_POSITION
OP_HEADING = 61          # 0x003D c2s MOVE_SET_HEADING
OP_CLICK = 62            # 0x003E c2s MOVE_TO_COORD
OP_STOP = 71             # 0x0047 c2s stop-report
INSTANCE_LOAD = 405
_LOADFILE = re.compile(r"INSTANCE_LOAD_SPAWN_POINT\(file (\d+)\)")

TICK_MS = 100            # synthetic tick for arrivals + the 3.333 s sweep
WINDOW_BEFORE = 0.25     # s before the pre-step report an eval may sit
FALSE_ALARM_WINDOW = 2.0 # s after a predicted snap for its hard step to show


def load_events(path):
    """One pass -> (events, fid). events = [(t, kind, payload)] sorted.

    Grant payloads are decoded from the sent row's `plain` hex by
    planecensus.parse_move (player-agent gate included); wire word order per
    the 0x0029 handler decode: word@14 rides the POINT (the destination's
    plane), word@16 is arg4 -> agent+0x80 (the agent's current plane)
    (studies/movement/FINDINGS.md:849-867).
    """
    events, fid = [], None
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            if '"sent"' not in line and '"decoded"' not in line:
                continue
            try:
                r = json.loads(line)
            except ValueError:
                continue
            kind, op, t = r.get("kind"), r.get("opcode"), r.get("t", 0.0)
            if kind == "sent":
                if op in (OP_GRANT, OP_DEST):
                    got = pc.parse_move(r.get("plain") or "")
                    if got:
                        events.append((t, "grant",
                                       (got[0], got[1], got[2], got[3],
                                        got[4])))
                elif op == OP_SETPOS:
                    got = pc.parse_move(r.get("plain") or "")
                    if got:
                        events.append((t, "setpos",
                                       (got[0], got[1], got[2])))
                elif op == OP_SPEED:
                    b = b""
                    try:
                        b = bytes.fromhex(r.get("plain") or "")
                    except ValueError:
                        pass
                    if len(b) >= 10 and struct.unpack_from(
                            "<I", b, 2)[0] == pc.PLAYER_AGENT_ID:
                        rate = struct.unpack_from("<f", b, 6)[0]
                        events.append((t, "speed", rate))
                elif op == INSTANCE_LOAD and fid is None:
                    m = _LOADFILE.search(r.get("label") or "")
                    if m:
                        fid = int(m.group(1))
            elif kind == "decoded":
                vals = r.get("values")
                if not isinstance(vals, (list, tuple)) or len(vals) < 2:
                    continue
                p = vals[1]
                if not isinstance(p, (list, tuple)) or len(p) < 2:
                    continue
                if op == OP_HEADING and len(vals) >= 5:
                    hv = vals[3] if isinstance(vals[3], (list, tuple)) \
                        else (0.0, 0.0)
                    events.append((t, "heading",
                                   (float(p[0]), float(p[1]),
                                    vals[2] if isinstance(vals[2], int)
                                    else None,
                                    float(hv[0]), float(hv[1]),
                                    vals[4])))
                elif op == OP_STOP:
                    events.append((t, "stop",
                                   (float(p[0]), float(p[1]),
                                    vals[2] if isinstance(vals[2], int)
                                    else None)))
                elif op == OP_CLICK:
                    events.append((t, "click",
                                   (float(p[0]), float(p[1]),
                                    vals[2] if isinstance(vals[2], int)
                                    else None)))
    events.sort(key=lambda e: e[0])
    return events, fid


class AsyncTrack(object):
    """The rendered copy's position, interpolated from the client's own wire
    reports (movesync.load_wire_reports: spliced 0x003D + 0x0047).  Linear
    between samples; during click silences (documented to 37 s) the chord is
    an approximation, stated rather than hidden."""

    def __init__(self, reports):
        self.ts = [r[0] for r in reports]
        self.ps = [(r[1][0], r[1][1]) for r in reports]

    def at(self, t):
        if not self.ts:
            return None
        i = bisect.bisect_right(self.ts, t)
        if i == 0:
            return self.ps[0]
        if i >= len(self.ts):
            return self.ps[-1]
        t0, t1 = self.ts[i - 1], self.ts[i]
        p0, p1 = self.ps[i - 1], self.ps[i]
        if t1 <= t0:
            return p1
        f = (t - t0) / (t1 - t0)
        return (p0[0] + f * (p1[0] - p0[0]), p0[1] + f * (p1[1] - p0[1]))


def hard_steps(reports):
    """movesync's two-arm hard bar over consecutive wire reports.

    Constants imported, not restated (toolkit/clientscan/movesync.py:184-216).
    Returns [(t0, t1, dist, p0, p1)].
    """
    out = []
    for i in range(1, len(reports)):
        t0, p0 = reports[i - 1][0], reports[i - 1][1]
        t1, p1 = reports[i][0], reports[i][1]
        dt = t1 - t0
        d = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
        if dt >= movesync.HARD_JUMP_MIN_DT:
            if d / dt > movesync.HARD_JUMP_SPEED:
                out.append((t0, t1, d, p0, p1))
        elif d >= movesync.HARD_JUMP_UNITS:
            out.append((t0, t1, d, p0, p1))
    return out


def replay_capture(path, mesh=None, prune_ms=None):
    """Drive the mirror through one capture. -> per-capture result dict."""
    events, fid = load_events(path)
    reports, _walls, _src = movesync.load_wire_reports(path)
    atrack = AsyncTrack(reports)
    mirror = am.AgTrackMirror(mesh=mesh, prune_ms=prune_ms)
    verdicts = []
    sync_trace = []          # (t_ms, x, y) -- for post-hoc step attribution

    def ms(t):
        return int(round(t * 1000.0))

    def trace(t_ms):
        p = mirror.sync.position(t_ms)
        if p is not None:
            sync_trace.append((t_ms, p[0], p[1]))

    last_ms = None
    cur_plane = None       # the async copy's own plane, from its reports
    for t, kind, data in events:
        now = ms(t)
        if last_ms is None:
            last_ms = now
        while last_ms + TICK_MS <= now:
            last_ms += TICK_MS
            v = mirror.tick(last_ms, atrack.at(last_ms / 1000.0))
            if v is not None:
                verdicts.append(v)
            trace(last_ms)
        apos = atrack.at(t)
        if kind == "grant":
            x, y, plane_a, plane_b, op = data
            v = mirror.on_grant(x, y, plane_a, plane_b, now,
                                async_pos=apos, opcode=op)
            verdicts.append(v)
        elif kind == "setpos":
            x, y, plane = data
            verdicts.append(mirror.on_update_position(x, y, plane, now))
        elif kind == "speed":
            mirror.on_speed(data, now)
        elif kind == "heading":
            x, y, plane, hx, hy, mtype = data
            cur_plane = plane if plane is not None else cur_plane
            mirror.on_player_command(
                now, (x, y), plane,
                ("head", round(hx, 1), round(hy, 1), mtype))
        elif kind == "stop":
            x, y, plane = data
            cur_plane = plane if plane is not None else cur_plane
            mirror.on_player_command(now, (x, y), plane, ("stop",))
        elif kind == "click":
            # 0x003E's dword is the clicked DESTINATION's plane (the stairs
            # note, authsrv.py:16844-16868).  The recorder's NODE samples the
            # async agent's own position block -- x, y and ITS current plane
            # (+0x80) -- so the node carries the plane the client last
            # REPORTED, and only the SEED (destination while moving) carries
            # the click's plane.
            x, y, dplane = data
            pos = apos if apos is not None else (x, y)
            speed = 288.0 * mirror.sync.move_speed
            d = math.hypot(x - pos[0], y - pos[1])
            arrive = now + max(int(d * 1000.0 / speed), 1) if speed > 0 \
                else 0
            mirror.on_player_command(
                now, pos, cur_plane, ("click", round(x, 1), round(y, 1)),
                dest=(x, y, dplane), arrive_t=arrive)
        trace(now)
        last_ms = max(last_ms, now)

    # ---- score ----------------------------------------------------------
    steps = hard_steps(reports)
    tested = [v for v in verdicts
              if v.code in (am.MATCH, am.NOMATCH_PASS, am.SNAP)]
    snaps = [v for v in tested if v.code == am.SNAP]
    trace_ts = [row[0] for row in sync_trace]

    def sync_at(t_s):
        """The mirror's sync position nearest (at or before) t seconds."""
        if not sync_trace:
            return None
        i = bisect.bisect_right(trace_ts, int(round(t_s * 1000.0)))
        row = sync_trace[i - 1] if i > 0 else sync_trace[0]
        return (row[1], row[2])

    per_step = []
    covered_snaps = set()
    for (t0, t1, d, p0, p1) in steps:
        win = [v for v in tested
               if t0 - WINDOW_BEFORE <= v.t / 1000.0 <= t1]
        codes = set(v.code for v in win)
        if am.SNAP in codes:
            cls = "covered"
            for v in win:
                if v.code == am.SNAP:
                    covered_snaps.add(id(v))
        elif am.NOMATCH_PASS in codes:
            cls = "gates-blind"
        elif am.MATCH in codes:
            cls = "MATCH-CONTRADICTED"      # the killing cell
            for v in win:
                if v.code == am.MATCH and v.matched:
                    (nx, ny, npl), pv, sig = v.matched
                    print(f"    [contradicted] eval t={v.t/1000.0:.3f} "
                          f"q=({v.q[0]:.0f},{v.q[1]:.0f}) matched node "
                          f"({nx:.0f},{ny:.0f}) pl{npl} sig={sig} -> prev "
                          f"{pv and (round(pv[0]), round(pv[1]))}, "
                          f"age {v.matched_age_ms}ms, chain "
                          f"{v.chain_len}", file=sys.stderr)
        else:
            cls = "no-eval"
        # ATTRIBUTION: a real AgTrack snap reseeds async <- sync, so the
        # post-step report lands ON the sync trajectory.  A step that lands
        # nowhere near it was not an AgTrack snap (candidate: the gate-free
        # local-input route 0x005FCAA0, studies/movement/HANDOFF.md:765).
        s1 = sync_at(t1)
        to_sync = (round(math.hypot(p1[0] - s1[0], p1[1] - s1[1]), 1)
                   if s1 else None)
        s0 = sync_at(t0)
        from_sync = (round(math.hypot(p0[0] - s0[0], p0[1] - s0[1]), 1)
                     if s0 else None)
        per_step.append({"t0": round(t0, 3), "t1": round(t1, 3),
                         "dist": round(d, 1), "class": cls,
                         "n_evals": len(win),
                         "to_sync": to_sync, "from_sync": from_sync})
    false_alarms = 0
    alarm_rows = []
    for v in snaps:
        if id(v) in covered_snaps:
            continue
        ts = v.t / 1000.0
        if not any(t0 - WINDOW_BEFORE <= ts <= t1 + FALSE_ALARM_WINDOW
                   for (t0, t1, _d, _p, _q) in steps):
            false_alarms += 1
            alarm_rows.append({
                "t": round(ts, 3), "event": v.event,
                "gate1": v.gate1, "gate2": v.gate2,
                "sep": (round(v.gate1_sep, 1)
                        if v.gate1_sep is not None else None)})
    counts = {"covered": 0, "gates-blind": 0, "MATCH-CONTRADICTED": 0,
              "no-eval": 0}
    for s in per_step:
        counts[s["class"]] += 1
    n_tested = len(tested)
    n_match = sum(1 for v in tested if v.code == am.MATCH)
    return {
        "capture": os.path.basename(path),
        "fid": fid,
        "mesh": ("loaded" if mesh is not None
                 and not getattr(mesh, "straightline_only", False)
                 else "straightline-only"),
        "reports": len(reports),
        "events": len(events),
        "evaluations": n_tested,
        "match": n_match,
        "nomatch_pass": sum(1 for v in tested
                            if v.code == am.NOMATCH_PASS),
        "snap_predicted": len(snaps),
        "match_rate": round(n_match / n_tested, 4) if n_tested else None,
        "hard_steps": len(steps),
        "step_classes": counts,
        "false_alarm_snaps": false_alarms,
        "chain_pushes": mirror.n_push,
        "clears": mirror.n_clear,
        "steps": per_step,
        "false_alarms": alarm_rows,
    }


class _Meshes(object):
    """Load-once PathingMap cache keyed by file id; failure -> None once."""

    def __init__(self):
        self.cache = {}

    def get(self, fid):
        if fid is None:
            return None
        if fid not in self.cache:
            try:
                from pathmap import PathingMap
                self.cache[fid] = am.MeshAdapter(PathingMap.load(fid))
            except Exception as e:
                print(f"  [mesh] file id 0x{fid:X} unavailable ({e}); "
                      f"straightline-only", file=sys.stderr)
                self.cache[fid] = None
        return self.cache[fid]


def scoreable_captures(vault):
    """The census's own labelled set, newest first (reports + a file id)."""
    labelled, _un, _cross = pc.label_captures(vault, 600.0)
    rows = [(v["path"], v["fid"], v["n"]) for v in labelled.values()
            if v["n"] > 0]
    rows.sort(key=lambda r: os.path.basename(r[0]), reverse=True)
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("captures", nargs="*", help="capture .jsonl paths")
    ap.add_argument("--latest", type=int, default=0,
                    help="replay the N newest scoreable captures")
    ap.add_argument("--all", action="store_true",
                    help="replay every scoreable capture in the corpus")
    ap.add_argument("--no-mesh", action="store_true",
                    help="skip navmesh loading (straightline-only, labelled)")
    ap.add_argument("--known-bad", action="store_true",
                    help="CONTROL ARM: shrink the match radius to 10 u; the "
                         "score must degrade or the metric measures nothing")
    ap.add_argument("--prune-ms", type=int, default=None,
                    help="reader 2's prune horizon in ms (the by-time render "
                         "query 0x00604ED0; cadence unresolved in the decode "
                         "-- the corpus adjudicates). Omit = never prunes.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    if args.known_bad:
        am.R_MATCH = 10.0
        am.R_MATCH_SQ = 100.0
        print("[known-bad] match radius forced to 10 u -- control arm",
              file=sys.stderr)

    paths = list(args.captures)
    meshes = _Meshes()
    if args.latest or args.all:
        vault = vaultpath.vault_root()
        rows = scoreable_captures(vault)
        if args.latest:
            rows = rows[:args.latest]
        paths += [r[0] for r in rows]
    if not paths:
        ap.error("no captures named; use paths, --latest N or --all")

    results = []
    for p in paths:
        mesh = None
        if not args.no_mesh:
            _ev, fid = None, None
            # cheap fid pre-read via load_events is wasteful; replay reads it
            # anyway -- load mesh lazily by peeking the label line.
            with open(p, encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if "INSTANCE_LOAD_SPAWN_POINT" in line:
                        m = _LOADFILE.search(line)
                        if m:
                            fid = int(m.group(1))
                        break
            mesh = meshes.get(fid)
        results.append(replay_capture(p, mesh=mesh, prune_ms=args.prune_ms))

    tot = {"captures": len(results),
           "evaluations": sum(r["evaluations"] for r in results),
           "match": sum(r["match"] for r in results),
           "snap_predicted": sum(r["snap_predicted"] for r in results),
           "hard_steps": sum(r["hard_steps"] for r in results),
           "false_alarm_snaps": sum(r["false_alarm_snaps"]
                                    for r in results),
           "step_classes": {}}
    for k in ("covered", "gates-blind", "MATCH-CONTRADICTED", "no-eval"):
        tot["step_classes"][k] = sum(r["step_classes"][k] for r in results)

    if args.json:
        print(json.dumps({"per_capture": results, "total": tot}, indent=1))
        return 0

    for r in results:
        print(f"\n=== {r['capture']}  (mesh: {r['mesh']}, "
              f"fid: {r['fid'] and hex(r['fid'])})")
        print(f"  events {r['events']}, reports {r['reports']}, "
              f"evaluations {r['evaluations']} "
              f"(match {r['match']}, nomatch-pass {r['nomatch_pass']}, "
              f"snap {r['snap_predicted']}), chain pushes "
              f"{r['chain_pushes']}, clears {r['clears']}")
        print(f"  hard steps {r['hard_steps']}: {r['step_classes']}  "
              f"false-alarm snaps {r['false_alarm_snaps']}")
        for s in r["steps"]:
            print(f"    step t={s['t0']}..{s['t1']} "
                  f"{s['dist']}u -> {s['class']} "
                  f"({s['n_evals']} evals; post-step report is "
                  f"{s['to_sync']}u from mirror-sync, was "
                  f"{s['from_sync']}u before)")
        for a in r["false_alarms"]:
            print(f"    false-alarm snap t={a['t']} on {a['event']}: "
                  f"gate1={a['gate1']} gate2={a['gate2']} "
                  f"sep={a['sep']}u")
    print(f"\nTOTAL: {tot['captures']} captures, "
          f"{tot['evaluations']} evaluations, "
          f"{tot['hard_steps']} hard steps -> {tot['step_classes']}, "
          f"{tot['false_alarm_snaps']} false-alarm snaps")
    mr = (tot["match"] / tot["evaluations"]) if tot["evaluations"] else 0
    print(f"vacuity guard: corpus MATCH rate {mr:.1%} "
          f"(an always-MISS mirror would cover trivially)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
