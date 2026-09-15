#!/usr/bin/env python3
"""At what distance does a retail hostile NOTICE the player, how far does it CHASE, and
where does it go afterwards? (monsterai §9 questions 7 and 8; §11)

    python studies/monsterai/review/noticeradius.py                 # every live capture
    python studies/monsterai/review/noticeradius.py --since 202609  # captures stamped 2026-09 on
    python studies/monsterai/review/noticeradius.py --all-rows      # print the excluded rows too

THE INSTRUMENT, stated before the numbers.

AN ENGAGEMENT is the hostile's own first act on the player -- a 0x002A follow naming the
player, OR an attack_started it sources, OR a damage word it sources -- after
ENGAGED_WINDOW s with no such act. The first cut keyed on the follow alone and missed a
whole class: a caster that walks a 0x0029 leg to its range and opens with attack_started,
never following at all (the Skale Broodcaller on 20260915T164906 -- speed jump, leg,
halt, swing; the follow came 19 s later when the player ran). Every act after the first
belongs to the same engagement until the window lapses.

THE NOTICE INSTANT is the start of the hostile's reaction BURST, walked back from the
first act over its orders (0x0029 / 0x002A / 0x002B / 0x002E / 0x0028) while they are <=
BURST_GAP s apart; when the burst carries a 0x002B jump to 1.0, that jump is the instant
(ANIMREF-RE 40.9: retail chasers run at 1.0; a patroller's 2 s leg cadence would otherwise
chain into the burst). animref §40.2 read "nothing precedes the first follow" on 7/7; the
corpus read here says a speed word and one or two legs precede it on most fresh chases.

THE HOSTILE'S POSITION at the notice is a wire number only when nothing is in flight: the
create's position, or the endpoint of a 0x0029 leg that ARRIVED at the hostile's own
declared speed (the create's field 9 base x the last 0x002B multiplier) before anything
else was ordered. A leg re-issued mid-leg, a halt mid-leg, a follow or a direction order
leave the position unknown until a later leg arrives. In between, the position is
DEAD-RECKONED along the order in flight with the client's own movement model
(NPCTRACK-F4/F7: the server's copy IS that model, 10 u median) and printed as
RECONSTRUCTION, never pooled with the observed rows (monsterai §7.8's refusal stands: four
such estimates presented as measurements were the refuted range figures of §6). The
player's own attack-walk is a free anchor: the server walks the player with 0x002A follows
naming the hostile, and each of those points is the server's copy of the hostile.

THE PLAYER'S POSITION at the notice: the follow's point when the first act is a follow at
the notice instant (the server's copy of the player at the send); otherwise the client's
newest self-report (0x003D / 0x0047 field 1) before it, with its age. The movement arc
measured the client's displacement across any self-report silence >= 2 s as exactly 0.0
u, so a stale report is an EXACT standing position; a fresh 0x003D is a moving one, width
= age x 288. A player under a SERVER-ordered walk (0x002A to the player: an attack or
interact approach) sends no self-report and has no position here.

THE NON-REACTION BOUND. Every 0x0047 stop the player made in the LOOKBACK s before the
notice, held >= MIN_STAND s without the hostile reacting, is a distance at which this
hostile did NOT notice. The smallest of them is an UPPER bound on its radius, and with the
notice distance a LOWER bound the radius is bracketed from both sides -- the check with no
free parameter. (20260915T155656: a level-5 creature let the player stand 5 s at 1,048 u,
then reacted 0.16 s after a stop at 887 u.)

PROVOKED, per engagement, from the player's acts on that hostile since the later of its
create, its previous engagement's end and PROVOKE_WINDOW s before the notice:
  SWING  -- a player attack_started or damage word landed on it: the hostile was HIT.
            The owner's note (2026-09-15): low-level creatures, or some flag, are not
            aggroed by walking into range -- you must attack them. Hit-then-react is that
            mechanic; `dwell<1012` says how long the player stood inside the circle first.
  CAST   -- a 0x0027 attack-skill / 0x0046 USE_SKILL naming it inside CAST_WINDOW s and
            no hit yet: the cast start itself may be the trigger. Kept apart.
  CLICK  -- a 0x0026 ATTACK click naming it, no swing landed: the server walked the
            player in and the hostile reacted BEFORE being hit -- a proximity notice
            unless retail's AI reads the player's intent. Reported apart from NONE.
  NONE   -- nothing. The strict population.
A NONE row where the player struck a DIFFERENT hostile inside CHAIN_WINDOW s is flagged
(the wiki's chain aggro) and kept out of the strict population.

THE CHASE AND THE LEASH (§9 Q8). Inside an engagement the CHASE is every order whose point
lies within CHASE_NEAR u of the player's copy or newest report -- the 0x002A follows, and
the 0x0029 legs a chaser is sometimes given instead (the level-5 creature chased with legs
once and with follows twice). The give-up point is the last such order's point, a wire
number roughly where the hostile turned; the leash is its distance from the notice
position; and the RETURN is where the hostile's legs go in the RETURN_WINDOW s after --
HOME (within HOME_RADIUS u of its create position), PATROL (the leg it abandoned at the
notice), or elsewhere. All three outcomes are findings.

Combat-word slots (OBSERVED on the 2026-09-14 tape): attack_started is [4, SOURCE, target,
0]; the damage words are [16|17, TARGET, source, value]. Client layouts (studies/cmsg):
0x0026 ATTACK [target, 0]; 0x0027 / 0x0046 [skillId, skillCopy, target, u8].

The player is derived by chasercensus's rule (the agent whose 0x0029s answer the c2s
0x003D reports -- a connection with fewer than five keyboard headings has no player).
The creature's definition index is the create's field 2 & 0xFFFF and its level the
0x0056 record's field 8 (npcdefs' layout). Read-only. Stdlib only. Needs the vault's
live captures.
"""
import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
for sub in ("toolkit", "toolkit/authsrv", "toolkit/clientscan", "toolkit/schema",
            "studies/npctrack/review"):
    p = os.path.join(ROOT, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import chasercensus                                            # noqa: E402

S2C_CREATE = 0x0020
S2C_MOVE_DIR = 0x0025
S2C_HALT = 0x0028
S2C_LEG = 0x0029
S2C_FOLLOW = 0x002A
S2C_SPEED = 0x002B
S2C_FACING = 0x002E
S2C_DEFINITION = 0x0056
S2C_GV_TARGET = 0x00A0
S2C_GV_FLOAT_TARGET = 0x00A3
C2S_ATTACK = 0x0026
C2S_ATTACK_SKILL = 0x0027
C2S_HEADING = 0x003D
C2S_USE_SKILL = 0x0046
C2S_STOP = 0x0047
GV_ATTACK_STARTED = 4
GV_COMBAT = (4, 16, 17)
KIND_NPC = 9
DEFINITION_MASK = 0xFFFF
RUN_SPEED = 288.0
BURST_GAP = 2.0
STANDING_WINDOW = 1.5
ENGAGED_WINDOW = 10.0
PROVOKE_WINDOW = 30.0
CHAIN_WINDOW = 5.0
CAST_WINDOW = 3.0
LOOKBACK = 90.0
MIN_STAND = 2.0
CHASE_NEAR = 600.0
RETURN_WINDOW = 25.0
HOME_RADIUS = 150.0
SPAWN_WINDOW = 5.0            # an engagement this soon after the create is the SPAWN, not a notice
MONSTER_TOKENS = ("mon1", "mons")
DANGER_ZONE = 1012.0     # WIKI, the drawn compass circle (studies/minimap/FINDINGS.md)
OURS = 1012.0            # authsrv.AGGRO_RANGE since 2026-09-15 (was 1200)
ORDER_OPS = (S2C_LEG, S2C_FOLLOW, S2C_SPEED, S2C_FACING, S2C_HALT, S2C_MOVE_DIR)


def d(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def fourcc(v):
    """npcdefs._fourcc's byte order (big-endian: 'mon1'), ascii-safe for a cp1252 console."""
    try:
        return int(v).to_bytes(4, "big").decode("ascii", "replace").replace("�", "?")
    except (OverflowError, ValueError):
        return f"{v}"


def q(v, f):
    v = sorted(v)
    return v[min(int(f * len(v)), len(v) - 1)] if v else float("nan")


def creates_of(merged):
    """agent -> [(t, pos, kind, token, definition, base_speed, mult)] per 0x0020, in order."""
    out = collections.defaultdict(list)
    for (t, dr, op, v) in merged:
        if dr == "s2c" and op == S2C_CREATE and len(v) >= 13:
            out[v[1]].append((t, tuple(v[5]), v[4], fourcc(v[12]), v[2] & DEFINITION_MASK,
                              float(v[9]), float(v[10])))
    return out


def levels_of(merged):
    out = {}
    for (t, dr, op, v) in merged:
        if dr == "s2c" and op == S2C_DEFINITION and len(v) >= 9:
            out[v[1]] = v[8]
    return out


def create_before(creates, agent, t):
    rows = [c for c in creates.get(agent, []) if c[0] <= t]
    return rows[-1] if rows else None


def agent_stream(merged, agent):
    return [(t, op, v) for (t, dr, op, v) in merged
            if dr == "s2c" and len(v) >= 2 and v[1] == agent]


def combat_source(v):
    return v[2] if v[1] == GV_ATTACK_STARTED else v[3]


def hostile_acts(merged, stream, pid, a):
    """[(t, kind, point)] the hostile's own acts on the player: follows naming it, and the
    combat words it sourced onto it."""
    acts = [(t, "follow", tuple(v[2])) for (t, op, v) in stream
            if op == S2C_FOLLOW and len(v) >= 6 and v[5] == pid]
    for (t, dr, op, v) in merged:
        if dr == "s2c" and op in (S2C_GV_TARGET, S2C_GV_FLOAT_TARGET) and len(v) >= 4 \
                and v[1] in GV_COMBAT and {v[2], v[3]} == {pid, a} and combat_source(v) == a:
            acts.append((t, "attack" if v[1] == GV_ATTACK_STARTED else "damage", None))
    return sorted(acts)


def engagements(acts):
    """Group the hostile's acts into engagements separated by ENGAGED_WINDOW s."""
    out, cur = [], None
    for act in acts:
        if cur is None or act[0] - cur["acts"][-1][0] > ENGAGED_WINDOW:
            cur = {"acts": [act]}
            out.append(cur)
        else:
            cur["acts"].append(act)
    for e in out:
        e["t_first"] = e["acts"][0][0]
        e["first_kind"] = e["acts"][0][1]
        e["t_last"] = e["acts"][-1][0]
    return out


def burst_start(stream, t0):
    orders = [(t, op, v) for (t, op, v) in stream if op in ORDER_OPS and t <= t0]
    t_n = t0
    for (t, op, v) in reversed(orders):
        if t_n - t <= BURST_GAP:
            t_n = t
        elif t < t_n:
            break
    jumps = [t for (t, op, v) in orders if t_n <= t <= t0 and op == S2C_SPEED and float(v[2]) >= 0.99]
    return jumps[0] if jumps else t_n


class HostileTrack:
    """The hostile's position as a function of time, replayed from its orders since the
    create with the client's own movement model. pos_at(t) -> (pos, observed, moving,
    n_moving): `observed` is True only when nothing is in flight and the position is a
    wire number -- the create's, or the endpoint of a leg that arrived. A leg re-issued
    mid-leg, a halt mid-leg, a follow or a direction order lose it; the next arriving
    0x0029 leg restores it (its endpoint IS a wire number). A follow is reckoned as a leg
    toward its point (the player's copy) at the current speed but never restores it."""

    def __init__(self, stream, create):
        self.t_c, self.pos_c, _k, _tok, _def, self.base, self.mult = create
        self.events = [(t, op, v) for (t, op, v) in stream
                       if t >= self.t_c and op in (S2C_LEG, S2C_FOLLOW, S2C_MOVE_DIR, S2C_SPEED, S2C_HALT)]

    def pos_at(self, t):
        pos, known, speed = self.pos_c, True, self.base * self.mult
        leg = None                      # [start, end, t_start, restores_known]
        n_moving = 0

        def advance(to):
            nonlocal pos, leg, known
            if leg is None:
                return
            start, end, t_start, restores = leg
            length = d(start, end)
            gone = speed * (to - t_start)
            if gone >= length:
                pos, leg = end, None
                if restores:
                    known = True
            else:
                f = gone / length if length else 1.0
                pos = (start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f)

        for (te, op, v) in self.events:
            if te >= t:
                break
            advance(te)
            if op == S2C_SPEED:
                if leg is not None:
                    leg = [pos, leg[1], te, leg[3]]
                speed = self.base * float(v[2])
            elif op == S2C_LEG:
                if leg is not None:
                    known = False
                leg = [pos, tuple(v[2]), te, True]
                n_moving += 1
            elif op == S2C_FOLLOW:
                known = False
                leg = [pos, tuple(v[2]), te, False]
                n_moving += 1
            elif op == S2C_HALT:
                if leg is not None:
                    known = False
                leg = None
            else:
                known = False
                leg = None
                n_moving += 1
        advance(t)
        return pos, (known and leg is None), leg is not None, n_moving

    def speed_at(self, t):
        s = self.base * self.mult
        for (te, op, v) in self.events:
            if te < t and op == S2C_SPEED:
                s = self.base * float(v[2])
        return s


def hostile_position(track, t_n, anchors):
    """(where, observed_pos, recon_pos, width, note) for the hostile at t_n."""
    pos, observed, moving, n_moving = track.pos_at(t_n)
    note = f"{n_moving} moving orders since create"
    recent = [(t, pt) for (t, pt) in anchors if 0 <= t_n - t <= 1.5]
    if observed:
        where = "PARKED-SINCE-CREATE" if n_moving == 0 else "PARKED-AFTER-LEG"
        if recent:
            note += f"; player-follow anchor {d(recent[-1][1], pos):.0f} u from it (control)"
        return where, pos, pos, 0.0, note
    if recent:
        t_a, pt = recent[-1]
        width = track.speed_at(t_n) * (t_n - t_a)
        return "ANCHORED", pt, pt, width, note + f"; player's follow of it {t_n - t_a:.1f} s before, +{width:.0f} u"
    return ("MOVING" if moving else "UNRESOLVED"), None, pos, None, note


def player_position(merged, pid, t_n, p0):
    """(pos, width, how) for the player at t_n; p0 is the follow's point when the first
    act is a follow AT t_n, else None."""
    if p0 is not None:
        return p0, 0.0, "server copy (the follow's point)"
    last_self, last_follow, last_halt = None, None, None
    for (t, dr, op, v) in merged:
        if t >= t_n:
            break
        if dr == "c2s" and op in (C2S_HEADING, C2S_STOP) and len(v) >= 2:
            last_self = (t, op, tuple(v[1]))
        elif dr == "s2c" and len(v) >= 2 and v[1] == pid:
            if op == S2C_FOLLOW:
                last_follow = t
            elif op == S2C_HALT:
                last_halt = t
    if last_follow is not None and (last_halt is None or last_follow > last_halt) \
            and (last_self is None or last_follow > last_self[0]):
        return None, None, "server-walk, no self-report"
    if last_self is None:
        return None, None, "no self-report"
    t, op, pos = last_self
    age = t_n - t
    if op == C2S_STOP or age >= 2.0:
        return pos, 30.0, f"self-report {age:.1f} s old, standing"
    return pos, age * RUN_SPEED + 30.0, f"self-report {age:.1f} s old, moving"


def player_moving(merged, pid, t_n):
    last_self, last_follow, last_halt = None, None, None
    for (t, dr, op, v) in merged:
        if t >= t_n:
            break
        if dr == "c2s" and op in (C2S_HEADING, C2S_STOP) and len(v) >= 2:
            last_self = (t, op)
        elif dr == "s2c" and len(v) >= 2 and v[1] == pid:
            if op == S2C_FOLLOW:
                last_follow = t
            elif op == S2C_HALT:
                last_halt = t
    if last_follow is not None and (last_halt is None or last_follow > last_halt) \
            and (last_self is None or last_follow > last_self[0]):
        return "MOVING (server-walk)"
    if last_self and last_self[1] == C2S_HEADING and t_n - last_self[0] < 2.0:
        return "MOVING"
    return "STANDING"


def player_reports(merged):
    return [(t, op, tuple(v[1])) for (t, dr, op, v) in merged
            if dr == "c2s" and op in (C2S_HEADING, C2S_STOP) and len(v) >= 2]


def report_at(reports, t):
    """The player's newest self-report at t: (t_report, pos) or None."""
    best = None
    for (tr, op, pos) in reports:
        if tr >= t:
            break
        best = (tr, pos)
    return best


def player_act_on(op, v, hostile):
    if op == C2S_ATTACK:
        return len(v) >= 2 and v[1] == hostile
    if op in (C2S_ATTACK_SKILL, C2S_USE_SKILL):
        return len(v) >= 4 and v[3] == hostile
    return False


def provocation(merged, pid, hostile, t_from, t_n):
    click, cast = None, None
    for (t, dr, op, v) in merged:
        if t >= t_n:
            break
        if t < t_from:
            continue
        if dr == "c2s" and player_act_on(op, v, hostile):
            if op == C2S_ATTACK and click is None:
                click = (t, "c2s 0x0026 attack click")
            elif op != C2S_ATTACK and t_n - t <= CAST_WINDOW:
                cast = (t, f"c2s 0x{op:04X} skill {v[1]} on it")
        elif dr == "s2c" and op in (S2C_GV_TARGET, S2C_GV_FLOAT_TARGET) and len(v) >= 4 \
                and v[1] in GV_COMBAT and {v[2], v[3]} == {pid, hostile} \
                and combat_source(v) == pid:
            return "SWING", t, f"s2c 0x{op:04X} gv {v[1]}"
    if cast:
        return "CAST", cast[0], cast[1]
    if click:
        return "CLICK", click[0], click[1]
    return "NONE", None, ""


def struck_another(merged, pid, hostile, npc_ids, t_lo, t_hi):
    for (t, dr, op, v) in reversed(merged):
        if t >= t_hi or t < t_lo:
            continue
        if dr == "c2s" and op in (C2S_ATTACK, C2S_ATTACK_SKILL, C2S_USE_SKILL):
            hit = [x for x in npc_ids if x != hostile and player_act_on(op, v, x)]
            if hit:
                return (t, f"c2s 0x{op:04X} on {hit[0]}")
        elif dr == "s2c" and op in (S2C_GV_TARGET, S2C_GV_FLOAT_TARGET) and len(v) >= 4 \
                and v[1] in GV_COMBAT and pid in (v[2], v[3]):
            other = v[3] if v[2] == pid else v[2]
            if other in npc_ids and other != hostile:
                return (t, f"s2c 0x{op:04X} gv {v[1]} with {other}")
    return None


def burst_shape(stream, t_n, t0):
    names = {S2C_LEG: "leg", S2C_FOLLOW: "follow", S2C_SPEED: "speed", S2C_FACING: "facing",
             S2C_HALT: "halt", S2C_MOVE_DIR: "dir"}
    out = []
    for (t, op, v) in stream:
        if t_n <= t <= t0 and op in ORDER_OPS:
            s = names[op]
            if op == S2C_SPEED:
                s += f"={float(v[2]):.2f}"
            out.append(s)
    return "+".join(out)


def dwell_inside(reports, track, t_n, radius, lookback=30.0):
    """(seconds, n_reports, observed) the player spent inside `radius` of the hostile,
    continuously, up to t_n, from the player's own self-reports against the track."""
    rs = [(t, pos) for (t, op, pos) in reports if t_n - lookback <= t < t_n]
    if not rs:
        return None
    inside, obs_all = [], True
    for (t, pp) in reversed(rs):
        hp, observed, _m, _n = track.pos_at(t)
        if d(hp, pp) <= radius:
            inside.append(t)
            obs_all = obs_all and observed
        else:
            break
    if not inside:
        return (0.0, 0, True)
    return (t_n - inside[-1], len(inside), obs_all)


def no_reaction_bound(reports, track, t_from, t_n):
    """The smallest distance at which the player stood >= MIN_STAND s without this hostile
    reacting, in [t_from, t_n): (distance, seconds stood, observed) or None. An UPPER
    bound on the notice radius from the same tape as the lower one."""
    best = None
    for i, (t, op, pos) in enumerate(reports):
        if op != C2S_STOP or t < t_from or t >= t_n:
            continue
        nxt = [tr for (tr, o, p) in reports[i + 1:] if o == C2S_HEADING]
        if not nxt or nxt[0] >= t_n - 0.3:
            continue                    # the stand contains the notice: that is the notice, not a bound
        t_end = nxt[0]
        stood = t_end - t
        if stood < MIN_STAND:
            continue
        dmin, obs = None, True
        for ts in (t, (t + t_end) / 2.0, t_end - 0.05):
            hp, observed, _m, _n = track.pos_at(ts)
            dist = d(hp, pos)
            obs = obs and observed
            dmin = dist if dmin is None else min(dmin, dist)
        if best is None or dmin < best[0]:
            best = (dmin, stood, obs)
    return best


def chase_profile(stream, eng, reports, track, t_n, create):
    """The chase inside an engagement and what came after it."""
    t_first, t_last = eng["t_first"], eng["t_last"]
    t_stop = t_last + RETURN_WINDOW
    orders = [(t, op, v) for (t, op, v) in stream if t_n <= t <= t_stop and op in ORDER_OPS]
    chase = []
    for (t, op, v) in orders:
        if op == S2C_FOLLOW and len(v) >= 6:
            chase.append((t, "follow", tuple(v[2])))
        elif op == S2C_LEG:
            r = report_at(reports, t)
            if r and d(tuple(v[2]), r[1]) <= CHASE_NEAR:
                chase.append((t, "leg", tuple(v[2])))
    if not chase:
        return None
    t_give, kind_give, p_give = chase[-1]
    after = [(t, op, v) for (t, op, v) in orders if t > t_give]
    end_kind = "none"
    if after:
        end_kind = {S2C_HALT: "halt", S2C_LEG: "leg", S2C_SPEED: "speed", S2C_FOLLOW: "follow",
                    S2C_FACING: "facing", S2C_MOVE_DIR: "dir"}[after[0][1]]
    legs_after = [tuple(v[2]) for (t, op, v) in after if op == S2C_LEG]
    pre = [tuple(v[2]) for (t, op, v) in stream if op == S2C_LEG and t < t_n]
    dest = legs_after[-1] if legs_after else None
    ret = "none"
    if dest is not None:
        if d(dest, create[1]) <= HOME_RADIUS:
            ret = "HOME"
        elif pre and any(d(l, pre[-1]) <= 50.0 for l in legs_after):
            ret = "PATROL (the leg abandoned at the notice)"
        else:
            ret = f"elsewhere ({d(dest, create[1]):.0f} u from home)"
    notice_pos, obs_n, _m, _n = track.pos_at(t_n)
    speeds_after = [float(v[2]) for (t, op, v) in after if op == S2C_SPEED]
    swings_in_chase = sum(1 for (t, k, p) in eng["acts"]
                          if k == "attack" and chase[0][0] < t < t_give)
    return {
        "n_follows": sum(1 for c in chase if c[1] == "follow"),
        "n_legs": sum(1 for c in chase if c[1] == "leg"),
        "t_chase0": chase[0][0], "t_give": t_give, "give_kind": kind_give,
        "leash": d(notice_pos, p_give), "leash_obs": obs_n,
        "duration": t_give - t_n, "chase_secs": t_give - chase[0][0],
        "end_kind": end_kind, "return": ret, "speed_after": speeds_after[0] if speeds_after else None,
        "swings_in_chase": swings_in_chase,
    }


def analyse_conn(stamp, gf, merged):
    rows = []
    pid, _c61 = chasercensus.player_of(merged)
    if pid is None:
        return rows, "no derived player"
    creates = creates_of(merged)
    levels = levels_of(merged)
    reports = player_reports(merged)
    npc_ids = {aid for aid, cs in creates.items() if any(c[2] == KIND_NPC for c in cs)}
    anchors_all = collections.defaultdict(list)
    for (t, dr, op, v) in merged:
        if dr == "s2c" and op == S2C_FOLLOW and len(v) >= 6 and v[1] == pid:
            anchors_all[v[5]].append((t, tuple(v[2])))
    for a in sorted(npc_ids):
        stream = agent_stream(merged, a)
        acts = hostile_acts(merged, stream, pid, a)
        if not acts:
            continue
        prev_end = None
        for eng in engagements(acts):
            t_act = eng["t_first"]
            c = create_before(creates, a, t_act)
            if c is None or c[2] != KIND_NPC:
                prev_end = eng["t_last"]
                continue
            t_n = max(burst_start(stream, t_act), c[0])
            p0 = eng["acts"][0][2] if (eng["first_kind"] == "follow" and t_n == t_act) else None
            t_from = max(c[0], prev_end or 0.0, t_n - PROVOKE_WINDOW)
            prov, t_prov, how = provocation(merged, pid, a, t_from, t_n)
            track = HostileTrack(stream, c)
            where, hpos, recon, hwidth, note = hostile_position(track, t_n, anchors_all.get(a, []))
            ppos, width, phow = player_position(merged, pid, t_n, p0)
            if width is not None and hwidth:
                width += hwidth
            dwell = dwell_inside(reports, track, t_n, DANGER_ZONE)
            bound = no_reaction_bound(reports, track, max(c[0], t_n - LOOKBACK, prev_end or 0.0), t_n)
            moving = player_moving(merged, pid, t_n)
            chain = struck_another(merged, pid, a, npc_ids, t_n - CHAIN_WINDOW, t_n) if prov == "NONE" else None
            shape = burst_shape(stream, t_n, t_act)
            switched = [v[5] for (t, op, v) in stream if op == S2C_FOLLOW and len(v) >= 6
                        and t_n <= t < t_act and v[5] != pid]
            spawned = (t_n - c[0]) <= SPAWN_WINDOW
            if spawned:
                note = (note + "; " if note else "") + f"SPAWN-TRIGGERED: {t_n - c[0]:.1f} s after its create"
            if switched:
                note = (note + "; " if note else "") + f"TARGET-SWITCH: followed agent {switched[0]} first"
            if chain:
                note = (note + "; " if note else "") + f"struck another hostile {t_n - chain[0]:.1f} s before ({chain[1]})"
            rows.append({
                "stamp": stamp, "conn": gf, "agent": a, "token": c[3], "definition": c[4],
                "level": levels.get(c[4]), "t0": t_act, "t_n": t_n, "shape": shape,
                "first_kind": eng["first_kind"],
                "switched": bool(switched), "spawned": spawned, "monster": c[3] in MONSTER_TOKENS,
                "prov": prov, "t_prov": t_prov, "how": how, "chain": chain,
                "where": where, "moving": moving, "phow": phow, "note": note,
                "dist": d(hpos, ppos) if (hpos and ppos) else None,
                "recon": d(recon, ppos) if (recon and ppos) else None,
                "width": width, "dwell": dwell, "bound": bound,
                "chase": chase_profile(stream, eng, reports, track, t_n, c),
            })
            prev_end = eng["t_last"]
    rows.sort(key=lambda r: (r["stamp"], r["conn"], r["t_n"]))
    return rows, None


def summarise(label, sel):
    v = [r["dist"] for r in sel]
    if not v:
        print(f"  {label}: n=0")
        return
    hi = [x + (r["width"] or 0.0) for x, r in zip(v, sel)]
    print(f"  {label}: n={len(v)}  observed min {min(v):.0f} p50 {q(v, .5):.0f} max {max(v):.0f} u, "
          f"upper bounds max {max(hi):.0f} u  (danger zone {DANGER_ZONE:.0f}; ours {OURS:.0f}); "
          f"over {DANGER_ZONE:.0f}: {sum(1 for x in v if x > DANGER_ZONE)}, "
          f"upper bound under {DANGER_ZONE:.0f}: {sum(1 for x in hi if x < DANGER_ZONE)}")


def fmt_bound(b):
    if b is None:
        return "--"
    return f"no reaction {b[1]:.0f} s at {b[0]:.0f} u{'' if b[2] else ' (recon)'}"


def main(argv):
    import livewire
    since = argv[argv.index("--since") + 1] if "--since" in argv else None
    all_rows = "--all-rows" in argv
    rows, refused = [], []
    for capdir, gf in livewire.live_connections():
        stamp = os.path.basename(capdir)
        if since and stamp < since:
            continue
        conn, merged, ok = livewire.decode_conn(capdir, gf)
        if not ok or not merged:
            refused.append((stamp, gf, "decode not closed"))
            continue
        r, why = analyse_conn(stamp, gf, merged)
        if why:
            refused.append((stamp, gf, why))
        rows.extend(r)
    print(f"engagements of the player by a kind-9 hostile (its own first act after "
          f"{ENGAGED_WINDOW:.0f} s of none): {len(rows)}  ({len(refused)} connections skipped: no "
          f"derived player or an unclosed decode)")
    print()
    print(f"{'capture':16} {'agent':>5} {'def':>5} {'lvl':>3} {'tok':4} {'prov':5} {'first':6} "
          f"{'hostile at t_n':19} {'player at t_n':18} {'d(obs)':>7} {'+w':>4} {'d(recon)':>8}  "
          f"burst / bound / note")
    for r in rows:
        ds = f"{r['dist']:7.0f}" if r["dist"] is not None else f"{'--':>7}"
        w = f"{r['width']:4.0f}" if (r["dist"] is not None and r["width"]) else f"{'':4}"
        rc = f"{r['recon']:8.0f}" if r["recon"] is not None else f"{'--':>8}"
        lvl = f"{r['level']:3d}" if r["level"] is not None else "  ?"
        print(f"{r['stamp']:16} {r['agent']:5d} {r['definition']:5d} {lvl} {r['token']:4} {r['prov']:5} "
              f"{r['first_kind']:6} {r['where']:19} {r['moving']:18} {ds} {w} {rc}  "
              f"{r['shape']} ({r['t0'] - r['t_n']:.1f} s); {fmt_bound(r['bound'])}; "
              f"player: {r['phow']}; hostile: {r['note']}; dwell<{DANGER_ZONE:.0f}: "
              + ("--" if r["dwell"] is None else
                 f"{r['dwell'][0]:.1f} s over {r['dwell'][1]} reports{'' if r['dwell'][2] else ' (recon)'}"))
        if r["t_prov"] is not None:
            print(f"{'':16} {'':5} {'':5} {'':3} {'':4} {r['prov']:5} {r['t_n'] - r['t_prov']:6.1f} s before t_n: {r['how']}")
        ch = r["chase"]
        if ch:
            print(f"{'':16} {'':5} {'':5} {'':3} {'':4} chase: {ch['n_follows']} follows + {ch['n_legs']} legs over "
                  f"{ch['chase_secs']:.1f} s ({ch['duration']:.1f} s after the notice), gave up on a {ch['give_kind']} "
                  f"{ch['leash']:.0f} u from its notice position{'' if ch['leash_obs'] else ' (recon)'}; "
                  f"then {ch['end_kind']}"
                  + (f", speed {ch['speed_after']:.2f}" if ch["speed_after"] is not None else "")
                  + f"; return: {ch['return']}; swings mid-chase: {ch['swings_in_chase']}")
    print()
    clean = [r for r in rows if r["prov"] == "NONE" and not r["chain"] and not r["switched"]
             and not r["spawned"] and r["monster"]]
    strict = [r for r in clean if r["dist"] is not None]
    click = [r for r in rows if r["prov"] == "CLICK" and r["dist"] is not None]
    cast = [r for r in rows if r["prov"] == "CAST"]
    swing = [r for r in rows if r["prov"] == "SWING"]
    unknown = [r for r in rows if r["prov"] != "SWING" and r["dist"] is None]
    print(f"excluded from the strict population: spawn-triggered {sum(1 for r in rows if r['spawned'])}, "
          f"non-monster token {sum(1 for r in rows if not r['monster'])}, target switch {sum(1 for r in rows if r['switched'])}, "
          f"chain {sum(1 for r in rows if r['chain'])}")
    print(f"by provocation: NONE {sum(1 for r in rows if r['prov'] == 'NONE')}, "
          f"CLICK-only {sum(1 for r in rows if r['prov'] == 'CLICK')}, CAST {len(cast)}, SWING {len(swing)}; "
          f"no observed distance (hostile MOVING or player unknown) on {len(unknown)} of the non-SWING rows")
    summarise("STRICT (unprovoked, both positions observed)", strict)
    summarise("CLICK  (clicked, not yet hit; assumes a click alone does not aggro)", click)
    recon = [r for r in rows if r["prov"] in ("NONE", "CLICK") and not r["chain"] and not r["switched"]
             and not r["spawned"] and r["monster"] and r["dist"] is None and r["recon"] is not None]
    if recon:
        v = [r["recon"] for r in recon]
        print(f"  RECON  (unprovoked/click rows with a dead-reckoned hostile -- NOT observed): n={len(v)} "
              f"min {min(v):.0f} p50 {q(v, .5):.0f} max {max(v):.0f} u")
    bounded = [r for r in clean if r["bound"] is not None
               and (r["dist"] is not None or r["recon"] is not None)]
    if bounded:
        print("  BRACKETS (lower = the notice, upper = the longest unreacted stand before it):")
        for r in bounded:
            lo = r["dist"] if r["dist"] is not None else r["recon"]
            tag = "obs" if r["dist"] is not None else "recon"
            print(f"    def {r['definition']} lvl {r['level']} {r['stamp']} agent {r['agent']}: "
                  f"[{lo:.0f} ({tag}), {r['bound'][0]:.0f}{'' if r['bound'][2] else ' (recon)'}] u "
                  f"-- stood {r['bound'][1]:.0f} s at the upper")
    by_def = collections.defaultdict(collections.Counter)
    for r in rows:
        by_def[(r["definition"], r["level"], r["token"])][r["prov"]] += 1
    print("  per definition: " + "; ".join(
        f"def {k[0]} lvl {k[1]} {k[2]}: " + ", ".join(f"{p} {n}" for p, n in sorted(c.items()))
        for k, c in sorted(by_def.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))))
    chases = [r for r in rows if r["chase"]]
    if chases:
        print(f"  CHASES: {len(chases)}; return HOME {sum(1 for r in chases if r['chase']['return'] == 'HOME')}, "
              f"PATROL {sum(1 for r in chases if r['chase']['return'].startswith('PATROL'))}, "
              f"elsewhere/none {sum(1 for r in chases if not (r['chase']['return'] == 'HOME' or r['chase']['return'].startswith('PATROL')))}")
    if not strict and not click:
        print("ZERO observed notice rows -- zero exposure, not a null.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
