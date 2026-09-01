"""pressscore.py -- why was each attack press (not) answered, on a capture.

    python toolkit/authsrv/pressscore.py                     # newest gamesrv capture
    python toolkit/authsrv/pressscore.py CAP.jsonl [CAP...]  # named captures
    python toolkit/authsrv/pressscore.py --section36         # the three captures
                                                             # FINDINGS section 36 scored
    options: --speed U/s (288)  --bound S (3.0)  --interval S (1.75)  --verbose

WHY THIS EXISTS. ANIMREF-RE section 36 is a correction: a fix for the
operator's "spacebar after a click-walk does nothing" was shipped on a unit
test written against the same hypothesis, reported as done, and the
operator's next run still had the bug. The rule that came out of it --
"measure the symptom on the wire in their post-fix capture before writing
the word fixed" -- needs an instrument, and this is it. It reads a gamesrv
capture, finds every c2s 0x0026 ATTACK press, says what the last movement
input was (CLICK 0x003E / STOP 0x0047 / WASD 0x003D), whether a server
attack_started answered it within the window, and -- by replaying the
server's own attack rules tick for tick from the c2s records -- WHICH GATE
refused every tick the press went unanswered. Then it forks the replayed
state at each press and scores the candidate bounds on the click latch
against each other, in BOTH directions (newly answered / newly refused /
opened while the modelled leg was still walking).

WHAT IS REPLAYED, AND THE CONTROL THAT KEEPS IT HONEST. The replay is a
transcription of begin_attack, cancel_on_move (the landing split),
_player_body_moving and attack_tick as they stood on 2026-09-01, driven at
the capture's own WORLD_SIMULATION_TICK instants. It is two of our own
components agreeing -- so it earns nothing by itself. What it earns is the
REPLAY CONTROL printed for every capture: the replayed attack_started and
attack_stopped instants must match the ones on the wire (all three
2026-09-01 captures: 52/52, 23/23, 11/11 starts; 27/27, 7/7, 1/1 stops,
within 0.12 s). A capture whose control does not close was produced by
rules this file does not transcribe, and every fork below it is then a
story; the tool says so rather than printing the numbers anyway.

THE LEG MODEL is the server's (authsrv._click_leg_arm): a click walks a
straight line from where the model puts the body -- the last report, or the
previous leg interpolated when the client has been silent since it -- to
the clicked point at `--speed`. It is a RECONSTRUCTION and the tool scores
it: every first report after a click that the model calls "arrived" is
compared to the click destination (10 of 10 within 3.5 u on the three
captures), and the in-flight ones give the residual against the model
position (n=1 clean, 284 u/s). The straight line is a lower bound on the
path the client walks; the caveat lives at _click_leg_arm.

DENOMINATORS, named once. "press" = every decoded c2s opcode 38; "last
input" = the most recent c2s 0x003E/0x0047/0x003D before it (0x003D of any
movementType -- every one in the corpus carries 1..8); "answered" = any
server attack_started within `--bound` seconds after the press, the section
36 scorer, which credits a chain swing that would have opened anyway. The
per-press rows are what tell those apart. Read-only; standard library only.
"""
import copy
import glob
import json
import math
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                ".."))
import vaultpath  # noqa: E402

SECTION36 = [
    # (tag, file, headline the section printed: CLICK a/n, STOP a/n, WASD a/n)
    ("12:59", "authsrv-20260901T125928-c1.jsonl", (18, 54, 39, 42, 5, 5)),
    ("14:32", "authsrv-20260901T143249-c1.jsonl", (20, 33, 10, 11, 2, 4)),
    ("15:17", "authsrv-20260901T151738-c1.jsonl", (13, 23, 7, 7, 0, 0)),
]
DEFAULT_SPEED = 288.0       # authsrv.DEFAULT_RUN_SPEED, the declared base
DEFAULT_BOUND = 3.0         # authsrv.GRANT_LOCAL_WINDOW, section 34's constant
DEFAULT_INTERVAL = 1.75     # the hammer; --interval for anything else
ATTACK_RANGE = 1500.0       # authsrv.ATTACK_RANGE (ours; unmeasured)
PLAYER = 1                  # authsrv.PLAYER_AGENT_ID
OP_TICK, OP_CREATE, OP_STARTED, OP_STOPPED, OP_E3 = 30, 32, 160, 159, 227
MODES = [("P0", "window", 0.0), ("P1", "leg", 0.0), ("P1.5", "leg", 0.5),
         ("P2", "press_ends", 0.0), ("F2", "window:reset", 0.0),
         ("P1+F2", "leg:reset", 0.0)]
CLS = {61: "WASD", 62: "CLICK", 71: "STOP"}


# ----------------------------------------------------------------- loading
def load(path):
    """(flags, events, spawns). events = [(t, order, kind, payload)], kinds:
    c2s (decoded record), tick, wire_started, wire_stopped, kill, revive,
    e3. spawns = {agent_id: (x, y)} from the WORLD_CREATE_AGENT frames,
    decoded through the schema codec so the layout is the catalog's."""
    from schema import codec as _codec
    cod = _codec.Codec()
    evs, spawns, flags = [], {}, None
    with open(path, encoding="utf-8") as fh:
        for i, line in enumerate(fh):
            try:
                r = json.loads(line)
            except ValueError:
                continue
            k = r.get("kind")
            if i == 1 and k not in ("decoded", "sent"):
                flags = r
            t = r.get("t")
            if k == "decoded":
                if r.get("opcode") in (38, 61, 62, 71, 70):
                    evs.append((t, i, "c2s", r))
            elif k == "sent":
                op, lab = r.get("opcode"), r.get("label", "")
                if op == OP_TICK:
                    evs.append((t, i, "tick", None))
                elif op == OP_STARTED and lab.startswith("attack_started"):
                    evs.append((t, i, "wire_started", lab))
                elif op == OP_STOPPED and lab.startswith("attack_stopped"):
                    evs.append((t, i, "wire_stopped", lab))
                elif lab.startswith("KILL agent "):
                    evs.append((t, i, "kill", int(lab.split()[2])))
                elif lab.startswith("revive agent "):
                    evs.append((t, i, "revive", int(lab.split()[2])))
                elif op == OP_E3 and lab.startswith("SKILL_ACTIVATED("):
                    evs.append((t, i, "e3", lab))
                elif op == OP_CREATE and r.get("plain"):
                    try:
                        _op, vals, _n = cod.decode_one(
                            "GAME_SMSG", bytes.fromhex(r["plain"]))
                        # [hdr, agent, dword, byte, byte, (x, y), ...]
                        spawns.setdefault(int(vals[1]),
                                          (float(vals[5][0]),
                                           float(vals[5][1])))
                    except Exception:   # a frame the catalog cannot read
                        pass            # is a missing spawn, not a crash
    evs.sort(key=lambda e: (e[0], e[1]))
    return flags or {}, evs, spawns


def base_mode(flags):
    """Which click-latch bound produced the capture, from its own flags
    record. Pre-section-34 captures carry no SWING_HOLDS_WALK_GATE key (that
    flag and the 3.0 s bound landed the same afternoon), section 34/35
    captures carry it, and section 37 captures carry CLICK_LATCH_LEG_ETA."""
    if "CLICK_LATCH_LEG_ETA" in flags:
        return ("leg" if flags["CLICK_LATCH_LEG_ETA"] else "window",
                "CLICK_LATCH_LEG_ETA=%s" % flags["CLICK_LATCH_LEG_ETA"])
    if "SWING_HOLDS_WALK_GATE" in flags:
        return "window", "section 34/35 flags (no CLICK_LATCH_LEG_ETA key)"
    return "unbounded", "pre-section-34 flags (no SWING_HOLDS_WALK_GATE key)"


# ------------------------------------------------------------ leg model
class LegModel:
    """authsrv._click_leg_start / _click_leg_arm, offline: reports anchor
    the body; a click starts a straight leg from the model's position at
    that instant; silence keeps the model on the leg (and at its end)."""

    def __init__(self, anchor, speed):
        self.anchor = anchor
        self.speed = speed
        self.leg = None          # (t0, src, dst, eta_seconds)

    def pos(self, t):
        if self.leg is None:
            return self.anchor
        t0, src, dst, eta = self.leg
        if eta <= 0.0 or t >= t0 + eta:
            return dst
        f = (t - t0) / eta
        return (src[0] + (dst[0] - src[0]) * f, src[1] + (dst[1] - src[1]) * f)

    def report(self, t, xy):
        self.anchor = (float(xy[0]), float(xy[1]))
        self.leg = None

    def click(self, t, dst):
        src = self.pos(t)
        dst = (float(dst[0]), float(dst[1]))
        d = math.hypot(dst[0] - src[0], dst[1] - src[1])
        self.leg = (t, src, dst, d / self.speed if self.speed > 0 else 0.0)
        return src, d, self.leg[3]

    def in_flight(self, t):
        return self.leg is not None and t < self.leg[0] + self.leg[3]


# --------------------------------------------------------------- replay
# The server stamps a FRESH target's `player_last_swing` as 0.0 -- the epoch,
# against a wall clock near 1.7e9 -- so the interval gate can never refuse
# the first swing and the pause accumulation (`+= now - since`) stays
# negligible beside `now`. A capture's `t` starts near 0, so the literal 0.0
# would turn that epoch into "1.75 s into the session" and refuse presses the
# server answered. FRESH is the epoch's meaning, not its value.
FRESH = -1.0e12


def fresh_state(spawn):
    return {"kbd": None, "click": None, "click_eta": None, "attacking": None,
            "last_swing": FRESH, "pause_tick": None, "swing": None,
            "cancel": None, "pending_e3": False, "dead": set(), "pos": spawn}


def moving(st, t, mode, bound, slack=0.0):
    if st["kbd"] is not None:
        return True, "kbd"
    c = st["click"]
    if c is None:
        return False, None
    if mode == "unbounded":
        return True, "click"
    if mode == "window":
        return (t - c) <= bound, "click"
    if mode == "leg":
        return t < c + (st["click_eta"] or 0.0) + slack, "click"
    raise ValueError(mode)


def _cancel_on_move(st, t, out):
    chain_live = (st["attacking"] or st["swing"]) and not st["pending_e3"]
    pre = st["swing"] is not None and t < st["swing"]["lands_at"]
    if chain_live and pre:
        out.append(("stopped", t, "movement"))
        st["cancel"] = "movement"
    if st["attacking"] and pre:
        st["attacking"] = None


def apply_c2s(st, r, t, out, lm):
    op, v = r["opcode"], r["values"]
    if op == 61:
        mt = v[4] if len(v) > 4 else 0
        if mt:
            _cancel_on_move(st, t, out)
        st["kbd"] = t if mt else None
        st["click"] = None
        st["pos"] = (float(v[1][0]), float(v[1][1]))
        lm.report(t, v[1])
    elif op == 62:
        _cancel_on_move(st, t, out)
        st["click"] = t
        _src, _d, eta = lm.click(t, v[1])
        st["click_eta"] = eta
    elif op == 71:
        st["kbd"] = None
        st["click"] = None
        st["pos"] = (float(v[1][0]), float(v[1][1]))
        lm.report(t, v[1])
    elif op == 38:
        target = v[1]
        if target in st["dead"]:
            st["attacking"] = None
        elif st["attacking"] != target:
            if st["attacking"] and st["swing"]:
                out.append(("stopped", t, "retarget"))
                st["cancel"] = "retarget"
            st["attacking"] = target
            st["last_swing"] = FRESH
    elif op == 70:
        if (st["attacking"] or st["swing"]) and not st["pending_e3"]:
            out.append(("stopped", t, "skill press"))
            st["cancel"] = "skill press"
        st["pending_e3"] = True


def tick(st, t, out, mode, bound, interval, windup, spawns, slack=0.0):
    """One attack_tick. Returns the gate that refused, or OPEN."""
    if st["cancel"]:
        st["swing"], st["cancel"] = None, None
    mv, why = moving(st, t, mode, bound, slack)
    if not mv:
        st["pause_tick"] = None
    if not st["attacking"]:
        st["swing"] = None
        return "no-target"
    if st["attacking"] in st["dead"]:
        st["attacking"], st["swing"] = None, None
        return "target-dead"
    tp = spawns.get(st["attacking"])
    if tp is not None:
        px, py = st["pos"]
        if math.hypot(tp[0] - px, tp[1] - py) > ATTACK_RANGE:
            st["swing"] = None
            return "range"
    if mv:
        since = st["pause_tick"]
        if since is not None and t > since:
            st["last_swing"] += (t - since)
        st["pause_tick"] = t
    else:
        st["pause_tick"] = None
    if st["swing"] is not None:
        if t >= st["swing"]["lands_at"]:
            st["swing"] = None
            out.append(("landed", t, None))
        return "swing-armed"
    if st["pending_e3"]:
        return "pending-cast"
    if mv:
        return "moving:" + why
    if t - st["last_swing"] < interval:
        return "interval"
    st["last_swing"] = t
    out.append(("started", t, st["attacking"]))
    st["swing"] = {"target": st["attacking"], "lands_at": t + windup}
    return "OPEN"


def run_forward(st, lm, evs, start, t_end, mode, bound, interval, windup,
                spawns, out, slack=0.0):
    """Advance a forked state through evs[start:] until t_end. Returns
    (blockers, first_open_t, opened_while_leg_in_flight)."""
    blockers, first_open, open_inflight = [], None, None
    for t, _o, kind, payload in evs[start:]:
        if t > t_end:
            break
        if kind == "c2s":
            apply_c2s(st, payload, t, out, lm)
        elif kind == "tick":
            b = tick(st, t, out, mode, bound, interval, windup, spawns, slack)
            blockers.append((t, b))
            if b == "OPEN" and first_open is None:
                first_open, open_inflight = t, lm.in_flight(t)
        elif kind == "kill":
            st["dead"].add(payload)
        elif kind == "revive":
            st["dead"].discard(payload)
        elif kind == "e3":
            st["pending_e3"] = False
    return blockers, first_open, open_inflight


# --------------------------------------------------------------- scoring
def _p(xs, q):
    xs = sorted(xs)
    return xs[min(int(len(xs) * q), len(xs) - 1)] if xs else float("nan")


def _match(a, b, tol):
    used, m = set(), 0
    for x in a:
        for j, y in enumerate(b):
            if j not in used and abs(x - y) <= tol:
                used.add(j)
                m += 1
                break
    return m


def score(flags, evs, spawns, mode=None, speed=DEFAULT_SPEED,
          bound=DEFAULT_BOUND, interval=DEFAULT_INTERVAL, say=print,
          verbose=False):
    """Score one capture. Returns a dict of the headline numbers so a test
    can assert them; prints the report through `say`."""
    windup = 0.5 * interval - 0.1          # the windup LAW (FINDINGS R1)
    mode_why = "given"
    if mode is None:
        mode, mode_why = base_mode(flags)
    spawn = spawns.get(PLAYER, (0.0, 0.0))
    wire_started = [t for t, _o, k, _p_ in evs if k == "wire_started"]
    wire_stopped = [t for t, _o, k, _p_ in evs if k == "wire_stopped"]
    presses = [(i, t, r) for i, (t, _o, k, r) in enumerate(evs)
               if k == "c2s" and r["opcode"] == 38]
    moves = [(t, r) for t, _o, k, r in evs
             if k == "c2s" and r["opcode"] in (61, 62, 71)]
    res = {"mode": mode, "presses": len(presses),
           "wire_started": len(wire_started)}
    say(f"  base predicate: {mode} ({mode_why}); speed {speed:.0f} u/s; "
        f"bound {bound:.1f} s; interval {interval:.2f} s; presses "
        f"{len(presses)}; attack_started on the wire {len(wire_started)}")

    def last_input(tp):
        last = None
        for t, r in moves:
            if t < tp:
                last = (t, r)
            else:
                break
        return last

    def answered(tp):
        for ts in wire_started:
            if tp < ts <= tp + bound:
                return ts
        return None

    # -- the section 36 scorer ------------------------------------------
    n36, a36 = Counter(), Counter()
    for _i, tp, _r in presses:
        li = last_input(tp)
        c = "NONE" if li is None else CLS[li[1]["opcode"]]
        n36[c] += 1
        if answered(tp) is not None:
            a36[c] += 1
    say("  section 36 scorer (answered = attack_started within the bound), "
        "by last movement input:")
    for c in ("CLICK", "STOP", "WASD", "NONE"):
        if n36[c]:
            say(f"    {c:5s} {a36[c]:3d}/{n36[c]:3d} = {100.0 * a36[c] / n36[c]:5.1f} %")
        res[c] = (a36[c], n36[c])

    # -- the base replay, and its control -------------------------------
    st, lm, out, blockers_all, snaps, resid = (
        fresh_state(spawn), LegModel(spawn, speed), [], [], {}, [])
    for idx, (t, _o, kind, payload) in enumerate(evs):
        if kind == "c2s":
            if payload["opcode"] == 38:
                snaps[idx] = (copy.deepcopy(st), copy.deepcopy(lm))
            if payload["opcode"] in (61, 71) and lm.leg is not None:
                model, rep = lm.pos(t), payload["values"][1]
                resid.append((t, math.hypot(rep[0] - model[0],
                                            rep[1] - model[1]),
                              not lm.in_flight(t)))
            apply_c2s(st, payload, t, out, lm)
        elif kind == "tick":
            blockers_all.append((t, tick(st, t, out, mode, bound, interval,
                                         windup, spawns)))
        elif kind == "kill":
            st["dead"].add(payload)
        elif kind == "revive":
            st["dead"].discard(payload)
        elif kind == "e3":
            st["pending_e3"] = False
    rep_started = [t for k, t, _w in out if k == "started"]
    rep_stopped = [t for k, t, _w in out if k == "stopped"]
    m_started = _match(rep_started, wire_started, 0.12)
    m_stopped = _match(rep_stopped, wire_stopped, 0.12)
    res["control"] = (m_started, len(wire_started), len(rep_started),
                      m_stopped, len(wire_stopped), len(rep_stopped))
    control_ok = (m_started == len(wire_started) == len(rep_started))
    say(f"  REPLAY CONTROL: attack_started replayed {len(rep_started)} vs "
        f"wire {len(wire_started)}, matched within 0.12 s: {m_started}; "
        f"attack_stopped replayed {len(rep_stopped)} vs wire "
        f"{len(wire_stopped)}, matched: {m_stopped}"
        + ("" if control_ok else
           "  <<< THE CONTROL DOES NOT CLOSE: this capture was produced by "
           "rules this replay does not transcribe (a different flag set, "
           "weapon, or a later build). The forks below are NOT evidence."))
    arr = [x for x in resid if x[2]]
    fl = [x for x in resid if not x[2]]
    res["leg_control"] = (len(arr), max([x[1] for x in arr], default=0.0),
                          len(fl), _p([x[1] for x in fl], 0.5))
    say(f"  LEG-MODEL CONTROL: first report after a click -- model says "
        f"ARRIVED n={len(arr)}, max residual "
        f"{max([x[1] for x in arr], default=0.0):.1f} u; model says "
        f"IN-FLIGHT n={len(fl)}, residual p50 "
        f"{_p([x[1] for x in fl], 0.5):.1f} u")

    # -- per press --------------------------------------------------------
    rows = []
    say("  PER PRESS  (age: s since the last input; leg/eta: the modelled "
        "click leg; fl: in flight at the press; rep: repeat press on the "
        "target already set; lat: wire latency to attack_started; then the "
        "gates that refused in the window and the fork latencies)")
    say("    #     t    last   age  leg_u  eta  fl rep ans  lat   gates                                   "
        + " ".join(f"{m:>5s}" for m, _m, _s in MODES))
    for n, (idx, tp, r) in enumerate(presses, 1):
        st0, lm0 = snaps[idx]
        li = last_input(tp)
        c = "NONE" if li is None else CLS[li[1]["opcode"]]
        age = None if li is None else tp - li[0]
        leg_u = eta = fl_ = None
        if c == "CLICK" and lm0.leg is not None:
            leg_u, eta = lm0.leg[3] * speed, lm0.leg[3]
            fl_ = lm0.in_flight(tp)
        repeat = (st0["attacking"] == r["values"][1]
                  and r["values"][1] not in st0["dead"])
        ans = answered(tp)
        lat = None if ans is None else ans - tp
        gates = [b for t, b in blockers_all if tp < t <= tp + bound]
        gc = Counter(gates)
        first_gate = gates[0] if gates else "?"
        cf, cf_fl = {}, {}
        for name, m, slack in MODES:
            stf, lmf, outf = copy.deepcopy(st0), copy.deepcopy(lm0), []
            reset = m.endswith(":reset")
            m = m.split(":")[0]
            if reset and r["values"][1] not in stf["dead"]:
                stf["attacking"] = None      # F2: the press acts as fresh
            if m == "press_ends":
                apply_c2s(stf, r, tp, outf, lmf)
                stf["click"] = None
                _b, fo, oi = run_forward(stf, lmf, evs, idx + 1, tp + bound,
                                         "window", bound, interval, windup,
                                         spawns, outf)
            else:
                _b, fo, oi = run_forward(stf, lmf, evs, idx, tp + bound,
                                         m, bound, interval, windup,
                                         spawns, outf, slack)
            cf[name], cf_fl[name] = fo, oi
        row = dict(n=n, t=tp, cls=c, age=age, leg_u=leg_u, eta=eta,
                   fl=fl_, repeat=repeat, ans=ans, lat=lat, gates=gc,
                   first_gate=first_gate, cf=cf, cf_fl=cf_fl)
        rows.append(row)
        f = lambda x, w=5, d=2: ("-" * w if x is None else f"{x:{w}.{d}f}")
        say(f"  {n:3d} {tp:7.3f} {c:5s} {f(age, 4)} {f(leg_u, 6, 0)} "
            f"{f(eta, 4)} {'T' if fl_ else ('F' if fl_ is False else '-')}  "
            f"{'Y' if repeat else 'n'}   {'Y' if ans else 'n'} {f(lat)}  "
            f"{','.join(f'{k}:{v}' for k, v in gc.most_common(3)):40s}"
            + " ".join(("-" * 5 if cf[m] is None else f"{cf[m] - tp:5.2f}")
                       for m, _m, _s in MODES))

    # -- buckets over the unanswered CLICK-last presses --------------------
    click_rows = [x for x in rows if x["cls"] == "CLICK"]
    un = [x for x in click_rows if x["ans"] is None]
    say(f"  CLICK-last presses n={len(click_rows)}; answered "
        f"{len(click_rows) - len(un)}; unanswered {len(un)}")

    def bucket(x):
        g = x["first_gate"]
        if g == "moving:click":
            return ("click latch, leg IN FLIGHT at the press" if x["fl"]
                    else "click latch, leg ARRIVED at the press") \
                + (", repeat press" if x["repeat"] else ", first press")
        if g == "moving:kbd":
            return "keyboard latch armed"
        if g == "interval":
            return "interval not due (pause accumulation)"
        if g == "swing-armed":
            return "a swing already in flight"
        if g in ("no-target", "target-dead"):
            return "no target / target dead"
        return "other: " + g
    bk = Counter(bucket(x) for x in un)
    res["buckets"] = dict(bk)
    say("  FIRST GATE after each UNANSWERED CLICK-last press "
        f"(denominator {len(un)}):")
    for k, v in bk.most_common():
        say(f"    {v:3d}  {k}")

    # -- predicate scores, both directions --------------------------------
    say("  PREDICATE SCORES on CLICK-last presses (fork at the press, the "
        "real inputs replayed forward; 'bad' = opened while the modelled "
        "leg was still walking -- for P1 that is an identity, not a "
        "measurement, so read P1's bad column as the model's own consistency)")
    say("    pred   answered  newly-answered  newly-refused  bad   fork p50/p90")
    res["scores"] = {}
    for name, _m, _s in MODES:
        a = sum(1 for x in click_rows if x["cf"][name] is not None)
        na = sum(1 for x in un if x["cf"][name] is not None)
        nr = sum(1 for x in click_rows
                 if x["ans"] is not None and x["cf"][name] is None)
        bad = sum(1 for x in click_rows if x["cf_fl"][name])
        lats = [x["cf"][name] - x["t"] for x in click_rows
                if x["cf"][name] is not None]
        res["scores"][name] = (a, len(click_rows), na, nr, bad)
        say(f"    {name:5s}  {a:3d}/{len(click_rows):<3d}    {na:3d}"
            f"             {nr:3d}          {bad:3d}   "
            f"{_p(lats, 0.5):.2f}/{_p(lats, 0.9):.2f}")
    sig = [round(ts, 3) for ts in wire_started
           if (last_input(ts) or (None, {"opcode": 0}))[1]["opcode"] == 62
           and bound <= ts - last_input(ts)[0] <= bound + 0.06]
    res["signature"] = len(sig)
    say(f"  WIRE SIGNATURE of a constant bound: attack_started opening "
        f"{bound:.1f}..{bound + 0.06:.2f} s after a click that was the last "
        f"input: {len(sig)}/{len(wire_started)} {sig}")
    other = [x for x in rows if x["cls"] != "CLICK" and x["ans"] is None]
    say(f"  non-CLICK-last unanswered n={len(other)}: "
        + "; ".join(f"#{x['n']} {x['cls']} first gate {x['first_gate']}"
                    for x in other))
    lats = [x["lat"] for x in rows if x["lat"] is not None]
    res["latency"] = (_p(lats, 0.5), _p(lats, 0.9))
    say(f"  answered-press latency: n={len(lats)} p50 {_p(lats, 0.5):.3f} "
        f"p90 {_p(lats, 0.9):.3f}")
    res["rows"] = rows if verbose else None
    return res


# ------------------------------------------------------------------- CLI
def newest_capture():
    root = vaultpath.vault_path("captures", "gamesrv")
    paths = sorted(glob.glob(os.path.join(root, "authsrv-*-c1.jsonl")),
                   key=os.path.getmtime)
    return paths[-1] if paths else None


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    speed, bound, interval, verbose, s36 = (DEFAULT_SPEED, DEFAULT_BOUND,
                                            DEFAULT_INTERVAL, False, False)
    paths = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--speed":
            speed, i = float(argv[i + 1]), i + 1
        elif a == "--bound":
            bound, i = float(argv[i + 1]), i + 1
        elif a == "--interval":
            interval, i = float(argv[i + 1]), i + 1
        elif a == "--verbose":
            verbose = True
        elif a == "--section36":
            s36 = True
        else:
            paths.append(a)
        i += 1
    if s36:
        root = vaultpath.vault_path("captures", "gamesrv")
        paths = [os.path.join(root, f) for _t, f, _h in SECTION36]
    if not paths:
        p = newest_capture()
        if p is None:
            print("no gamesrv capture in the vault (%s)" % vaultpath.vault_why())
            return 2
        paths = [p]
    rc = 0
    for p in paths:
        print("=" * 100)
        print(f"CAPTURE {os.path.basename(p)}")
        if not os.path.exists(p):
            print("  MISSING")
            rc = 2
            continue
        flags, evs, spawns = load(p)
        r = score(flags, evs, spawns, speed=speed, bound=bound,
                  interval=interval, verbose=verbose)
        if s36:
            exp = dict((f, h) for _t, f, h in SECTION36)[os.path.basename(p)]
            got = (r["CLICK"][0], r["CLICK"][1], r["STOP"][0], r["STOP"][1],
                   r["WASD"][0], r["WASD"][1])
            ok = got == exp
            print(f"  SECTION 36 HEADLINE {'REPRODUCED' if ok else 'DIFFERS'}: "
                  f"got {got} expected {exp}")
            rc = rc or (0 if ok else 1)
    return rc


if __name__ == "__main__":
    sys.exit(main())
