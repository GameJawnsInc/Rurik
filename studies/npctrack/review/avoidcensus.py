"""NPCTRACK-F14 -- the client's agent-avoidance pass, replayed through the SHIPPED mirror
(toolkit/authsrv/agtrack_mirror.AgTrackMirror with `obstacles` = the hostile's sync copy off the
tape) on the arc's seven tapes, and scored two ways:

  1. THE CENSUS: every sidestep the mirror bakes against every waypoint leg the tape shows on
     the player's sync copy (bit 18 rising, or its epoch/segment changing while set, with a
     finite segment), per grant, plus the halts the mirror predicts (a lead ending inside a
     parked hostile's disc) against the tape's own evidence of a halt;
  2. THE FRAME: the mirror against the client's world-0 copy while moving, and F5's hybrid
     frame (last STOP report while standing, the mirror while moving) at the halts.

    python studies/npctrack/review/avoidcensus.py              # the shipped arm
    python studies/npctrack/review/avoidcensus.py --no-avoid   # the revert arm (MIRROR_AVOID off)

Pinned 2026-09-06 (FINDINGS F14): avoid ON -- 232 grants, 24 both / 1 model-only / 1 tape-only,
14 halts, waypoint error p50 0.2 u; mirror vs world-0 moving p50 10.1 / p90 19.9 / max 105
(n = 1,509); hybrid at 120 halts p50 1.5 / p90 17.6.  Avoid OFF -- 0 / 0 / 25, 0 halts; moving
p90 89.3; hybrid p90 49.9.  The tapes are fixed files, so these are exact pins, not floors.
"""
import sys, os, math, bisect, json, tempfile, statistics

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "authsrv"))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
import npcdrift as N                 # noqa: E402
import agtrack_replay as AR          # noqa: E402
import agtrack_mirror as am          # noqa: E402
import movesync                      # noqa: E402
import w0score as W                  # noqa: E402
import vaultpath                     # noqa: E402

V = vaultpath.vault_root()
RUNS = [(n, os.path.join(V, t), os.path.join(V, c)) for n, t, c in N.PINNED] + [
    ("R1(Q1)", os.path.join(V, "research/npctrack/r1-agenttap.jsonl"),
     os.path.join(V, "captures/gamesrv/authsrv-20260906T094349-c1.jsonl")),
    ("R1(ctrl)", os.path.join(V, "research/npctrack/r1-control-agenttap.jsonl"),
     os.path.join(V, "captures/gamesrv/authsrv-20260906T100642-c1.jsonl")),
    ("R2", os.path.join(V, "research/npctrack/r2-agenttap.jsonl"),
     os.path.join(V, "captures/gamesrv/authsrv-20260906T124708-c1.jsonl")),
    ("R3", os.path.join(V, "research/npctrack/r3-agenttap.jsonl"),
     os.path.join(V, "captures/gamesrv/authsrv-20260906T125541-c1.jsonl")),
]
TICK = 16          # the replay's own frame; the client's world-0 tick steps 100 ms (F14)


# ---------------------------------------------------------------------------
# tape helpers
# ---------------------------------------------------------------------------

def hostile_series(rows, head, aid=10):
    out = []
    for s in rows:
        a = (s.get("agents") or {}).get(str(aid))
        if not a or not a.get("sync") or "x" not in a["sync"]:
            continue
        out.append((head["t0"] + s["t"], a["sync"], s.get("clock0")))
    return out


class Hostile(object):
    """The hostile's SYNC copy off the tape, dead-reckoned between samples the
    way the client's pass dead-reckons `other` (+0x78 + v*dt, arrival clamp)."""

    def __init__(self, ser, t0):
        self.ts = [w - t0 for w, _, _ in ser]
        self.ser = ser

    def at(self, t):
        if not self.ser:
            return None
        i = max(bisect.bisect_right(self.ts, t) - 1, 0)
        w, sy, c0 = self.ser[i]
        clock = (c0 + (t - self.ts[i]) * 1000.0) if c0 is not None else None
        pos = W.live(sy, clock)
        stop = sy.get("stop") or 0
        moving = not (stop != 0 and clock is not None and clock >= stop)
        v = (sy.get("vx", 0.0), sy.get("vy", 0.0)) if moving else (0.0, 0.0)
        if not (math.isfinite(pos[0]) and math.isfinite(pos[1])):
            return None
        return pos, v


def wp_legs(rows, head, t0, aid=1):
    """(t, seg, updated, v, start) at every waypoint leg on the sync copy: bit
    18 rising, or -- while it stays set -- the epoch or segment changing
    (two sidesteps in one sample interval never drop the bit)."""
    legs = []
    prev = 0
    prev_key = None
    for s in rows:
        a = (s.get("agents") or {}).get(str(aid))
        if not a or not a.get("sync") or "x" not in a["sync"]:
            continue
        sy = a["sync"]
        f = sy.get("flags", 0) & 0x40000
        key = (sy.get("updated"), sy.get("segx"), sy.get("segy"))
        if f and (not prev or key != prev_key) and math.isfinite(sy.get("segx", float("inf"))):
            legs.append((head["t0"] + s["t"] - t0, (sy["segx"], sy["segy"]), sy.get("updated"),
                         (sy.get("vx", 0.0), sy.get("vy", 0.0)), (sy.get("x"), sy.get("y"))))
        prev, prev_key = f, key
    return legs


# ---------------------------------------------------------------------------
# the replay through the shipped mirror
# ---------------------------------------------------------------------------

def replay(run_rows, reps, end_t, hostile):
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
    try:
        for r in run_rows:
            tmp.write(json.dumps(r) + "\n")
        tmp.close()
        events, _fid = AR.load_events(tmp.name)
        reports, _w, _s = movesync.load_wire_reports(tmp.name)
    finally:
        os.unlink(tmp.name)
    atrack = AR.AsyncTrack(reports)
    mirror = am.AgTrackMirror(mesh=None, prune_ms=3000)
    sa = mirror.sync

    def obst(ms):
        h = hostile.at(ms / 1000.0)
        return [(h[0][0], h[0][1], h[1][0], h[1][1])] if h else []
    mirror.obstacles = obst
    ms = lambda t: int(round(t * 1000.0))   # noqa: E731
    last = None
    grants, log, trace = [], [], []
    if reps:
        t, p, _ = reps[0]
        sa.set_position(p[0], p[1], 0, ms(t))
        last = ms(t)
    seen = [0, 0]

    def note(now):
        if sa.n_sidestep > seen[0]:
            seen[0] = sa.n_sidestep
            log.append((now / 1000.0, "fire", (sa.dest[0], sa.dest[1])))
        if sa.n_avoid_halt > seen[1]:
            seen[1] = sa.n_avoid_halt
            log.append((now / 1000.0, "halt", (sa.x78, sa.y78)))

    def frames_to(now):
        nonlocal last
        while last + TICK <= now:
            last += TICK
            mirror.tick(last, atrack.at(last / 1000.0))
            note(last)
            p = sa.position(last)
            if p:
                trace.append((last / 1000.0, p))
    cur_plane = None
    for t, kind, data in events:
        now = ms(t)
        if last is None:
            last = now
        frames_to(now)
        apos = atrack.at(t)
        if kind == "grant":
            x, y, pa, pb, op = data
            p0 = sa.position(now) or (sa.x78, sa.y78)
            dist = math.hypot(x - p0[0], y - p0[1]) if p0 and p0[0] is not None else 0.0
            mirror.on_grant(x, y, pa, pb, now, async_pos=apos, opcode=op)
            note(now)
            grants.append((t, x, y, dist))
        elif kind == "setpos":
            x, y, plane = data
            mirror.on_update_position(x, y, plane, now)
        elif kind == "speed":
            mirror.on_speed(data, now)
        elif kind == "heading":
            x, y, plane, hx, hy, mtype = data
            cur_plane = plane if plane is not None else cur_plane
            mirror.on_player_command(now, (x, y), plane, ("head", round(hx, 1), round(hy, 1), mtype))
        elif kind == "stop":
            x, y, plane = data
            cur_plane = plane if plane is not None else cur_plane
            mirror.on_player_command(now, (x, y), plane, ("stop",))
        elif kind == "click":
            x, y, dplane = data
            pos = apos if apos is not None else (x, y)
            speed = 288.0 * sa.move_speed
            d = math.hypot(x - pos[0], y - pos[1])
            arrive = now + max(int(d * 1000.0 / speed), 1) if speed > 0 else 0
            mirror.on_player_command(now, pos, cur_plane, ("click", round(x, 1), round(y, 1)),
                                     dest=(x, y, dplane), arrive_t=arrive)
        p = sa.position(now)
        if p:
            trace.append((now / 1000.0, p))
        last = max(last, now)
    frames_to(ms(end_t))
    trace.sort()
    return grants, log, events, trace


def score_run(name, tape, cap):
    head, rows = W.load(tape)
    crows = W.load_gamesrv(cap)
    t0 = N.cap_t0(crows)
    reps = sorted((r["t"], tuple(r["reported"]), r.get("source") == "0x0047")
                  for r in crows if r.get("kind") == "position_report" and r.get("accepted"))
    hs = Hostile(hostile_series(rows, head), t0)
    end = head["t0"] + rows[-1]["t"] - t0
    grants, log, events, trace = replay(crows, reps, end, hs)
    legs = wp_legs(rows, head, t0)
    fires = [(t, d) for t, k, d in log if k == "fire"]
    halts = [(t, d) for t, k, d in log if k == "halt"]
    ev_ts = sorted(set(e[0] for e in events if e[1] in ("grant", "setpos")))
    g_ts = [g[0] for g in grants]
    owner = {}
    for k, leg in enumerate(legs):
        j = bisect.bisect_right(g_ts, leg[0] + 0.08) - 1     # 80 ms of stamp slack
        if j >= 0:
            owner.setdefault(j, []).append(k)
    both = mo = to = 0
    wperr = []
    for i, (gt, gx, gy, dist) in enumerate(grants):
        if dist <= 1.0:
            continue
        j = bisect.bisect_right(ev_ts, gt)
        w1 = ev_ts[j] if j < len(ev_ts) else end
        gr = round(gt * 1000.0) / 1000.0
        mf = [f for f in fires if gr - 0.0005 <= f[0] < w1 - 0.0005]
        tl = owner.get(i, [])
        if mf and tl:
            both += 1
            wperr.append(math.hypot(mf[0][1][0] - legs[tl[0]][1][0], mf[0][1][1] - legs[tl[0]][1][1]))
        elif mf:
            mo += 1
        elif tl:
            to += 1
    ng = sum(1 for g in grants if g[3] > 1.0)
    # the frame
    run = N.Run(name, tape, cap)
    ws = [w for w, _ in trace]

    def mirror_at(t):
        i = bisect.bisect_right(ws, t)
        return trace[i - 1][1] if i > 0 else trace[0][1]
    rts = [r[0] for r in run.reps]

    def hybrid_at(t):
        i = bisect.bisect_right(rts, t)
        if i > 0 and run.reps[i - 1][2]:
            return run.reps[i - 1][1]
        return mirror_at(t)
    w1s = [(s["w"] - run.t0, s["w0"], s["v0"]) for s in run.s1]
    at_halt = []
    for ht, _pt in run.halts:
        tw = N.interp([(w, p) for w, p, v in w1s], ht)
        if tw is not None:
            at_halt.append(N.dist(hybrid_at(ht), tw))
    moving = [N.dist(mirror_at(t), w0) for t, w0, v in w1s if v > 5]
    return dict(name=name, grants=ng, both=both, model_only=mo, tape_only=to, halts=len(halts),
                wperr=wperr, at_halt=at_halt, moving=moving)


def q(v, f):
    v = sorted(v)
    return v[min(int(f * len(v)), len(v) - 1)] if v else float("nan")


def main(argv):
    if "--no-avoid" in argv:
        am.MIRROR_AVOID = False
    P = dict(grants=0, both=0, model_only=0, tape_only=0, halts=0)
    wp, at_halt, moving = [], [], []
    for name, tape, cap in RUNS:
        if not (os.path.exists(tape) and os.path.exists(cap)):
            print("%-10s SKIPPED: tape or capture missing" % name)
            continue
        r = score_run(name, tape, cap)
        print("%-10s grants %3d | both %2d model-only %2d tape-only %2d | halts %2d | hybrid@halt p50 %5.1f p90 %5.1f (n=%d) | mirror vs world-0 moving p50 %5.1f p90 %5.1f max %5.1f" % (
            name, r["grants"], r["both"], r["model_only"], r["tape_only"], r["halts"],
            statistics.median(r["at_halt"]) if r["at_halt"] else float("nan"), q(r["at_halt"], 0.9), len(r["at_halt"]),
            statistics.median(r["moving"]), q(r["moving"], 0.9), max(r["moving"])))
        for k in P:
            P[k] += r[k]
        wp.extend(r["wperr"]); at_halt.extend(r["at_halt"]); moving.extend(r["moving"])
    print("POOLED (avoid %s): grants %d | both %d model-only %d tape-only %d | halts %d | waypoint error p50 %.1f p90 %.1f max %.1f (n=%d)" % (
        "ON" if am.MIRROR_AVOID else "OFF", P["grants"], P["both"], P["model_only"], P["tape_only"], P["halts"],
        statistics.median(wp) if wp else 0.0, q(wp, 0.9) if wp else 0.0, max(wp) if wp else 0.0, len(wp)))
    print("  mirror vs the client's world-0 while MOVING: p50 %.1f p90 %.1f max %.1f (n=%d) | the hybrid frame at the halts: p50 %.1f p75 %.1f p90 %.1f max %.1f (n=%d)" % (
        statistics.median(moving), q(moving, 0.9), max(moving), len(moving),
        statistics.median(at_halt), q(at_halt, 0.75), q(at_halt, 0.9), max(at_halt), len(at_halt)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
