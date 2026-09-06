#!/usr/bin/env python3
"""How far is the SERVER's copy of a hostile from the copy the CLIENT holds? (NPCTRACK)

    python studies/npctrack/review/npcdrift.py                      # the three pinned stairs tapes
    python studies/npctrack/review/npcdrift.py <agenttap.jsonl>     # score one run (RUN-NPCTRACK-R1)
    python studies/npctrack/review/npcdrift.py <agenttap.jsonl> <gamesrv.jsonl>
    python studies/npctrack/review/npcdrift.py <agenttap.jsonl> --control   # the revert arm's inverted bars

THE QUANTITY. At every 0x0028 halt the server sent agent 10, the halt's own label
carries the server's copy of the body ("agent 10 halts at (x,y)"), and the agenttap
tape carries BOTH client copies of it (world 0, the sync copy our messages write;
world 1, the drawn body) read through the client's own accessor (w0score.live).
Their distance at the halt, and 0.5 s later once the body has settled, is the drift.
Nothing here is dead-reckoned by us: the server's number is what it printed, the
client's is what it held.

WHAT IT PRINTS, per run and pooled (studies/npctrack/FINDINGS.md):
  F1  the drift at the halts: server copy vs the drawn body and vs the sync copy
  F2  the client's own two copies of the hostile against each other
  F3  which stop rule the client's copy obeyed (AT-DISC / AT-POINT / NEITHER), and
      whether it was still walking when our halt landed
  F4  the CLIENT'S OWN MODEL -- agtrack_mirror.SyncAgent fed with the hostile's own
      grants, plus ANIMREF 38.2's disc stop -- replayed against the tape's sync copy
  F5  the same model in each FRAME the server could use for the disc

TWO GUARDS, because a run that measured nothing failed:
  * EXPOSURE -- fewer than FLOOR_HALTS halts or FLOOR_SAMPLES ok samples per agent
    is a REFUSAL, printed as such, never a flattering zero.
  * THE POSITIVE CONTROL, pinned-tape mode -- the model in the TRUE frame must
    reproduce the client's sync copy to <= CONTROL_MODEL_P50 at the halts, and the
    shipped-before-Q1 integrator (the halt labels on those tapes) must sit >=
    CONTROL_TODAY_P50 from it. A scorer that cannot reproduce the known before-
    picture cannot be trusted on the after; exit 1.

Read-only. Stdlib only. Needs the vault (the tapes and captures are personal data
and stay there).
"""
import bisect
import collections
import glob
import json
import math
import os
import statistics
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/clientscan", "toolkit/authsrv", "toolkit/mapdata"):
    sys.path.insert(0, os.path.join(REPO, sub))

import w0score as W                 # noqa: E402
import agtrack_mirror as am         # noqa: E402
import agtrack_replay as AR         # noqa: E402
import movesync                     # noqa: E402
import vaultpath                    # noqa: E402

AGENT = 10
STOP = 80.0                     # follow_stop_radius(): r + r + 56, ANIMREF 38.2
COS_CONE = 0.5                  # the resolver's +-60 degree cone, fcomp [0x009458BC]
PRUNE_MS = 3000                 # the live guard's reader-2 stand-in (agtrack_guard)
FLOOR_HALTS = 8
FLOOR_SAMPLES = 200
CONTROL_MODEL_P50 = 20.0        # F4 measured 11.6 u pooled; 12.0 / 10.7 / 13.7 per run
CONTROL_TODAY_P50 = 40.0        # F1 measured 53.8 u pooled; 63.3 / 47.9 / 56.0 per run
OVER = 40.0                     # "a halt over 40 u" -- the tally that names the tail

# The three scripted stairs runs the arc was opened on. Same route, same map, same
# harness, same client build; only the server between them (1z-bz/1z-by, then
# GROUNDZ-F9).
PINNED = [
    ("1zCA", "research/movecode/1zca-agenttap.jsonl",
     "captures/gamesrv/authsrv-20260905T233210-c1.jsonl"),
    ("GROUNDZ-R1", "research/renderobj/r1-agenttap.jsonl",
     "captures/gamesrv/authsrv-20260906T013213-c1.jsonl"),
    ("GROUNDZ-R2", "research/renderobj/r2-agenttap.jsonl",
     "captures/gamesrv/authsrv-20260906T024050-c1.jsonl"),
]

HALT_RE = __import__("re").compile(r"agent (\d+) halts at \((-?\d+),(-?\d+)\)")
FOLLOW_RE = __import__("re").compile(
    r"FOLLOW(?: re-path)?: agent (\d+) -> player at \((-?\d+),(-?\d+)\)")


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------

def dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def q(vals, f):
    v = sorted(vals)
    return v[min(int(f * len(v)), len(v) - 1)] if v else float("nan")


def nearest(ser, w, after=0.0):
    ws = [s["w"] for s in ser]
    i = bisect.bisect_left(ws, w + after)
    if i >= len(ser):
        return ser[-1]
    if i > 0 and abs(ws[i - 1] - (w + after)) < abs(ws[i] - (w + after)):
        return ser[i - 1]
    return ser[i]


def interp(samples, t):
    """samples: sorted (t, (x, y)); linear between, clamped at the ends."""
    ts = [s[0] for s in samples]
    i = bisect.bisect_left(ts, t)
    if i == 0:
        return samples[0][1]
    if i >= len(samples):
        return samples[-1][1]
    (t0, p0), (t1, p1) = samples[i - 1], samples[i]
    f = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
    return (p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f)


def cap_t0(rows):
    for r in rows:
        if "wall_unix" in r and "t" in r:
            return r["wall_unix"] - r["t"]
    return None


def npc_events(rows, agent_id=AGENT):
    """[(t, kind, data)] for one NPC, decoded from the sent rows' own bytes:
    0x002A = agent u32, x f32, y f32, plane u16 x2, target u32; 0x0029 the same
    without the target; 0x0028 = agent; 0x002B = agent, rate f32."""
    ev = []
    for r in rows:
        if r.get("kind") != "sent":
            continue
        try:
            b = bytes.fromhex(r.get("plain") or "")
        except ValueError:
            continue
        op = r.get("opcode")
        if len(b) < 6 or struct.unpack_from("<I", b, 2)[0] != agent_id:
            continue
        t = r["t"]
        if op == 0x2A and len(b) >= 22:
            x, y = struct.unpack_from("<ff", b, 6)
            p1, p2 = struct.unpack_from("<HH", b, 14)
            ev.append((t, "grant", (x, y, p1, p2, 0x2A)))
        elif op == 0x29 and len(b) >= 18:
            x, y = struct.unpack_from("<ff", b, 6)
            p1, p2 = struct.unpack_from("<HH", b, 14)
            ev.append((t, "grant", (x, y, p1, p2, 0x29)))
        elif op == 0x28:
            ev.append((t, "halt", None))
        elif op == 0x2B and len(b) >= 10:
            ev.append((t, "speed", struct.unpack_from("<f", b, 6)[0]))
    ev.sort(key=lambda e: e[0])
    return ev


class Run(object):
    def __init__(self, name, tape, cap):
        self.name = name
        self.head, rows = W.load(tape)
        self.s1 = W.series(self.head, rows, 1)
        self.s10 = W.series(self.head, rows, AGENT)
        self.rows = W.load_gamesrv(cap)
        self.t0 = cap_t0(self.rows)
        self.ev = npc_events(self.rows)
        self.halts = []            # (capture t, label point)
        self.follows = []          # (capture t, payload)
        self.ours = []             # (capture t, the server's player copy)
        self.reps = []             # (capture t, reported, was_stop)
        for r in self.rows:
            k = r.get("kind")
            if k == "sent":
                lab = r.get("label") or ""
                m = HALT_RE.search(lab)
                if m and int(m.group(1)) == AGENT:
                    self.halts.append((r["t"], (float(m.group(2)), float(m.group(3)))))
                m = FOLLOW_RE.search(lab)
                if m and int(m.group(1)) == AGENT:
                    self.follows.append((r["t"], (float(m.group(2)), float(m.group(3)))))
                    self.ours.append((r["t"], (float(m.group(2)), float(m.group(3)))))
            elif k == "position_report" and r.get("accepted"):
                if r.get("ours"):
                    self.ours.append((r["t"], tuple(r["ours"])))
                self.reps.append((r["t"], tuple(r["reported"]), r.get("source") == "0x0047"))
        self.ours.sort()
        self.reps.sort()
        self._mirror = None

    def ok(self):
        why = []
        if len(self.s1) < FLOOR_SAMPLES or len(self.s10) < FLOOR_SAMPLES:
            why.append("tape samples player %d / hostile %d, floor %d"
                       % (len(self.s1), len(self.s10), FLOOR_SAMPLES))
        if len(self.halts) < FLOOR_HALTS:
            why.append("halts %d, floor %d" % (len(self.halts), FLOOR_HALTS))
        if self.t0 is None:
            why.append("capture has no wall clock")
        return why

    # the three frames the server could compute, plus the truth
    def w0_at(self, t):
        return interp([(s["w"] - self.t0, s["w0"]) for s in self.s1], t)

    def srv_at(self, t):
        return interp(self.ours, t)

    def mirror_at(self, t):
        if self._mirror is None:
            self._mirror = mirror_trace(self.rows, self.reps)
        ws = [w for w, _ in self._mirror]
        i = bisect.bisect_right(ws, t)
        return self._mirror[i - 1][1] if i > 0 else self._mirror[0][1]

    def hybrid_at(self, t):
        rts = [r[0] for r in self.reps]
        i = bisect.bisect_right(rts, t)
        if i > 0 and self.reps[i - 1][2]:
            return self.reps[i - 1][1]
        return self.mirror_at(t)


def mirror_trace(rows, reps):
    """The AgTrack mirror replayed from the capture (agtrack_replay's own
    driver), seeded from the first accepted report the way the live guard is
    seeded by placement. -> [(capture t, (x, y))]."""
    import tempfile
    # agtrack_replay reads a PATH; hand it the rows it already parsed.
    tmp = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False,
                                      encoding="utf-8")
    try:
        for r in rows:
            tmp.write(json.dumps(r) + "\n")
        tmp.close()
        events, _fid = AR.load_events(tmp.name)
        reports, _w, _s = movesync.load_wire_reports(tmp.name)
    finally:
        os.unlink(tmp.name)
    atrack = AR.AsyncTrack(reports)
    mirror = am.AgTrackMirror(mesh=None, prune_ms=PRUNE_MS)
    ms = lambda t: int(round(t * 1000.0))   # noqa: E731
    trace = []
    last_ms = None
    if reps:
        t, p, _ = reps[0]
        mirror.sync.set_position(p[0], p[1], 0, ms(t))
        last_ms = ms(t)
    cur_plane = None
    for t, kind, data in events:
        now = ms(t)
        if last_ms is None:
            last_ms = now
        while last_ms + AR.TICK_MS <= now:
            last_ms += AR.TICK_MS
            mirror.tick(last_ms, atrack.at(last_ms / 1000.0))
            p = mirror.sync.position(last_ms)
            if p:
                trace.append((last_ms / 1000.0, p))
        apos = atrack.at(t)
        if kind == "grant":
            x, y, pa, pb, op = data
            mirror.on_grant(x, y, pa, pb, now, async_pos=apos, opcode=op)
        elif kind == "setpos":
            x, y, plane = data
            mirror.on_update_position(x, y, plane, now)
        elif kind == "speed":
            mirror.on_speed(data, now)
        elif kind == "heading":
            x, y, plane, hx, hy, mtype = data
            cur_plane = plane if plane is not None else cur_plane
            mirror.on_player_command(now, (x, y), plane,
                                     ("head", round(hx, 1), round(hy, 1), mtype))
        elif kind == "stop":
            x, y, plane = data
            cur_plane = plane if plane is not None else cur_plane
            mirror.on_player_command(now, (x, y), plane, ("stop",))
        elif kind == "click":
            x, y, dplane = data
            pos = apos if apos is not None else (x, y)
            speed = 288.0 * mirror.sync.move_speed
            d = math.hypot(x - pos[0], y - pos[1])
            arrive = now + max(int(d * 1000.0 / speed), 1) if speed > 0 else 0
            mirror.on_player_command(now, pos, cur_plane,
                                     ("click", round(x, 1), round(y, 1)),
                                     dest=(x, y, dplane), arrive_t=arrive)
        p = mirror.sync.position(now)
        if p:
            trace.append((now / 1000.0, p))
        last_ms = max(last_ms, now)
    trace.sort()
    return trace


# ---------------------------------------------------------------------------
# F4: the client's own model of its sync copy
# ---------------------------------------------------------------------------

def in_cone(sa, p, pl):
    vx, vy = sa.vx, sa.vy
    sp = math.hypot(vx, vy)
    dx, dy = pl[0] - p[0], pl[1] - p[1]
    d = math.hypot(dx, dy)
    if sp <= 0.0 or d <= 1e-9:
        return True
    return (vx * dx + vy * dy) / (sp * d) >= COS_CONE


def replay_model(ev, seed_xy, seed_t, sample_ts, frame_of=None, tick=0.01):
    """agtrack_mirror.SyncAgent over the hostile's own events, sampled at
    sample_ts (capture seconds). frame_of(t) -> the player position the disc
    runs against, or None for no disc (the DR-only arm). -> (positions, stops)."""
    sa = am.SyncAgent()
    ms = lambda t: int(round(t * 1000.0))   # noqa: E731
    sa.set_position(seed_xy[0], seed_xy[1], 0, ms(seed_t))
    out, stops = [], []
    moving = False
    t, ei, si = seed_t, 0, 0
    while si < len(sample_ts):
        while ei < len(ev) and ev[ei][0] <= t:
            et, kind, data = ev[ei]
            ei += 1
            if kind == "grant":
                x, y, p1, p2, _op = data
                sa.consume_arrival(ms(et))
                sa.bake_grant(x, y, p1, p2, ms(et))
                moving = True
            elif kind == "halt":
                p = sa.position(ms(et)) or (sa.x78, sa.y78)
                sa.set_position(p[0], p[1], sa.plane or 0, ms(et))
                moving = False
            elif kind == "speed":
                sa.move_speed = float(data)
        if sa.consume_arrival(ms(t)):
            moving = False
        if moving and frame_of is not None:
            p = sa.position(ms(t))
            pl = frame_of(t)
            if p is not None and pl is not None and dist(p, pl) <= STOP \
                    and in_cone(sa, p, pl):
                sa.set_position(p[0], p[1], sa.plane or 0, ms(t))
                moving = False
                stops.append(t)
        while si < len(sample_ts) and sample_ts[si] <= t:
            out.append(sa.position(ms(sample_ts[si])))
            si += 1
        t += tick
    return out, stops


# ---------------------------------------------------------------------------
# scoring
# ---------------------------------------------------------------------------

def score(run):
    """-> dict of per-halt lists, printed as it goes."""
    R = collections.defaultdict(list)
    head, s1, s10 = run.head, run.s1, run.s10
    print("\n=== %s: tape %d/%d samples, %d halts, %d follow orders, %d NPC events"
          % (run.name, len(s1), len(s10), len(run.halts), len(run.follows), len(run.ev)))

    # F1 / F2 / F3 -- straight off the labels and the tape
    for h, cpos in run.halts:
        hw = run.t0 + h
        a0 = nearest(s10, hw)
        a1 = nearest(s10, hw, after=0.5)
        p1 = nearest(s1, hw, after=0.5)
        R["copy_vs_drawn"].append(dist(cpos, a1["body"]))
        R["copy_vs_sync"].append(dist(cpos, a1["w0"]))
        # THE SAME INSTANT (F9). The registered metric above reads the client
        # 0.5 s after the halt, which was fair on the corridor integrator
        # (the hostile then stood in reach and swung) and is NOT fair under
        # the client model, whose halt is followed by a fresh follow 0.05 s
        # later whenever the player kept moving: RUN-R1 read 76.6 u on the
        # registered metric and 11.8 u at the same instant, with the client
        # walking within 0.5 s of 17 of its 23 halts. Both are printed; the
        # walking count is the confound's own witness.
        R["copy_vs_sync_now"].append(dist(cpos, a0["w0"]))
        R["client_walks_after"].append(bool(a1["v0"] > 5.0
                                            or dist(a0["w0"], a1["w0"]) > 20.0))
        R["sync_vs_drawn"].append(dist(a1["w0"], a1["body"]))
        s2s = dist(a1["w0"], p1["w0"])
        lastf = [f for f in run.follows if f[0] <= h]
        pay = lastf[-1][1] if lastf else (float("nan"), float("nan"))
        hs_pay = dist(a1["w0"], pay)
        R["rule"].append("AT-DISC" if 68 <= s2s <= 92 else
                         "AT-POINT" if hs_pay < 12 else "NEITHER")
        R["drawn_vs_player"].append(dist(a1["body"], p1["body"]))
        # was the sync copy still walking at the last sample before the halt
        i = bisect.bisect_left([s["w"] for s in s10], hw) - 1
        R["moving_at_halt"].append(bool(i >= 0 and s10[i]["v0"] > 5.0))
    cvs = R["copy_vs_sync"]
    now = R["copy_vs_sync_now"]
    print("  F9 the same at the halt's OWN instant:            vs SYNC p50 %5.1f p75 %5.1f p90 %6.1f max %6.1f | over %.0f u: %d/%d | client walking within 0.5 s of the halt: %d/%d"
          % (statistics.median(now), q(now, .75), q(now, .9), max(now), OVER,
             sum(1 for x in now if x > OVER), len(now), sum(R["client_walks_after"]), len(now)))
    parks = [r for r in run.rows if r.get("kind") == "npc_model" and r.get("act") == "disc"]
    if parks:
        pd = [dist(p["at"], nearest(s10, run.t0 + p["t"])["w0"]) for p in parks]
        holds = sum(1 for r in run.rows if r.get("kind") == "npc_model" and r.get("act") == "hold")
        R["park_vs_sync"] = pd
        print("  F9 the model's own disc parks (npc_model rows) vs the client's sync copy at that instant: n=%d p50 %5.1f p90 %5.1f max %5.1f; holds %d"
              % (len(pd), statistics.median(pd), q(pd, .9), max(pd), holds))
    print("  F1 server copy vs client at the halt (settled):  vs DRAWN p50 %5.1f p90 %6.1f max %6.1f | vs SYNC p50 %5.1f p75 %5.1f p90 %6.1f max %6.1f | over %.0f u: %d/%d"
          % (statistics.median(R["copy_vs_drawn"]), q(R["copy_vs_drawn"], .9), max(R["copy_vs_drawn"]),
             statistics.median(cvs), q(cvs, .75), q(cvs, .9), max(cvs), OVER,
             sum(1 for x in cvs if x > OVER), len(cvs)))
    print("  F2 the client's own two copies of the hostile:   max %.1f u, over 12 u on %d/%d"
          % (max(R["sync_vs_drawn"]), sum(1 for x in R["sync_vs_drawn"] if x > 12), len(cvs)))
    c = collections.Counter(R["rule"])
    print("  F3 stop rule: %s; sync copy still walking at the halt: %d/%d; drawn hostile -> drawn player p50 %.1f u (the disc is 80)"
          % (dict(c), sum(R["moving_at_halt"]), len(cvs), statistics.median(R["drawn_vs_player"])))

    # F4 / F5 -- the client's own model, in each frame
    ts = [s["w"] - run.t0 for s in s10]
    truth = [s["w0"] for s in s10]
    frames = [("DR-only", None), ("truth(w0)", run.w0_at), ("hybrid", run.hybrid_at),
              ("mirror", run.mirror_at), ("state[pos]", run.srv_at)]
    halt_ts = [h for h, _ in run.halts]
    for fname, ff in frames:
        pos, stops = replay_model(run.ev, s10[0]["w0"], ts[0], ts, ff)
        e = [dist(p, t) if p else float("nan") for p, t in zip(pos, truth)]
        eh = []
        for h in halt_ts:
            i = bisect.bisect_left(ts, h + 0.5)
            eh.append(e[i] if i < len(e) and e[i] == e[i] else float("nan"))
        eh = [x for x in eh if x == x]
        e_all = [x for x in e if x == x]
        R["model:" + fname] = eh
        tag = "F4" if fname in ("DR-only", "truth(w0)") else "F5"
        print("  %s model[%-10s] vs client sync: all p50 %5.1f p90 %6.1f | at halts p50 %5.1f p75 %5.1f p90 %6.1f max %6.1f | over %.0f u: %d/%d | disc stops %d"
              % (tag, fname, statistics.median(e_all), q(e_all, .9),
                 statistics.median(eh), q(eh, .75), q(eh, .9), max(eh), OVER,
                 sum(1 for x in eh if x > OVER), len(eh), len(stops)))
    return R


def pooled(results):
    P = collections.defaultdict(list)
    for R in results:
        for k, v in R.items():
            if k in ("rule", "moving_at_halt", "client_walks_after"):
                P[k].extend(v)
            elif isinstance(v, list) and v and isinstance(v[0], float):
                P[k].extend(v)
    n = len(P["copy_vs_sync"])
    print("\nPOOLED over %d halts" % n)
    print("  %-22s %6s %6s %6s %6s  %s" % ("server copy vs SYNC", "p50", "p75", "p90", "max", "over 40 u"))
    for k in ("copy_vs_sync", "copy_vs_sync_now", "copy_vs_drawn", "model:truth(w0)", "model:hybrid",
              "model:mirror", "model:state[pos]", "model:DR-only"):
        v = P[k]
        if v:
            print("  %-22s %6.1f %6.1f %6.1f %6.1f  %d/%d" % (
                k, statistics.median(v), q(v, .75), q(v, .9), max(v),
                sum(1 for x in v if x > OVER), len(v)))
    print("  stop rules %s; still walking at the halt %d/%d; sync-vs-drawn over 12 u %d/%d; client walking within 0.5 s of the halt %d/%d"
          % (dict(collections.Counter(P["rule"])), sum(P["moving_at_halt"]), n,
             sum(1 for x in P["sync_vs_drawn"] if x > 12), n, sum(P["client_walks_after"]), n))
    return P


def main(argv):
    control = "--control" in argv
    argv = [a for a in argv if a != "--control"]
    if len(argv) >= 2:
        tape = argv[1]
        head, rows = W.load(tape)
        cap = argv[2] if len(argv) >= 3 else W.find_gamesrv(head, rows)
        if cap is None:
            print("REFUSED: no gamesrv capture overlaps this tape's wall span; pass it explicitly")
            return 2
        run = Run(os.path.basename(tape), tape, cap)
        why = run.ok()
        if why:
            print("REFUSED (%s): %s -- zero trials, not a null" % (run.name, "; ".join(why)))
            return 2
        R = score(run)
        v = R["copy_vs_sync"]
        p50 = statistics.median(v)
        frac = sum(1 for x in v if x > OVER) / float(len(v))
        cut = sum(R["moving_at_halt"]) / float(len(v))
        walks = sum(R["client_walks_after"])
        print("\nRUN-NPCTRACK-R1 verdicts (registered predictions, studies/npctrack/RUN-R1.md):")
        print("  P1 copy-vs-client-sync 0.5 s AFTER the halt p50 %.1f u  -> %s (bar <= 30; the three pinned runs measured 63.3 / 47.9 / 56.0)"
              % (p50, "MET" if p50 <= 30.0 else "REFUTED"))
        print("  P2 halts over %.0f u on that metric: %.0f%%  -> %s (bar <= 30%%; pinned 65%%)"
              % (OVER, 100 * frac, "MET" if frac <= 0.30 else "REFUTED"))
        if walks:
            print("     CONFOUND: the client copy was walking within 0.5 s of %d of %d halts -- a halt followed by a fresh follow; that metric reads the walk, not the drift (F9)" % (walks, len(v)))
        print("  P3 client copy still walking when the halt landed: %.0f%%  -> %s (bar <= 15%%; pinned 25%%)"
              % (100 * cut, "MET" if cut <= 0.15 else "REFUTED"))
        now = R["copy_vs_sync_now"]
        p50n = statistics.median(now)
        fracn = sum(1 for x in now if x > OVER) / float(len(now))
        if control:
            # THE CONTROL ARM (--no-npc-client-model) must come out RED on the
            # instant metric, or the scorer -- not the fix -- is what the run
            # convicted (RUN-R1.md, RE-REGISTERED).
            print("  CONTROL ARM (--no-npc-client-model): the bars are inverted -- this arm must reproduce the old drift")
            print("  P1' same-instant p50 %.1f u  -> %s (bar >= 40; the pinned runs 59.3 / 45.7 / 68.0)"
                  % (p50n, "MET" if p50n >= 40.0 else "REFUTED -- the scorer is suspect"))
            print("  P2' halts over %.0f u at that instant: %.0f%%  -> %s (bar >= 50%%; pinned 26 of 40)"
                  % (OVER, 100 * fracn, "MET" if fracn >= 0.50 else "REFUTED -- the scorer is suspect"))
            print("  P3' halts on a walking client copy: %.0f%%  -> %s (bar >= 20%%; pinned 25%%)"
                  % (100 * cut, "MET" if cut >= 0.20 else "REFUTED"))
            return 0
        print("  P1' copy-vs-client-sync at the halt's OWN instant p50 %.1f u  -> %s (bar <= 30; the pinned runs on this metric 59.3 / 45.7 / 68.0)"
              % (p50n, "MET" if p50n <= 30.0 else "REFUTED"))
        print("  P2' halts over %.0f u at that instant: %.0f%%  -> %s (bar <= 30%%; pinned 26 of 40)"
              % (OVER, 100 * fracn, "MET" if fracn <= 0.30 else "REFUTED"))
        return 0

    try:
        vault = vaultpath.vault_path()
    except Exception as ex:                                  # noqa: BLE001
        print("REFUSED: no vault (%s) -- the pinned tapes live there" % ex)
        return 2
    results, refused = [], []
    for name, tape, cap in PINNED:
        tp, cp = os.path.join(vault, tape), os.path.join(vault, cap)
        if not (os.path.exists(tp) and os.path.exists(cp)):
            refused.append("%s: missing %s" % (name, tape if not os.path.exists(tp) else cap))
            continue
        run = Run(name, tp, cp)
        why = run.ok()
        if why:
            refused.append("%s: %s" % (name, "; ".join(why)))
            continue
        results.append(score(run))
    for r in refused:
        print("  REFUSED", r)
    if not results:
        print("REFUSED: no pinned run could be scored -- zero trials")
        return 2
    P = pooled(results)
    model = statistics.median(P["model:truth(w0)"])
    today = statistics.median(P["copy_vs_sync_now"])
    ok_model = model <= CONTROL_MODEL_P50
    ok_today = today >= CONTROL_TODAY_P50
    print("\nPOSITIVE CONTROL: the client's own model in the TRUE frame reproduces the client's copy to p50 %.1f u (bar <= %.0f) -> %s;"
          % (model, CONTROL_MODEL_P50, "PASS" if ok_model else "FAIL"))
    print("                  the pre-Q1 integrator sits p50 %.1f u from it (bar >= %.0f) -> %s"
          % (today, CONTROL_TODAY_P50, "PASS" if ok_today else "FAIL"))
    if not (ok_model and ok_today):
        print("A scorer that cannot reproduce the before-picture cannot be trusted on the after.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
