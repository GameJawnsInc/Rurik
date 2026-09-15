#!/usr/bin/env python3
"""At what distance does a retail hostile NOTICE the player? (monsterai §9 question 7)

    python studies/monsterai/review/noticeradius.py                 # every live capture
    python studies/monsterai/review/noticeradius.py --since 202609  # captures stamped 2026-09 on
    python studies/monsterai/review/noticeradius.py --all-rows      # print the excluded rows too

THE INSTRUMENT, stated before the numbers.

THE NOTICE INSTANT is the start of the hostile's reaction BURST, not its first follow.
animref sec.40.2 read "nothing precedes the first follow" on 7/7 chases; the corpus read
here says otherwise on 3 of the 4 unprovoked ones: a 0x002B speed jump to 1.0 and one or
two 0x0029 legs closing on the player come 0.5-2.5 s BEFORE the first 0x002A follow. So
the burst is walked back from the first follow over that hostile's orders (0x0029 / 0x002A
/ 0x002B / 0x002E / 0x0028) while consecutive orders are <= BURST_GAP s apart, and the
notice instant t_n is the burst's first order. A patrol leg 10 s earlier is not in it.

THE HOSTILE'S POSITION at t_n is only KNOWN from the wire when it has not been ordered
anywhere since its 0x0020 create (PARKED-SINCE-CREATE: the create's position) or when its
last 0x0029 leg had time to arrive at ITS OWN declared speed -- the create's field 9 base
times the last 0x002B multiplier (PARKED-AFTER-LEG: the leg's endpoint). A patrolling
hostile walks at 0.28-0.35 x base, so testing arrival at 288 u/s would call a mid-leg
patroller parked; the first cut of this file did exactly that. Anything else is MOVING and
the OBSERVED distance is not reported. A RECONSTRUCTION is printed beside it instead --
the leg's start plus speed x age along the leg -- which is the client's own movement model
(NPCTRACK-F4/F7: the server's copy IS that model, 10 u median) but is NOT a wire number,
and monsterai sec.7.8 refused exactly this kind of estimate after four of them produced
refuted range figures. It is labelled recon and never pooled with the observed rows.

THE PLAYER'S POSITION at t_n: when t_n is the follow itself, the follow's point -- the
SERVER'S copy of the player at the send (animref sec.40.2, 45/45). When t_n is earlier, the
client's newest c2s self-report (0x003D / 0x0047 field 1) before t_n, with its age; a
standing player's copy sits within ~30 u of a fresh report, a moving one's within age x
288 u, and that width is printed. A player under a SERVER-ordered walk (the attack
approach, an interact walk: cmsg -- the walk is a server order) sends no self-report at
all, so an early t_n on such a row has NO player position and says so.

WHICH CHASES ARE NOTICES. chasercensus.chases() opens a chase at a hostile's first follow
naming the player and closes it at its next 0x0028, so a fight where the player steps back
and the hostile re-follows yields several "chases" of one engagement. A row is a
RE-FOLLOW when the HOSTILE already acted on the player (its attack_started, or a damage
word it sourced) or already followed the player inside ENGAGED_WINDOW s before t_n. The
player's own words on the hostile are NOT engagement, they are provocation.

PROVOKED, per row, from the player's acts on that hostile since the later of its create,
its previous chase's end and PROVOKE_WINDOW s before t_n:
  SWING  -- a player attack_started or damage word landed on it: the hostile was HIT.
            The owner's note (2026-09-15): low-level creatures, or some flag, are not
            aggroed by walking into range -- you must attack them. Hit-then-follow is that
            mechanic, so SWING rows are the passive population, and per-definition they
            say which creatures it applies to.
  CAST   -- a 0x0027 attack-skill / 0x0046 USE_SKILL naming it inside CAST_WINDOW s and
            no hit yet: the cast start itself may be the trigger. Kept apart.
  CLICK  -- the client sent 0x0026 ATTACK naming it but no swing had landed: the server walked the player in and the hostile
            reacted BEFORE being hit. A proximity notice, UNLESS retail's AI reads the
            player's intent, which nothing here rules out -- reported apart from NONE.
  NONE   -- nothing. The strict population.
A NONE row where the player struck a DIFFERENT hostile inside CHAIN_WINDOW s is flagged
(the wiki's chain aggro) and kept out of the strict population.

Combat-word slots (OBSERVED on the 2026-09-14 tape): attack_started is [4, SOURCE, target,
0] ([4, 80, 31, 0] as hostile 80 opens on player 31); the damage words are [16|17, TARGET,
source, value] (the WARRIOR-PRE plan's [16, me, foe, -f]; [17, 31, 80, v] 1.1 s after
that attack_started).

The player is derived by chasercensus's rule (the agent whose 0x0029s answer the c2s
0x003D reports). The creature's definition index is the create's field 2 & 0xFFFF and its
level is the 0x0056 definition record's field 8 (npcdefs' layout). Read-only. Stdlib
only. Needs the vault's live captures.
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
DANGER_ZONE = 1012.0     # WIKI, the drawn compass circle (studies/minimap/FINDINGS.md)
OURS = 1200.0            # authsrv.AGGRO_RANGE, ours
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
    """definition index -> level, from the 0x0056 records (npcdefs: field 8)."""
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


def combat_pairs(merged, pid, hostile):
    """[(t, op, gv, source)] combat words between the two."""
    return [(t, op, v[1], combat_source(v)) for (t, dr, op, v) in merged
            if dr == "s2c" and op in (S2C_GV_TARGET, S2C_GV_FLOAT_TARGET) and len(v) >= 4
            and v[1] in GV_COMBAT and {v[2], v[3]} == {pid, hostile}]


def burst_start(stream, t0):
    """The notice instant: the 0x002B speed jump to 1.0 inside the burst if there is one
    (a patroller at 0.28-0.35 walks legs at a 2 s cadence, so a gap rule alone would chain
    its patrol into the burst -- the jump to full speed is the reaction, ANIMREF-RE 40.9:
    6/6 retail chasers ran at 1.0); otherwise the first order of the contiguous run of
    orders (gaps <= BURST_GAP s) ending at the follow at t0."""
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
    create with the client's own movement model (a leg walks start->end at the declared
    speed; NPCTRACK-F4/F7: the server's copy IS this model). pos_at(t) -> (pos, observed,
    moving): `observed` is True only while every leg since the create ARRIVED before the
    next order and no follow / direction order intervened -- then the position is a wire
    number (the create's, or a leg endpoint). Otherwise it is a RECONSTRUCTION."""

    def __init__(self, stream, create):
        self.t_c, self.pos_c, _k, _tok, _def, self.base, self.mult = create
        self.events = [(t, op, v) for (t, op, v) in stream
                       if t >= self.t_c and op in (S2C_LEG, S2C_FOLLOW, S2C_MOVE_DIR, S2C_SPEED, S2C_HALT)]

    def pos_at(self, t):
        pos, observed, speed = self.pos_c, True, self.base * self.mult
        leg = None                      # (start, end, t_start)
        n_moving = 0

        def advance(to):
            nonlocal pos, leg
            if leg is None:
                return
            start, end, t_start = leg
            length = d(start, end)
            gone = speed * (to - t_start)
            if gone >= length:
                pos, leg = end, None
            else:
                f = gone / length if length else 1.0
                pos = (start[0] + (end[0] - start[0]) * f, start[1] + (end[1] - start[1]) * f)

        for (te, op, v) in self.events:
            if te >= t:
                break
            advance(te)
            if op == S2C_SPEED:
                if leg is not None:
                    leg = (pos, leg[1], te)
                speed = self.base * float(v[2])
            elif op == S2C_LEG:
                if leg is not None:
                    observed = False         # re-issued mid-leg
                leg = (pos, tuple(v[2]), te)
                n_moving += 1
            elif op == S2C_HALT:
                if leg is not None:
                    observed = False         # stopped mid-leg
                leg = None
            else:                            # a follow or a direction order
                observed = False
                leg = None
                n_moving += 1
        advance(t)
        return pos, observed and leg is None, leg is not None, n_moving


def hostile_position(track, t_n, anchors):
    """(where, observed_pos, recon_pos, width, note). `anchors` are the player's own 0x002A
    follows naming this hostile: their point is the SERVER'S copy of the hostile at the
    send, an observed position the attack-walk hands us for free."""
    pos, observed, moving, n_moving = track.pos_at(t_n)
    speed_now = track.base * track.mult
    for (t, op, v) in track.events:
        if t < t_n and op == S2C_SPEED:
            speed_now = track.base * float(v[2])
    note = f"{n_moving} moving orders since create"
    recent = [(t, pt) for (t, pt) in anchors if 0 <= t_n - t <= 1.5]
    if observed:
        where = "PARKED-SINCE-CREATE" if n_moving == 0 else "PARKED-AFTER-LEG"
        if recent:
            note += f"; player-follow anchor {d(recent[-1][1], pos):.0f} u from it (control)"
        return where, pos, pos, 0.0, note
    if recent:
        t_a, pt = recent[-1]
        width = speed_now * (t_n - t_a)
        return "ANCHORED", pt, pt, width, note + f"; player's follow of it {t_n - t_a:.1f} s before, +{width:.0f} u"
    return ("MOVING" if moving else "UNRESOLVED"), None, pos, None, note


def player_position(merged, pid, t_n, t0, p0):
    """(pos, width, how) for the player at t_n. width = the bracket the position carries.

    A SERVER-WALK is a 0x002A follow ordered to the player (an attack approach, an interact
    walk) with no 0x0028 halt and no self-report after it -- the client is silent AND
    moving, so the position is unknown. A 0x0029 to the player is a grant answering the
    client's own report and does not make one. Otherwise the movement arc's own result
    applies: the client's displacement across any self-report silence >= 2 s is exactly
    0.0 u (studies/movement/FINDINGS.md, handoff sec.4 item 4), so a stale report is an
    EXACT standing position, and a fresh 0x003D is a moving one, width = age x 288."""
    if t_n == t0:
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
    if last_follow is not None and (last_halt is None or last_follow > last_halt)             and (last_self is None or last_follow > last_self[0]):
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
    if last_follow is not None and (last_halt is None or last_follow > last_halt)             and (last_self is None or last_follow > last_self[0]):
        return "MOVING (server-walk)"
    if last_self and last_self[1] == C2S_HEADING and t_n - last_self[0] < 2.0:
        return "MOVING"
    return "STANDING"


def player_act_on(op, v, hostile):
    """Does this c2s message name `hostile`? Layouts (studies/cmsg/FINDINGS.md): 0x0026
    ATTACK [target, 0]; 0x0027 attack-skill and 0x0046 USE_SKILL [skillId, skillCopy,
    target, u8] -- the target is field 3, and field 1 is a SKILL id that collides with
    small agent ids if read as one (the first cut of this file did)."""
    if op == C2S_ATTACK:
        return len(v) >= 2 and v[1] == hostile
    if op in (C2S_ATTACK_SKILL, C2S_USE_SKILL):
        return len(v) >= 4 and v[3] == hostile
    return False


def provocation(merged, pid, hostile, t_from, t_n):
    """('SWING'|'CAST'|'CLICK'|'NONE', t, how) -- the player's strongest act on `hostile`
    in [t_from, t_n). CAST: a skill use naming it inside CAST_WINDOW s -- the cast START
    may be what the hostile answered (the wiki says instant skills and pre-cast damage do
    not take aggro; a targeted cast in flight is not settled), kept apart from CLICK."""
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
        elif dr == "s2c" and op in (S2C_GV_TARGET, S2C_GV_FLOAT_TARGET) and len(v) >= 4                 and v[1] in GV_COMBAT and {v[2], v[3]} == {pid, hostile}                 and combat_source(v) == pid:
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
        elif dr == "s2c" and op in (S2C_GV_TARGET, S2C_GV_FLOAT_TARGET) and len(v) >= 4                 and v[1] in GV_COMBAT and pid in (v[2], v[3]):
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


def dwell_inside(merged, track, t_n, radius, lookback=30.0):
    """(seconds, n_reports, observed) the player spent inside `radius` of the hostile,
    continuously, up to t_n -- from the player's own c2s self-reports against the hostile's
    track at each report. None when no report falls inside the window. This is the direct
    test of the owner's passive-creature note: a hostile that let the player sit inside
    the danger zone for seconds before reacting, or reacted only when hit, is passive;
    one that reacted within a tick of the crossing is not."""
    reports = [(t, tuple(v[1])) for (t, dr, op, v) in merged
               if dr == "c2s" and op in (C2S_HEADING, C2S_STOP) and t_n - lookback <= t < t_n]
    if not reports:
        return None
    inside, obs_all = [], True
    for (t, pp) in reversed(reports):
        hp, observed, _m, _n = track.pos_at(t)
        if d(hp, pp) <= radius:
            inside.append(t)
            obs_all = obs_all and observed
        else:
            break
    if not inside:
        return (0.0, 0, True)
    return (t_n - inside[-1], len(inside), obs_all)


def analyse_conn(stamp, gf, merged):
    rows = []
    pid, _c61 = chasercensus.player_of(merged)
    if pid is None:
        return rows, "no derived player"
    creates = creates_of(merged)
    levels = levels_of(merged)
    npc_ids = {aid for aid, cs in creates.items() if any(c[2] == KIND_NPC for c in cs)}
    chases = sorted(chasercensus.chases(merged, pid), key=lambda c: c["t0"])
    prev_end = {}
    for ch in chases:
        a = ch["agent"]
        t0, p0 = ch["follows"][0]
        c = create_before(creates, a, t0)
        if c is None or c[2] != KIND_NPC:
            prev_end[a] = ch["t1"]
            continue
        stream = agent_stream(merged, a)
        t_n = max(burst_start(stream, t0), c[0])
        pairs = combat_pairs(merged, pid, a)
        engaged = [x for x in pairs if t_n - ENGAGED_WINDOW <= x[0] < t_n and x[3] == a] + \
                  [t for (t, op, v) in stream if op == S2C_FOLLOW and len(v) >= 6 and v[5] == pid
                   and t_n - ENGAGED_WINDOW <= t < t_n]
        t_from = max(c[0], prev_end.get(a, 0.0), t_n - PROVOKE_WINDOW)
        prov, t_prov, how = provocation(merged, pid, a, t_from, t_n)
        track = HostileTrack(stream, c)
        anchors = [(t, tuple(v[2])) for (t, dr, op, v) in merged
                   if dr == "s2c" and op == S2C_FOLLOW and len(v) >= 6 and v[1] == pid and v[5] == a]
        where, hpos, recon, hwidth, note = hostile_position(track, t_n, anchors)
        ppos, width, phow = player_position(merged, pid, t_n, t0, p0)
        if width is not None and hwidth:
            width += hwidth
        dwell = dwell_inside(merged, track, t_n, DANGER_ZONE)
        moving = player_moving(merged, pid, t_n)
        chain = struck_another(merged, pid, a, npc_ids, t_n - CHAIN_WINDOW, t_n) if prov == "NONE" else None
        shape = burst_shape(stream, t_n, t0)
        switched = [v[5] for (t, op, v) in stream if op == S2C_FOLLOW and len(v) >= 6
                    and t_n <= t < t0 and v[5] != pid]
        if switched:
            note = (note + "; " if note else "") + f"TARGET-SWITCH: followed agent {switched[0]} first"
        if chain:
            note = (note + "; " if note else "") + f"struck another hostile {t_n - chain[0]:.1f} s before ({chain[1]})"
        rows.append({
            "stamp": stamp, "conn": gf, "agent": a, "token": c[3], "definition": c[4],
            "level": levels.get(c[4]), "t0": t0, "t_n": t_n, "shape": shape,
            "fresh": not engaged, "switched": bool(switched), "prov": prov, "t_prov": t_prov, "how": how, "chain": chain,
            "where": where, "moving": moving, "phow": phow, "note": note,
            "dist": d(hpos, ppos) if (hpos and ppos) else None,
            "recon": d(recon, ppos) if (recon and ppos) else None,
            "width": width, "dwell": dwell,
        })
        prev_end[a] = ch["t1"]
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
    fresh = [r for r in rows if r["fresh"]]
    print(f"chases of the player by a kind-9 hostile: {len(rows)}; FRESH (the hostile had not acted on "
          f"or followed the player inside {ENGAGED_WINDOW:.0f} s): {len(fresh)}; re-follows inside a fight: "
          f"{len(rows) - len(fresh)}  ({len(refused)} connections skipped: no derived player or an unclosed decode)")
    print()
    print(f"{'capture':16} {'agent':>5} {'def':>5} {'lvl':>3} {'tok':4} {'prov':5} {'hostile at t_n':19} "
          f"{'player at t_n':18} {'d(obs)':>7} {'+w':>4} {'d(recon)':>8}  burst / note")
    for r in sorted(rows, key=lambda r: (r["stamp"], r["conn"], r["t0"])):
        if not r["fresh"] and not all_rows:
            continue
        ds = f"{r['dist']:7.0f}" if r["dist"] is not None else f"{'--':>7}"
        w = f"{r['width']:4.0f}" if (r["dist"] is not None and r["width"]) else f"{'':4}"
        rc = f"{r['recon']:8.0f}" if r["recon"] is not None else f"{'--':>8}"
        lvl = f"{r['level']:3d}" if r["level"] is not None else "  ?"
        tag = "" if r["fresh"] else "RE-FOLLOW "
        print(f"{r['stamp']:16} {r['agent']:5d} {r['definition']:5d} {lvl} {r['token']:4} {r['prov']:5} "
              f"{r['where']:19} {r['moving']:18} {ds} {w} {rc}  {tag}{r['shape']} ({r['t0'] - r['t_n']:.1f} s); "
              f"player: {r['phow']}; hostile: {r['note']}; dwell<{DANGER_ZONE:.0f}: "
              + ("--" if r["dwell"] is None else f"{r['dwell'][0]:.1f} s over {r['dwell'][1]} reports{'' if r['dwell'][2] else ' (recon)'}"))
        if r["t_prov"] is not None:
            print(f"{'':16} {'':5} {'':5} {'':3} {'':4} {r['prov']:5} {r['t_n'] - r['t_prov']:6.1f} s before t_n: {r['how']}")
    print()
    strict = [r for r in fresh if r["prov"] == "NONE" and not r["chain"] and not r["switched"] and r["dist"] is not None]
    click = [r for r in fresh if r["prov"] == "CLICK" and r["dist"] is not None]
    cast = [r for r in fresh if r["prov"] == "CAST"]
    swing = [r for r in fresh if r["prov"] == "SWING"]
    unknown = [r for r in fresh if r["prov"] != "SWING" and r["dist"] is None]
    print(f"FRESH rows by provocation: NONE {sum(1 for r in fresh if r['prov'] == 'NONE')}, "
          f"CLICK-only {sum(1 for r in fresh if r['prov'] == 'CLICK')}, CAST {len(cast)}, SWING {len(swing)}; "
          f"no observed distance (hostile MOVING or player unknown) on {len(unknown)} of the non-SWING rows")
    summarise("STRICT (unprovoked, both positions observed)", strict)
    summarise("CLICK  (clicked, not yet hit; assumes a click alone does not aggro)", click)
    recon = [r for r in fresh if r["prov"] in ("NONE", "CLICK") and not r["chain"] and not r["switched"]
             and r["dist"] is None and r["recon"] is not None]
    if recon:
        v = [r["recon"] for r in recon]
        print(f"  RECON  (unprovoked/click rows with a dead-reckoned hostile -- NOT observed): n={len(v)} "
              f"min {min(v):.0f} p50 {q(v, .5):.0f} max {max(v):.0f} u")
    by_def = collections.defaultdict(collections.Counter)
    for r in fresh:
        by_def[(r["definition"], r["level"], r["token"])][r["prov"]] += 1
    print("  per definition (fresh rows): " + "; ".join(
        f"def {k[0]} lvl {k[1]} {k[2]}: " + ", ".join(f"{p} {n}" for p, n in sorted(c.items()))
        for k, c in sorted(by_def.items(), key=lambda kv: (kv[0][0], str(kv[0][1])))))
    if not strict and not click:
        print("ZERO observed notice rows -- zero exposure, not a null.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
