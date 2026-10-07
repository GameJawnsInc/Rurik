"""test_approachroute -- the out-of-reach approach (ROUTE). Two pieces have shipped:
ROUTE-A, a RANGED approach's first swing holds the walk gate and halts the body
(RANGERPRE-S16, 2026-09-30, sections 1-3), and ROUTE-B, a HELD interact is served at the
follow disc rather than at INTERACT_RANGE (RANGERPRE-S17, 2026-09-30, sections 4-5).
ROUTE-C (corner routing), ROUTE-C2 and ROUTE-D are not built; each adds its own section
here when it lands.

    python toolkit/authsrv/test_approachroute.py

ROUTE-B, WHAT RETAIL DOES (section 5 re-derives every figure from the bytes). On
20260929T150923 the two held interacts whose walk starts from an exact point are served
at 67.8 u (:56064, the dialog at 979.1046, 1.850 s after the 0x002A left the last
corner 600.7 u out) and at 75.2 u (:59969, the dialog at 202.6552, the model still
42.3 u short of its last leg's end -- served on the way, a DISTANCE rule): 45.7 and
20.0 ms after the model crosses 81 u, where a 144 u serve predicts 0.26 and 0.24 s
early. Presses from exact stops 95.7 and 134.6 u out are answered at once; one from
~167 u was walked. Ours walked to 100 u and served at the first tick inside 144 u. Now
the walk stops at the follow disc (80 u) and the hold is served inside 81 u while the
walk is in flight, or anywhere inside 144 u once it is over -- the slack fix, so a leg
that ends outside the disc (a clip-fallback, a client report a few units off) cannot
strand it.

WHAT RETAIL SENDS (OBSERVED; section 3 re-derives every count from the bytes). On the
four live connections whose player shoots, the FIRST own attack start after a server
0x002A follow carries, in one wire segment, 0x00A0 [4, me, T, 0], 0x009F [8, me, 1],
a 0x001E tick and 0x0028 [me] -- 12 of 12 (20260929T150923 :55934 335.0923, 338.0686,
379.4129, 453.5679, 515.4825; 20260914T005758 :56011 169.8902, 223.5783, 361.9119,
363.9707, 583.1255; 20260810T235916 :61624 95.4709; 20260807T143055 :62994 82.7741).
The swing's own launch segment carries no [8, me, 0] (0 of 10); the hold's first release
answers a keyboard report 7 times, a re-approach once, a skill press twice and the
target's death twice; the chain's later starts are [4] alone; a start with the body at
rest carries neither message (37 of 37 on 20260929T150923). Melee is mixed (:53756, 1 of
4 with both) and is not this rule.

What ours sent: [4] alone -- no hold (ANIMREF-RE 35 took it off every auto swing) and
no halt, so nothing stopped the drawn body at range: the 0x002A names the target and
the client's resolver parks at the MELEE disc.

SECTIONS. 1 our server, offline: the approach driven through begin_attack /
attack_tick / approach_tick / _approach_send / _land_player_swing / cancel_on_move,
with the known-bad arm (--no-approach-start-halt) and the controls (a sword, a bow
already in range, another target). 2 the flag and main()'s rebind. 3 THE TAPES:
the census, OURS == RETAIL on all 12 with the ids substituted, the known-bad batch
matching none, the launches, what ends each hold, the at-rest control and the melee
split. Section 3 is a declared skip on a machine with no captures/live; a vault that
has captures but not these dies loudly in require_dir. Sections 1-2 need no vault, no
socket and no client. 4 ROUTE-B on our server, offline, over an open-field stub mesh:
the press, the walk driven tick by tick in world_tick's order, where it is served, the
known-bad arm (--held-interact-at-range), the slack cases, the controls, the flag.
5 ROUTE-B's TAPES: the two exact-start witnesses, ours against retail's dialog instant,
and the immediate range -- a declared skip like section 3.
"""
import contextlib
import io
import json
import math
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
PARENT = os.path.dirname(HERE)
if PARENT not in sys.path:
    sys.path.insert(0, PARENT)

import checks                                                  # noqa: E402
import agents                                                  # noqa: E402
import authsrv                                                 # noqa: E402
import vaultpath                                               # noqa: E402

# Floor from the green run of 2026-09-30 with RURIK_VAULT at an EMPTY directory (sections 3
# and 5 declared skips): 32 -- 21 for ROUTE-A (20 until the review follow-up added 1r) and
# 11 for ROUTE-B's section 4 (RANGERPRE-S17). With the captures present section 3 adds 9
# and section 5 adds 5 (46). 2026-10-07, RANGERLOOP-F9: section 6 adds 7 on any machine
# (39 on the empty-vault green run, sections 3, 5 and 7 declared skips) and section 7 adds
# 4 with the gamesrv captures present (57 on the full green run).
LEDGER = checks.Ledger("the approach (ROUTE-A, ROUTE-B, RANGERLOOP-F9)", floor=39)
check = checks.adopt(LEDGER)

PLAYER, FOE, OTHER = authsrv.PLAYER_AGENT_ID, 10, 11
OP_START, OP_INT, OP_HALT, OP_FOLLOW = 0x00A0, 0x009F, 0x0028, 0x002A
OP_LAUNCH, OP_TICK, OP_REPIN = 0x00A4, 0x001E, 0x002C
MOVE_C2S = (0x003D, 0x003E, 0x0047)

# (stamp, client port, own agent) -- the four connections whose player shoots
RANGED = (("20260929T150923", "55934", 31), ("20260914T005758", "56011", 29),
          ("20260810T235916", "61624", 31), ("20260807T143055", "62994", 31))
FOLLOW_FIRST = {"55934": [335.0923, 338.0686, 379.4129, 453.5679, 515.4825],
                "56011": [169.8902, 223.5783, 361.9119, 363.9707, 583.1255],
                "61624": [95.4709], "62994": [82.7741]}
# what ends each of those holds: its first own [8, me, 0], by what it rides (first_release)
RELEASE_FIRST = {"keyboard": [461.5991, 171.2864, 224.8611, 362.1789, 365.3111, 584.6648,
                              99.8772],
                 "re-approach": [337.5687], "skill": [338.1238, 517.4328],
                 "death": [384.3644, 86.2717]}
CONTROL_STAMP = "20260929T150923"
MELEE = ("20260929T150923", "53756", 9)

SAVED = ("PLAYER_WEAPON", "PLAYER_OFFHAND")
SAVED_A = ("ATTACK_INTERVAL", "WEAPON_ATTACK_SPEED", "PLAYER_SWING_DAMAGE",
           "APPROACH_START_HALTS", "LANDING_HOLD_RELEASE", "ATTACK_START_HOLDS")


class Globals:
    """Put back every global section 1 moves (the weapon and the arms)."""

    def __enter__(self):
        self.a = {k: getattr(agents, k) for k in SAVED}
        self.s = {k: getattr(authsrv, k) for k in SAVED_A}
        return self

    def __exit__(self, *exc):
        for k, v in self.a.items():
            setattr(agents, k, v)
        for k, v in self.s.items():
            setattr(authsrv, k, v)
        return False


def collect():
    sent = []
    return sent, (lambda op, v, label="", quiet=False: sent.append((op, list(v))))


def ops(sent):
    return [op for op, _v in sent]


def show(sent):
    return [(hex(op), v) for op, v in sent]


def world(distance):
    entry = {"name": "suit", "dead": False, "died_at": 0.0,
             "health": 9000.0, "max_health": 9000.0, "last_hit": 0.0,
             "pos": (float(distance), 0.0), "plane": 0, "armor_rating": 60.0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": False, "skills": (), "skill_ready": []}
    return {"agents": {FOE: entry}, "pos": (0.0, 0.0), "player_health": 480.0}


def age_leg(st):
    """Time passes: the follow's leg (and its record) end now, and the server's copy
    stands at the leg's end -- the integrator's own arrival."""
    dt = (st["click_leg"]["eta"] - time.time()) + 0.01
    for k in ("t0", "eta"):
        st["click_leg"][k] -= dt
    for k in ("t0", "eta", "sent_at"):
        st["approach"][k] -= dt
    st["click_moving_at"] -= dt
    st["pos"] = tuple(st["click_leg"]["dest"])
    st["dest"] = None


def approach(weapon, distance=2000.0):
    """A press on FOE `distance` out with `weapon`, then its arrival.
    -> (state, send, what the press sent, what the arrival tick sent)."""
    authsrv.apply_party_character({"player_weapon": weapon})
    st = world(distance)
    sent, send = collect()
    authsrv.begin_attack(send, st, FOE, 1)
    authsrv.attack_tick(send, st, 1)
    pressed = list(sent)
    sent.clear()
    if st.get("approach") is not None:
        age_leg(st)
    authsrv.attack_tick(send, st, 1)
    return st, send, sent, pressed


def land(st, send, sent):
    """The armed swing's windup passes: what the landing tick sends."""
    sent.clear()
    st["player_swing"]["lands_at"] -= 30.0
    authsrv.attack_tick(send, st, 1)
    return list(sent)


def retail_batch(me, target):
    return [(OP_START, [4, me, target, 0]), (OP_INT, [8, me, 1]), (OP_HALT, [me])]


def substitute(batch, me, target):
    """Our batch with retail's ids: the player -> me, FOE -> target."""
    out = []
    for op, v in batch:
        v = list(v)
        if op == OP_START:
            v[1], v[2] = me, target
        elif op == OP_INT:
            v[1] = me
        elif op == OP_HALT:
            v[0] = me
        out.append((op, v))
    return out


# --------------------------------------------------------------------------- 1
def section_server():
    print("\n1. ROUTE-A on our server: the ranged approach's start batch, its hold, its end")
    batches = {}
    with Globals():
        st, send, at_start, pressed = approach("starter_bow")
        batches["good"] = list(at_start)
        check(ops(pressed) == [OP_FOLLOW] and pressed[0][1][4] == FOE,
              "1a. the press from 2000 u with a bow is answered by ONE 0x002A [me, the "
              "target's point, 0, 0, target] -- the follow, unchanged", show(pressed))
        check(at_start == retail_batch(PLAYER, FOE),
              "1b. AT ARRIVAL the start is exactly 0x00A0 [4, me, T, 0], 0x009F [8, me, 1], "
              "0x0028 [me], in that order -- retail's batch (12 of 12)", show(at_start))
        check(st.get("approach_hold") is True and st.get("action_hold") == 1
              and "approach_closed" not in st,
              "1c. the hold is recorded as the APPROACH's, and the arrival marker is "
              "consumed by the start that used it",
              f"approach_hold {st.get('approach_hold')}, closed {st.get('approach_closed')}")
        at_launch = land(st, send, at_start)
        check(ops(at_launch) == [OP_LAUNCH],
              "1d. the launch releases NOTHING: 0x00A4 alone, no [8, me, 0] -- retail keeps "
              "the approach's hold through the launch (0 of 10)", show(at_launch))
        sent_next = []
        st["player_last_swing"] -= 100.0
        send_next = lambda op, v, label="", quiet=False: sent_next.append((op, list(v)))  # noqa: E731
        authsrv.attack_tick(send_next, st, 1)
        check(sent_next == [(OP_START, [4, PLAYER, FOE, 0])],
              "1e. the chain's NEXT start is [4] alone -- the hold is transition-only and "
              "nothing re-halts (retail :55934 381.8887, 456.0487)", show(sent_next))

        # 1f: the re-approach -- the target walks out of range mid-chain
        st["player_swing"] = None
        st["agents"][FOE]["pos"] = (5000.0, 0.0)
        st["approach_hold"], st["action_hold"] = True, 1
        re_sent, re_send = collect()
        authsrv.attack_tick(re_send, st, 1)
        seq = ops(re_sent)
        k = next((i for i, (op, v) in enumerate(re_sent)
                  if op == OP_INT and v == [8, PLAYER, 0]), None)
        check(k is not None and k + 1 < len(seq) and seq[k + 1] == OP_FOLLOW
              and seq.count(OP_FOLLOW) == 1 and "approach_hold" not in st,
              "1f. a RE-APPROACH releases the hold first, adjacent to its 0x002A: [8, me, 0] "
              "then 0x002A (retail :55934 337.5687), and the hold is no longer the approach's",
              show(re_sent))
        # 1g: that re-approach's own start, however long the interval holds it
        st["player_last_swing"] = time.time()
        age_leg(st)
        wait_sent, wait_send = collect()
        authsrv.attack_tick(wait_send, st, 1)
        held_closed = st.get("approach_closed")
        st["player_last_swing"] -= 100.0
        authsrv.attack_tick(wait_send, st, 1)
        check(held_closed == FOE and wait_sent == retail_batch(PLAYER, FOE),
              "1g. the mid-chain re-approach's start carries the batch too, after waiting on "
              "the swing interval (retail's 338.0686 is one, 0.5 s after its re-approach)",
              f"closed while waiting {held_closed}; {show(wait_sent)}")
        # 1h: a re-path is the same follow and releases nothing
        st["approach_hold"], st["action_hold"] = True, 1
        rp_sent, rp_send = collect()
        authsrv._approach_send(rp_send, st, 1, FOE, st["agents"][FOE], time.time(),
                               repath=True)
        check(ops(rp_sent) == [OP_FOLLOW] and st.get("approach_hold") is True,
              "1h. a RE-PATH (the target moved, the same follow re-issued) releases nothing",
              show(rp_sent))
        # 1i: a keyboard move ends it (7 of retail's 12 first releases, 3i)
        mv_sent, mv_send = collect()
        authsrv.cancel_on_move(mv_send, st, 1, moved=50.0)
        check((OP_INT, [8, PLAYER, 0]) in mv_sent and "approach_hold" not in st
              and st.get("action_hold") == 0,
              "1i. a MOVE releases it: cancel_on_move sends [8, me, 0] and forgets the "
              "approach's hold (retail :55934 461.5991, answering the c2s 0x003D at "
              "461.5639; :56011 171.2864, answering 171.2508)",
              show(mv_sent))

        # 1j: the launch gate reads the APPROACH's hold, not any hold
        other, other_sent = world(800.0), []
        other["action_hold"] = 1
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        authsrv._land_player_swing(lambda op, v, label="", quiet=False:
                                   other_sent.append((op, list(v))), other, 1,
                                   {"target": FOE})
        check(ops(other_sent) == [OP_LAUNCH, OP_INT] and other_sent[1][1] == [8, PLAYER, 0],
              "1j. CONTROL: a hold that is NOT the approach's still ends at the launch "
              "(test_weapons section 5's [8, me, 0]) -- the exemption is the approach's alone",
              show(other_sent))

        # 1k: the known-bad arm
        authsrv.APPROACH_START_HALTS = False
        authsrv.ATTACK_START_HOLDS = False   # 1z-ds.31's start hold off too: the old build
        st_b, _send_b, bad, _p = approach("starter_bow")
        batches["bad"] = list(bad)
        check(bad == [(OP_START, [4, PLAYER, FOE, 0])] and not st_b.get("approach_hold")
              and "approach_closed" not in st_b,
              "1k. KNOWN-BAD, --no-approach-start-halt --no-attack-start-hold: [4] alone, no "
              "hold, no halt -- this server before RANGERPRE-S16, which retail's 12 of 12 refute",
              show(bad))
        authsrv.APPROACH_START_HALTS = True
        authsrv.ATTACK_START_HOLDS = True

        # 1l-1n: the controls
        _st, _s, sword, sword_press = approach("starter_sword")
        check(ops(sword_press) == [OP_FOLLOW]
              and sword == [(OP_START, [4, PLAYER, FOE, 0]), (OP_INT, [8, PLAYER, 1])]
              and not _st.get("approach_hold") and _st.get("press_hold") is True,
              "1l. CONTROL, melee: a sword's approach arrives and its start is [4], [8, me, 1] "
              "with NO 0x0028 and no approach hold -- RE-AIMED 2026-10-02 (MOVECODE-1z-ds.31: "
              "retail's melee walk-ins are held 75 of 75; the 'mixed' read counted transitions)",
              show(sword))
        st_n, _s, near, near_press = approach("starter_bow", distance=800.0)
        check(near_press == [(OP_START, [4, PLAYER, FOE, 0]), (OP_INT, [8, PLAYER, 1])]
              and near == [] and not st_n.get("approach_hold"),
              "1m. CONTROL, at rest: a bow press already in range opens [4], [8, me, 1] -- no "
              "approach, no halt. RE-AIMED 2026-10-02 (MOVECODE-1z-ds.31): '37 of 37 carry "
              "neither' counted transitions; the state is held on every one",
              show(near_press))
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        st_o = world(800.0)
        st_o["approach_closed"] = OTHER
        o_sent, o_send = collect()
        authsrv.begin_attack(o_send, st_o, FOE, 1)
        authsrv.attack_tick(o_send, st_o, 1)
        check(o_sent == [(OP_START, [4, PLAYER, FOE, 0]), (OP_INT, [8, PLAYER, 1])]
              and "approach_closed" not in st_o and not st_o.get("approach_hold"),
              "1n. an arrival marker naming ANOTHER target halts nothing (the start's own hold, "
              "no 0x0028, no approach hold), and the start consumes it anyway", show(o_sent))
        gone = {"approach": None, "approach_closed": FOE}
        authsrv._approach_abandon(gone)
        check("approach_closed" not in gone and gone["approach"] is None,
              "1o. _approach_abandon forgets an arrived-but-unopened approach even with no "
              "follow on record (it pops BEFORE its early return): a body that moved or "
              "clicked since is not standing where the follow left it", str(gone))
        rel = {"approach_hold": True, "action_hold": 0}
        rel_sent, rel_send = collect()
        authsrv.action_hold(rel_send, rel, 0, "t")
        check(rel_sent == [] and "approach_hold" not in rel,
              "1p. action_hold(0) forgets the approach's hold even when the flag is "
              "already clear (it sends nothing -- transition-only -- and still forgets)",
              show(rel_sent))
        held_sent, held_send = collect()
        authsrv.action_hold(held_send, {"approach_hold": True, "action_hold": 0}, 1, "t")
        check(held_sent == [(OP_INT, [8, PLAYER, 1])],
              "1q. and a SET leaves it alone (only a release forgets it)", show(held_sent))
        # 1r: the target's death ends it (2 of retail's 12 first releases, 3i). The skill
        # press (2 more) is the press's own action_hold(0), and 1p shows the pop does not
        # depend on which site calls it.
        st_d, send_d, start_d, _p = approach("starter_bow")
        launch_d = land(st_d, send_d, start_d)
        up = st_d.get("approach_hold") is True and ops(launch_d) == [OP_LAUNCH]
        st_d["agents"][FOE]["dead"] = True
        die_sent, die_send = collect()
        authsrv.attack_tick(die_send, st_d, 1)
        # RE-AIMED 2026-10-06 (DEATHWALK-D4): the release waits for the chain's next due
        # start -- this check's own retail witnesses come 0.79 s after the death, and
        # :62994 86.2717 is start + 1.7465, the next due start (1z-ds.50) -- so the
        # death tick sends nothing and the scheduled release is the [8, me, 0].
        pend_d = st_d.get("target_death_release") or {}
        quiet = die_sent == [] and pend_d.get("cell") == "next-start"
        if pend_d:
            pend_d["at"] = time.time() - 0.001
        rel_d, rel_send_d = collect()
        authsrv.attack_tick(rel_send_d, st_d, 1)
        check(up and quiet and rel_d == [(OP_INT, [8, PLAYER, 0])]
              and "approach_hold" not in st_d and st_d.get("action_hold") == 0,
              "1r. the TARGET'S DEATH releases it: after the launch nothing goes out on the "
              "death tick, and at the chain's next due start the scheduled release sends "
              "[8, me, 0] and forgets the approach's hold (retail :55934 384.3644, 0.79 s "
              "after agent 46 dies; :62994 86.2717 = start + 1.7465; DEATHWALK-D4)",
              f"held through the launch {up}; death {show(die_sent)}; release {show(rel_d)}")
    return batches


# --------------------------------------------------------------------------- 2
def section_flag():
    print("\n2. the flag: --no-approach-start-halt, main()'s rebind, the default")
    import serverargs
    ap = serverargs.build_parser(
        doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST, GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
        HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING, TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
        GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
        VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
    src = open(authsrv.__file__, encoding="utf-8").read()
    i_main = src.find("\ndef main():")
    i_flip = src.find("    if a.no_approach_start_halt:", i_main)
    check(ap.parse_args([]).no_approach_start_halt is False
          and ap.parse_args(["--no-approach-start-halt"]).no_approach_start_halt is True
          and 0 < i_main < i_flip
          and "APPROACH_START_HALTS = False" in src[i_flip:i_flip + 120],
          "2a. the revert parses (default off) and main() flips APPROACH_START_HALTS")
    check(authsrv.APPROACH_START_HALTS is True
          and "APPROACH_START_HALTS" in authsrv.capture_flags(),
          "2b. the default is ON, and the capture header records which arm ran")
    i_tick = src.find("\ndef attack_tick(")
    i_start = src.find('f"attack_started: player swings at {target_id}")', i_tick)
    i_pop = src.find('_closed = state.pop("approach_closed", None)', i_tick)
    i_eng = src.find('leader_engaged(state, target_id, now, "swing")', i_tick)
    check(0 < i_tick < i_start < i_pop < i_eng,
          "2c. the halt sits in attack_tick directly behind the [4] send and ahead of "
          "everything else the start does", f"{i_tick} {i_start} {i_pop} {i_eng}")


# --------------------------------------------------------------------------- 3
def own_starts(merged, me):
    """Every own attack start [4, me, T, 0] on a decoded connection, classified by the
    body's last own movement event before it -- 'follow-first' (a server 0x002A follow,
    and this the first start since), 'rest' (a c2s 0x0047 or a server 0x0028 / 0x002C,
    or none yet), 'other' -- with its wire segment's s2c messages in stream order and,
    when its swing launched without a stop, the launch's segment."""
    out = []
    state, fresh = "rest", False
    for i, (t, d, op, v) in enumerate(merged):
        if d == "s2c" and op == OP_START and v[1] == 4 and v[2] == me:
            seg = [(op2, list(v2)[1:]) for t2, d2, op2, v2 in merged
                   if d2 == "s2c" and t2 == t]
            launch = None
            for t2, d2, op2, v2 in merged[i + 1:]:
                if t2 - t > 1.6:
                    break
                if d2 == "s2c" and op2 == OP_INT and v2[1] == 3 and v2[2] == me:
                    break                                   # the swing was stopped
                if d2 == "s2c" and op2 == OP_LAUNCH and v2[1] == me:
                    launch = [(op3, list(v3)[1:]) for t3, d3, op3, v3 in merged
                              if d3 == "s2c" and t3 == t2]
                    break
            klass = ("follow-first" if state == "follow" and fresh
                     else "rest" if state == "rest" else "other")
            out.append({"t": round(t, 4), "target": v[3], "klass": klass, "seg": seg,
                        "launch": launch})
            fresh = False
        if d == "c2s" and op in MOVE_C2S:
            fresh, state = True, ("rest" if op == 0x0047 else "moving")
        elif d == "s2c" and op in (OP_HALT, OP_REPIN) and v[1] == me:
            fresh, state = True, "rest"
        elif d == "s2c" and op == OP_FOLLOW and v[1] == me:
            fresh, state = True, "follow"
        elif d == "s2c" and op == 0x0029 and v[1] == me:
            fresh, state = True, "route"
    return out


def batch_of(seg, me):
    """The start / hold / halt messages of one segment, and whether a 0x001E sits between
    the hold and the halt. -> (list of (op, values), tick_between)."""
    k_s = next((k for k, (op, w) in enumerate(seg) if op == OP_START and w[:2] == [4, me]), None)
    k_h = next((k for k, (op, w) in enumerate(seg) if op == OP_INT and w == [8, me, 1]), None)
    k_x = next((k for k, (op, w) in enumerate(seg) if op == OP_HALT and w == [me]), None)
    picked = [seg[k] for k in sorted(x for x in (k_s, k_h, k_x) if x is not None)]
    tick = (None not in (k_h, k_x) and k_h < k_x
            and any(op == OP_TICK for op, _w in seg[k_h:k_x]))
    return picked, tick


def first_release(merged, me, t_start, target):
    """What ends the hold a start set: the first own [8, me, 0] after it, classified by
    what it rides, tested in this order -- 're-approach' (its segment carries the
    player's new 0x002A), 'keyboard' (its segment carries the player's 0x0029 leg and a
    c2s 0x003D lies under 0.1 s ahead), 'skill' (a c2s 0x0027 under 0.1 s ahead),
    'death' (the target's 0x0026 [T, 8] between the start and it), else 'other'.
    -> (kind, t), or ('none', None) when no release follows."""
    k = next((i for i, (t, d, op, v) in enumerate(merged)
              if t > t_start and d == "s2c" and op == OP_INT
              and list(v)[1:] == [8, me, 0]), None)
    if k is None:
        return "none", None
    t = merged[k][0]
    seg = [(op, list(v)[1:]) for t2, d, op, v in merged if d == "s2c" and t2 == t]
    ahead = [op for t2, d, op, _v in merged if d == "c2s" and t - 0.1 <= t2 <= t]
    if any(op == OP_FOLLOW and w[0] == me for op, w in seg):
        kind = "re-approach"
    elif any(op == 0x0029 and w[0] == me for op, w in seg) and 0x003D in ahead:
        kind = "keyboard"
    elif 0x0027 in ahead:
        kind = "skill"
    elif any(d == "s2c" and op == 0x0026 and list(v)[1:3] == [target, 8]
             for t2, d, op, v in merged if t_start < t2 <= t):
        kind = "death"
    else:
        kind = "other"
    return kind, round(t, 4)


def decode(stamp, port):
    import livewire
    capdir = vaultpath.require_dir("captures", "live", stamp)
    fn = [f for f in sorted(os.listdir(capdir))
          if f.startswith("game-") and f"_{port}-to-" in f]
    if len(fn) != 1:
        raise RuntimeError(f"{stamp}: {len(fn)} game connections on port {port}")
    return livewire.decode_conn(capdir, fn[0])


def section_tape(batches):
    print("\n3. THE TAPES: the census, OURS == RETAIL, the launches, the controls")
    if not os.path.isdir(vaultpath.vault_path("captures", "live")):
        LEDGER.skip("the tapes", f"no {vaultpath.vault_path('captures', 'live')} "
                                 "(bare machine)")
        return
    import adrenjoin
    rows, idents, releases = [], [], {}
    for stamp, port, me in RANGED:
        conn, merged, ok = decode(stamp, port)
        who = adrenjoin.whose_agent([(t, op, v) for t, d, op, v in merged if d == "s2c"])
        idents.append((port, ok, who))
        firsts = [s for s in own_starts(merged, who) if s["klass"] == "follow-first"]
        rows += [(port, me, s) for s in firsts]
        for s in firsts:
            kind, t_rel = first_release(merged, who, s["t"], s["target"])
            releases.setdefault(kind, []).append(t_rel)
    found = {}
    for port, _me, s in rows:
        found.setdefault(port, []).append(s["t"])
    check(all(ok and who == me for (_p, ok, who), (_s, _p2, me) in zip(idents, RANGED))
          and found == FOLLOW_FIRST,
          "3a. the four shooting connections decode whole, the own agent is 31 / 29 / 31 / "
          "31, and the first starts after a follow are exactly the twelve named",
          f"{idents} {found}")
    shaped, ticked, ours_eq, bad_eq = 0, 0, 0, 0
    for _port, me, s in rows:
        picked, tick = batch_of(s["seg"], me)
        want = retail_batch(me, s["target"])
        shaped += picked == want
        ticked += bool(tick)
        ours_eq += substitute(batches["good"], me, s["target"]) == picked
        bad_eq += substitute(batches["bad"], me, s["target"]) == picked
    check(shaped == len(rows) == 12,
          "3b. RETAIL: each of the 12 carries 0x00A0 [4, me, T, 0] < 0x009F [8, me, 1] < "
          "0x0028 [me] in its own segment", f"{shaped} of {len(rows)}")
    check(ticked == 12,
          "3c. RETAIL, recorded and NOT reproduced: a 0x001E tick sits between the hold and "
          "the halt on all 12 (retail's halt is one simulation tick behind; ours rides the "
          "start's own tick)", f"{ticked} of 12")
    check(ours_eq == 12,
          "3d. OURS == RETAIL: section 1's start batch with retail's ids substituted equals "
          "the tape's three messages on 12 of 12", f"{ours_eq} of 12")
    check(bad_eq == 0,
          "3e. KNOWN-BAD: the --no-approach-start-halt batch ([4] alone) matches 0 of 12",
          f"{bad_eq} of 12")
    launched = [s for _p, _m, s in rows if s["launch"] is not None]
    released = [s["t"] for p, me, s in rows if s["launch"] is not None
                and any(op == OP_INT and w == [8, me, 0] for op, w in s["launch"])]
    check(len(launched) == 10 and released == [],
          "3f. the launches: 10 of the 12 swings launched (338.0686 and 361.9119 were "
          "stopped first), and none of the 10 launch segments carries [8, me, 0] -- ours "
          "(1d) releases nothing there either", f"launched {len(launched)}, released {released}")
    import livewire
    capdir = vaultpath.require_dir("captures", "live", CONTROL_STAMP)
    rest, rest_clean, all_ok = 0, 0, True
    for fn in sorted(os.listdir(capdir)):
        if not fn.startswith("game-"):
            continue
        _c, merged, ok = livewire.decode_conn(capdir, fn)
        all_ok = all_ok and ok
        me = adrenjoin.whose_agent([(t, op, v) for t, d, op, v in merged if d == "s2c"])
        if me is None:
            continue
        for s in own_starts(merged, me):
            if s["klass"] != "rest":
                continue
            rest += 1
            picked, _tick = batch_of(s["seg"], me)
            rest_clean += picked == [(OP_START, [4, me, s["target"], 0])]
    check(all_ok and rest == rest_clean == 37,
          "3g. CONTROL: every start with the body at rest on 20260929T150923 carries "
          "neither the hold nor the halt -- 37 of 37", f"{rest_clean} of {rest}, ok {all_ok}")
    stamp, port, me = MELEE
    _c, merged, ok = decode(stamp, port)
    melee = [batch_of(s["seg"], me)[0] for s in own_starts(merged, me)
             if s["klass"] == "follow-first"]
    kinds = sorted(tuple(op for op, _w in b) for b in melee)
    check(ok and kinds == [(OP_START,), (OP_START,), (OP_START, OP_INT),
                           (OP_START, OP_INT, OP_HALT)],
          "3h. WHY RANGED ONLY: :53756's melee approach starts are mixed -- neither twice, "
          "the hold alone once, both once -- so the rule is not melee's",
          f"{[[hex(o) for o in k] for k in kinds]}")
    check(releases == RELEASE_FIRST,
          "3i. what ENDS the hold: the first own [8, me, 0] after each of the 12 starts "
          "answers a keyboard report 7 times (:55934 461.5991 among them), a re-approach "
          "once (337.5687), a skill press twice (338.1238, 517.4328) and the target's death "
          "twice (:55934 384.3644, :62994 86.2717) -- never the launch. Ours releases at "
          "each through action_hold(0) (1i, 1f, the press, 1r). 339.4568 is NOT one: it "
          "ends 338.1238's skill hold", str(releases))


# --------------------------------------------------------------------------- 4
NPC, NPC_AT = 99, (1000.0, 0.0)
OP_SPEED, OP_LEG = 0x002B, 0x0029


class OpenPM:
    """An open field on plane 0: every point walkable, every line clear, every route one
    straight leg -- the router's verbatim answer. `wall_x`, when set, is a line the mesh
    ends at: route() finds nothing past it and the rays stop on it, so the router's
    clip-fallback grants the leg only that far -- the approach point off our mesh, the
    shape that strands a disc-only serve."""

    def __init__(self, wall_x=None):
        self.wall_x = wall_x

    def walkable(self, x, y):
        return self.wall_x is None or x <= self.wall_x

    def containing(self, x, y):
        return [1] if self.walkable(x, y) else []

    def plane_at(self, x, y, prefer=None):
        return 0

    def clip(self, x0, y0, x1, y1, step=16.0):
        if self.wall_x is not None and x1 > self.wall_x >= x0:
            f = (self.wall_x - x0) / (x1 - x0)
            return (self.wall_x, y0 + f * (y1 - y0))
        return (x1, y1)

    def seam_clip(self, x0, y0, x1, y1, plane, step=2.0):
        return self.clip(x0, y0, x1, y1, step)

    def nearest_walkable(self, x, y, radius):
        return (x, y, 0.0) if self.walkable(x, y) else None

    def route(self, x0, y0, x1, y1, start_plane=None, goal_plane=None,
              with_planes=False):
        if not (self.walkable(x0, y0) and self.walkable(x1, y1)):
            return None
        pts = [(x0, y0), (x1, y1)]
        return (pts, [0, 0]) if with_planes else pts


def talk_world(pm=None, pos=(0.0, 0.0)):
    """The state the interact path reads, the NPC 1000 u out on +x."""
    st = {"pos": tuple(pos), "plane": 0, "agent_pos": {NPC: NPC_AT}, "agents": {},
          "quests": set(), "objectives_done": set(), "desc_sent": set(),
          "kbd_moving_at": None}
    if pm is not None:
        st["pathmap"] = pm
    return st


def gap(st):
    return math.hypot(NPC_AT[0] - st["pos"][0], NPC_AT[1] - st["pos"][1])


def drive(st, send, ticks=600):
    """world_tick's order, tick by tick: interact_pending_tick, then the integrator's step
    toward `dest` (DEFAULT_RUN_SPEED x TICK_SECONDS; arrival lands ON dest and clears it).
    -> the model's distance from the NPC when the hold was served, or None."""
    step = authsrv.DEFAULT_RUN_SPEED * authsrv.TICK_SECONDS
    for _ in range(ticks):
        authsrv.interact_pending_tick(send, st, 1)
        if st.get("pending_interact") is None:
            return gap(st)
        dest = st.get("dest")
        if not dest:
            continue
        px, py = st["pos"]
        dx, dy = dest[0] - px, dest[1] - py
        d = math.hypot(dx, dy)
        if d <= step:
            st["pos"], st["dest"] = tuple(dest), None
        else:
            st["pos"] = (px + dx / d * step, py + dy / d * step)
    return None


def press(pm, pos=(0.0, 0.0)):
    """A click on NPC from `pos`. -> (state, send, what the press sent)"""
    st = talk_world(pm, pos)
    sent, send = collect()
    authsrv._handle_interact(send, st, 1, NPC)
    return st, send, sent


def section_route_b_server():
    print("\n4. ROUTE-B on our server: where a held interact is served")
    # Run under the arm in force (the module default), so a known-bad module flip
    # reddens the headlines; 4d / 4e set each arm themselves and put it back.
    saved = authsrv.HELD_INTERACT_AT_DISC
    try:
        disc = authsrv.follow_stop_radius() + authsrv.INTERACT_DISC_SLACK
        p = authsrv.interact_approach_point(NPC_AT, (0.0, 0.0))
        check(authsrv.INTERACT_STOP == authsrv.follow_stop_radius() == 80.0
              and authsrv.interact_stop() == authsrv.INTERACT_STOP
              and p == (NPC_AT[0] - 80.0, 0.0) and disc == 81.0,
              "4a. the interact walk stops at the FOLLOW DISC: INTERACT_STOP == "
              "follow_stop_radius() == 80 u (12 + 12 + 56), the approach point 80 u short, "
              "and the serve disc 81 u", f"stop {authsrv.INTERACT_STOP}, point {p}, disc {disc}")

        st, send, sent = press(OpenPM())
        check(ops(sent) == [OP_SPEED, OP_LEG] and sent[1][1][1] == [920.0, 0.0]
              and st.get("pending_interact") == (NPC, 0) and st.get("dest") == (920.0, 0.0)
              and st.get("interact_walk") == st.get("click_moving_at") is not None
              and authsrv.interact_walk_live(st),
              "4b. a press from 1000 u on an open field is HELD and walked: 0x002B then "
              "0x0029 [me, (920, 0)] -- the router's verbatim leg to the disc -- and the walk "
              "is recorded as the click latch's stamp and live", show(sent))
        served = drive(st, send)
        check(served is not None and abs(served - 80.0) < 1e-6
              and st.get("interacting") == NPC,
              "4c. HEADLINE: driven tick by tick, the hold is served when the model reaches "
              "the walk's end, 80.0 u -- NOT on the way in: every in-flight tick inside "
              "144 u serves nothing (retail: 67.8 / 75.2 u, section 5)", f"served at {served}")

        authsrv.HELD_INTERACT_AT_DISC = False
        st_b, send_b, sent_b = press(OpenPM())
        served_b = drive(st_b, send_b)
        check(sent_b[1][1][1] == [900.0, 0.0] and served_b is not None
              and 144.0 - 14.4 < served_b <= 144.0,
              "4d. KNOWN-BAD, --held-interact-at-range: the walk stops 100 u short and the "
              "hold is served at the first tick inside INTERACT_RANGE -- this server until "
              "today; retail's dialog comes 0.24-0.26 s later than that rule puts it",
              f"leg {sent_b[1][1][1]}, served at {served_b}")

        # 4e: the spec's direct check -- the model 100 u out, the walk still in flight
        arms = {}
        for arm in (True, False):
            authsrv.HELD_INTERACT_AT_DISC = arm
            st_e, send_e, _s = press(OpenPM())
            st_e["pos"] = (900.0, 0.0)
            authsrv.interact_pending_tick(send_e, st_e, 1)
            arms[arm] = st_e.get("pending_interact") is None
        check(arms == {True: False, False: True},
              "4e. the model 100 u out with the walk in flight is NOT served; the known-bad "
              "arm serves it there", f"served {arms}")
        authsrv.HELD_INTERACT_AT_DISC = saved

        # 4f-4h: the slack (the critic's ERROR against a disc-only serve)
        st_f, send_f, sent_f = press(OpenPM(wall_x=890.0))
        served_f = drive(st_f, send_f)
        check(sent_f[1][1][1] == [890.0, 0.0] and served_f is not None
              and abs(served_f - 110.0) < 1e-6 and st_f.get("interacting") == NPC,
              "4f. SLACK, the router's word: the approach point is off our mesh, so the "
              "clip-fallback grants the leg only to (890, 0), 110 u out, 29 u outside the "
              "disc -- and the hold is served at the walk's END, not stranded (a disc-only "
              "serve never fires: this tick has no expiry)",
              f"leg {sent_f[1][1][1]}, served at {served_f}")
        st_g, send_g, _s = press(OpenPM())
        st_g["pos"], st_g["dest"], st_g["click_moving_at"] = (917.0, 0.0), None, None
        authsrv.interact_pending_tick(send_g, st_g, 1)
        check(st_g.get("pending_interact") is None and st_g.get("interacting") == NPC,
              "4g. SLACK, the client's word: a stop reported 3 u beyond the modelled end "
              "(83 u; the 0x0047 arm writes pos, clears dest and the click latch) is served "
              "on the next tick", f"pending {st_g.get('pending_interact')}")
        st_h, send_h, sent_h = press(OpenPM(wall_x=800.0))
        served_h = drive(st_h, send_h)
        check(sent_h[1][1][1] == [800.0, 0.0] and served_h is None
              and st_h.get("pending_interact") == (NPC, 0) and gap(st_h) == 200.0,
              "4h. a walk that ends BEYOND INTERACT_RANGE (200 u) keeps the hold, served by "
              "nothing, as it always was -- retail's expiry is unmeasured",
              f"served {served_h}, pending {st_h.get('pending_interact')}, at {gap(st_h)}")

        # 4i-4j: the controls
        st_i, send_i, sent_i = press(None)
        walked_i = list(sent_i)
        st_i["pos"] = (900.0, 0.0)
        authsrv.interact_pending_tick(send_i, st_i, 1)
        check(walked_i == [] and "interact_walk" not in st_i
              and st_i.get("interacting") == NPC,
              "4i. CONTROL, no mesh: no walk goes out and the hold is served at "
              "INTERACT_RANGE as before (100 u) -- test_interact section 3 unchanged",
              f"sent {show(walked_i)}, interacting {st_i.get('interacting')}")
        now_at = {}
        for d in (100.0, 134.6, 145.0):
            st_j, _send_j, sent_j = press(OpenPM(), pos=(NPC_AT[0] - d, 0.0))
            now_at[d] = (st_j.get("interacting") == NPC, OP_LEG in ops(sent_j),
                         st_j.get("pending_interact") is not None)
        check(now_at == {100.0: (True, False, False), 134.6: (True, False, False),
                         145.0: (False, True, True)},
              "4j. CONTROL, the IMMEDIATE range is untouched: presses from 100 u and from "
              "134.6 u (retail's :56025 780.6734) are served at once with nothing walked; "
              "one from 145 u is held and walked", str(now_at))

        import serverargs
        ap = serverargs.build_parser(
            doc="x", GAME_SRV_HOST=authsrv.GAME_SRV_HOST,
            GAME_SRV_PORT=authsrv.GAME_SRV_PORT,
            HOST_FIELD_ENCODING=authsrv.HOST_FIELD_ENCODING,
            TEST_SKILLBAR=authsrv.TEST_SKILLBAR,
            GRANT_MIN_INTERVAL=authsrv.GRANT_MIN_INTERVAL, PROF_WARRIOR=authsrv.PROF_WARRIOR,
            VAULT_DEFAULT=authsrv.VAULT_DEFAULT)
        src = open(authsrv.__file__, encoding="utf-8").read()
        i_main = src.find("\ndef main():")
        i_flip = src.find("    if a.held_interact_at_range:", i_main)
        check(ap.parse_args([]).held_interact_at_range is False
              and ap.parse_args(["--held-interact-at-range"]).held_interact_at_range is True
              and 0 < i_main < i_flip
              and "HELD_INTERACT_AT_DISC = False" in src[i_flip:i_flip + 120]
              and saved is True and "HELD_INTERACT_AT_DISC" in authsrv.capture_flags(),
              "4k. the revert --held-interact-at-range parses (default off), main() flips "
              "HELD_INTERACT_AT_DISC, the default is ON and the capture header records it")
    finally:
        authsrv.HELD_INTERACT_AT_DISC = saved


# --------------------------------------------------------------------------- 5
V_RUN = 288.0
# (stamp, port, own agent, press t, NPC, dialog t) -- the two exact-start held interacts
HELD_CORNER = ("20260929T150923", "56064", 9, 968.0936, 10, 979.1046)
HELD_LEGS = ("20260929T150923", "59969", 123, 190.9224, 40, 202.6552)
# (port, press t, NPC, the answer) -- exact 0x0047 stops answered at once, and the
# dead-reckoned press that was walked
IMMEDIATE = (("55934", 628.2476, 142), ("56025", 780.6734, 38))
WALKED = ("55934", 630.7047, 176)


def near(t, want, tol=0.0006):
    return abs(t - want) <= tol


def our_serve_radius():
    """The farthest a held interact is served from while its walk is still in flight,
    ASKED of interact_pending_tick itself (bisection to well under 0.01 u) rather than
    read off a constant -- so the arm in force is what gets compared with retail."""
    import contextlib
    import io
    lo, hi = 0.0, 1000.0                   # lo is served, hi is not
    for _ in range(40):
        mid = (lo + hi) / 2.0
        st = talk_world()
        st["pos"] = (NPC_AT[0] - mid, 0.0)
        st["pending_interact"] = (NPC, 0)
        st["interact_walk"] = st["click_moving_at"] = 1.0
        st["dest"] = (NPC_AT[0] - authsrv.INTERACT_STOP, 0.0)
        _sent, send = collect()
        with contextlib.redirect_stdout(io.StringIO()):
            authsrv.interact_pending_tick(send, st, 1)
        if st.get("pending_interact") is None:
            lo = mid
        else:
            hi = mid
    return lo


def where(merged, agent, before):
    """An agent's last announced position before `before`: its 0x0020 create's point,
    or a later 0x0029 / 0x002A / 0x002C naming it."""
    w = None
    for t, d, op, v in merged:
        if t >= before:
            break
        if d == "s2c" and op == 0x0020 and v[1] == agent:
            w = tuple(v[5])
        elif d == "s2c" and op in (0x0029, 0x002A, 0x002C) and v[1] == agent:
            w = tuple(v[2])
    return w


def crossing(p0, p1, npc, r):
    """How far along p0 -> p1 the body first comes within `r` of npc, or None."""
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    length = math.hypot(dx, dy)
    ux, uy = dx / length, dy / length
    fx, fy = p0[0] - npc[0], p0[1] - npc[1]
    b = fx * ux + fy * uy
    disc = b * b - (fx * fx + fy * fy - r * r)
    if disc < 0:
        return None
    s = -b - math.sqrt(disc)
    return s if 0.0 <= s <= length else None


def held_case(case, legs_want):
    """One exact-start held interact off the tape. -> dict, or a reason string."""
    stamp, port, me_want, t_press, npc, t_dlg = case
    _conn, merged, ok = decode(stamp, port)
    import adrenjoin
    me = adrenjoin.whose_agent([(t, op, v) for t, d, op, v in merged if d == "s2c"])
    pr = [r for r in merged if r[1] == "c2s" and r[2] == 0x0039 and near(r[0], t_press)]
    dlg = [r for r in merged if r[1] == "s2c" and r[2] == 0x0081 and near(r[0], t_dlg)]
    if not (ok and me == me_want and pr and pr[0][3][1] == npc and dlg
            and dlg[0][3][1] == npc):
        return f"ok {ok}, me {me}, press {pr[:1]}, dialog {dlg[:1]}"
    between = [r for r in merged if pr[0][0] < r[0] < dlg[0][0]]
    moves = [r for r in between if r[1] == "c2s" and r[2] in MOVE_C2S]
    legs = [r for r in between if r[1] == "s2c" and r[2] == 0x0029 and r[3][1] == me]
    fol = [r for r in between if r[1] == "s2c" and r[2] == OP_FOLLOW and r[3][1] == me]
    first_dlg = min((r[0] for r in between if r[1] == "s2c" and r[2] == 0x0081
                     and r[3][1] == npc), default=None)
    if moves or len(legs) != legs_want or first_dlg is not None:
        return f"moves {len(moves)}, legs {len(legs)}, an earlier dialog {first_dlg}"
    return {"merged": merged, "me": me, "legs": legs, "follow": fol, "t_dlg": dlg[0][0],
            "t_press": pr[0][0]}


def section_route_b_tape():
    print("\n5. ROUTE-B's TAPES: where retail serves a held interact, and the immediate range")
    if not os.path.isdir(vaultpath.vault_path("captures", "live")):
        LEDGER.skip("ROUTE-B's tapes", f"no {vaultpath.vault_path('captures', 'live')} "
                                       "(bare machine)")
        return
    serve_r = our_serve_radius()       # 81 u under ROUTE-B, 144 under the known-bad arm
    lead = {}                          # case -> (ours ms, known-bad ms) before the dialog

    a = held_case(HELD_CORNER, 4)
    corner = {}
    if isinstance(a, dict):
        prev, last = a["legs"][-2][3][2], a["legs"][-1][3][2]
        eta = a["legs"][-1][0] + math.hypot(last[0] - prev[0], last[1] - prev[1]) / V_RUN
        fol = a["follow"]
        spot = tuple(fol[0][3][2]) if fol else None
        if fol and list(fol[0][3][1:]) == [9, spot, 0, 0, 10] and spot == (21195.0, 13076.0):
            d0 = math.hypot(spot[0] - last[0], spot[1] - last[1])
            walk = a["t_dlg"] - fol[0][0]
            corner = {"eta_ms": round(1e3 * (fol[0][0] - eta), 1), "d0": round(d0, 1),
                      "at_dialog": round(d0 - V_RUN * walk, 1)}
            lead["56064"] = tuple(round(1e3 * (a["t_dlg"] - (fol[0][0] + (d0 - r) / V_RUN)), 1)
                                  for r in (serve_r, authsrv.INTERACT_RANGE))
    check(isinstance(a, dict) and len(a["follow"]) == 1 and corner
          and abs(corner["eta_ms"]) < 10.0 and corner["d0"] == 600.7,
          "5a. :56064 (own agent 9) decodes whole: the press at 968.0936 on agent 10 is "
          "walked by four 0x0029 corners, then 0x002A [9, (21195, 13076), 0, 0, 10] at "
          "977.2544 within 10 ms of the last corner's ETA -- the body at (21120, 12480), "
          "600.7 u out -- and the dialog 0x0081 [10] at 979.1046, no client movement between",
          f"{a if not isinstance(a, dict) else corner}")
    check(bool(corner) and 60.0 <= corner["at_dialog"] <= 85.0,
          "5b. :56064: the model stands 67.8 u from the NPC at the dialog -- inside the "
          "follow disc, far inside 144", f"{corner}")

    b = held_case(HELD_LEGS, 3)
    legs = {}
    if isinstance(b, dict):
        merged = b["merged"]
        stop = [r for r in merged if r[1] == "c2s" and r[2] == 0x0047
                and b["t_press"] - 1.5 < r[0] < b["t_press"]]
        after = [r for r in merged if stop and stop[-1][0] < r[0] < b["t_press"]
                 and r[1] == "c2s" and r[2] in MOVE_C2S]
        npc = where(merged, 40, b["t_press"])
        if stop and not after and npc == (11715.0, 3517.0):
            pts = [tuple(stop[-1][3][1])] + [tuple(r[3][2]) for r in b["legs"]]
            p0, p1 = pts[-2], pts[-1]
            length = math.hypot(p1[0] - p0[0], p1[1] - p0[1])
            s = (b["t_dlg"] - b["legs"][-1][0]) * V_RUN
            pos = (p0[0] + (p1[0] - p0[0]) * s / length, p0[1] + (p1[1] - p0[1]) * s / length)
            legs = {"stop_t": round(stop[-1][0], 4), "at_dialog": round(math.hypot(
                npc[0] - pos[0], npc[1] - pos[1]), 1), "short_of_end": round(length - s, 1),
                "end_to_npc": round(math.hypot(npc[0] - p1[0], npc[1] - p1[1]), 1)}
            cr = [crossing(p0, p1, npc, r) for r in (serve_r, authsrv.INTERACT_RANGE)]
            if None not in cr:
                lead["59969"] = tuple(round(1e3 * (b["t_dlg"] - (b["legs"][-1][0] + c / V_RUN)),
                                            1) for c in cr)
    check(bool(legs) and legs["stop_t"] == 189.9401 and 60.0 <= legs["at_dialog"] <= 85.0
          and legs["short_of_end"] > 30.0,
          "5c. :59969 (own agent 123): the press at 190.9224 on agent 40 (11715, 3517), from "
          "the EXACT 0x0047 stop at 189.9401, walked by three 0x0029 legs; at the dialog "
          "(202.6552) the model is 75.2 u from the NPC and still 42.3 u short of its last "
          "leg's end -- served ON THE WAY, a distance rule, not an arrival",
          f"{b if not isinstance(b, dict) else legs}")
    check(set(lead) == {"56064", "59969"}
          and all(0.0 <= ours <= 50.0 and bad >= 200.0 for ours, bad in lead.values()),
          "5d. OURS == RETAIL to one tick: our serve instant -- the model crossing the "
          f"radius interact_pending_tick itself serves from with a walk in flight "
          f"({serve_r:.1f} u) -- precedes retail's dialog by 0-50 ms on both (45.7, 20.0); "
          "KNOWN-BAD: the INTERACT_RANGE rule precedes it by >= 0.2 s on both (264.5, "
          "238.8)", f"(ours ms, known-bad ms) {lead}")

    import adrenjoin
    got = {}
    for port, t_press, npc in IMMEDIATE + (WALKED,):
        _c, merged, ok = decode("20260929T150923", port)
        me = adrenjoin.whose_agent([(t, op, v) for t, d, op, v in merged if d == "s2c"])
        pr = next(r for r in merged if r[1] == "c2s" and r[2] == 0x0039
                  and near(r[0], t_press))
        rep = [r for r in merged if r[1] == "c2s" and r[2] in (0x003D, 0x0047)
               and r[0] < pr[0]][-1]
        grants = [r for r in merged if rep[0] < r[0] < pr[0] and r[1] == "s2c"
                  and r[2] in (0x0029, OP_FOLLOW) and r[3][1] == me]
        body = tuple(rep[3][1])
        if rep[2] == 0x003D and grants:     # RECONSTRUCTION: along the report's own grant
            g = grants[-1][3][2]
            dd = math.hypot(g[0] - body[0], g[1] - body[1])
            f = min(1.0, (pr[0] - rep[0]) * V_RUN / dd) if dd else 0.0
            body = (body[0] + (g[0] - body[0]) * f, body[1] + (g[1] - body[1]) * f)
        w = where(merged, npc, pr[0])
        ans = next((r for r in merged if pr[0] < r[0] < pr[0] + 0.25 and r[1] == "s2c"
                    and ((r[2] in (0x0029, OP_FOLLOW) and r[3][1] == me)
                         or (r[2] == 0x0081 and r[3][1] == npc))), None)
        got[port + "@" + str(t_press)] = (
            ok, "stop" if rep[2] == 0x0047 and not grants else "reckoned",
            round(math.hypot(w[0] - body[0], w[1] - body[1]), 1),
            None if ans is None else (hex(ans[2]), round(ans[0] - pr[0], 3)))
    exact = [got[p + "@" + str(t)] for p, t, _n in IMMEDIATE]
    walked = got[WALKED[0] + "@" + str(WALKED[1])]
    check([e[:3] for e in exact] == [(True, "stop", 95.7), (True, "stop", 134.6)]
          and all(e[3] is not None and e[3][0] == "0x81" and e[3][1] < 0.06 for e in exact)
          and all(e[2] <= authsrv.INTERACT_RANGE for e in exact)
          and walked[3] is not None and walked[3][0] == "0x2a"
          and walked[2] > authsrv.INTERACT_RANGE,
          "5e. the IMMEDIATE range: presses from exact stops 95.7 u (:55934 628.2476) and "
          "134.6 u (:56025 780.6734) are answered with the dialog inside 60 ms and no walk, "
          "both inside INTERACT_RANGE; one from ~167 u (:55934 630.7047, RECONSTRUCTION -- "
          "dead-reckoned from a keyboard report 0.32 s old) is walked -- so 144 sits in "
          "(134.6, ~167]", str(got))


# --------------------------------------------------------------------------- 6
# RANGERLOOP-F9: our 0x0028 parks the AgTrack mirror. Sections 1-5 drive the server with
# no guard, so `_reach_frame` falls back to state["pos"] and the mirror never runs; these
# two seed the real guard and feed it exactly as the live send() choke does, on a fake
# clock (authsrv's `time` swapped for the block, as test_bodywindup does).
F9_T0 = 50000.0
F9_STEP = 0.05
F9_FLAGS = ("MIRROR_PARKS_ON_STOP", "SWING_CLOCK_CHARGES_MOVING",
            "CANCELLED_SWING_FREES_CLOCK")
F9_CAP = ("captures", "gamesrv", "authsrv-20260930T132022-c1.jsonl")   # S16 RUN-T, 131951


class F9Clock:
    """A fake `time` module for authsrv: the ticks and the guard read `time.time()`."""

    def __init__(self, t):
        self.t = t

    def time(self):
        return self.t

    def __getattr__(self, name):
        return getattr(time, name)


class F9Rec:
    def __init__(self):
        self.rows = []

    def event(self, kind, **kw):
        self.rows.append(dict(kw, kind=kind, t=authsrv.time.t - F9_T0))


@contextlib.contextmanager
def f9_rig(**flags):
    """The fake clock and the named flags for the block, the weapon globals too; all
    restored after. Server prints are swallowed: the checks print the numbers."""
    saved = {k: getattr(authsrv, k) for k in F9_FLAGS}
    saved_time = authsrv.time
    with Globals():
        for k, v in flags.items():
            setattr(authsrv, k, v)
        authsrv.time = F9Clock(F9_T0)
        try:
            with contextlib.redirect_stdout(io.StringIO()):
                yield
        finally:
            authsrv.time = saved_time
            for k, v in saved.items():
                setattr(authsrv, k, v)


def f9_world():
    """A bow, FOE 1800 u out on +x, the guard seeded at the origin, and a send that feeds
    _note_wire_move and _agtrack_shadow_emit as send()'s pre-lock hooks do.
    -> (state, rec, sent [(t, op, values)], send)"""
    authsrv.apply_party_character({"player_weapon": "starter_bow"})
    st = world(1800.0)
    st["plane"] = 0
    authsrv._agtrack_guard_seed(st, (0.0, 0.0), 0, 1)
    rec, sent = F9Rec(), []

    def send(op, v, label="", quiet=False):
        v = list(v)
        sent.append((authsrv.time.t - F9_T0, op, v))
        if op in (0x0029, OP_FOLLOW, OP_REPIN):
            authsrv._note_wire_move(st, op, v, authsrv.time.t, rec=rec)
        if authsrv.AGTRACK_SHADOW and st.get("agtrack_guard") is not None:
            authsrv._agtrack_shadow_emit(st, op, v, rec)
    return st, rec, sent, send


def f9_tick(st, rec, send, t):
    """One world tick at t (seconds after F9_T0), the guard's half first, as world_tick."""
    authsrv.time.t = F9_T0 + t
    authsrv._agtrack_shadow_tick(st, rec, send)
    authsrv.projectile_tick(send, st, 1)
    authsrv.attack_tick(send, st, 1, rec)


def f9_flight(v):
    """0x00A4's flight field: the f32's bits as the wire carries them."""
    return struct.unpack("<f", struct.pack("<I", int(v[3]) & 0xFFFFFFFF))[0]


def f9_drive(park):
    """The press, the approach, S16's halt, then 6.5 s of chain. -> dict of readings."""
    out = {"track": [], "probe": {}}
    with f9_rig(MIRROR_PARKS_ON_STOP=park):
        st, rec, sent, send = f9_world()
        authsrv.begin_attack(send, st, FOE, 1, rec=rec)
        how = authsrv.player_ranged(st)
        t, halt_t = 0.0, None
        while t < 8.0 - 1e-9:
            prev = authsrv._npc_mirror_pos(st, authsrv.time.t)
            t = round(t + F9_STEP, 6)
            f9_tick(st, rec, send, t)
            now = authsrv.time.t
            g = st.get("agtrack_guard")
            p = authsrv._npc_mirror_pos(st, now)
            out["track"].append((t, p, authsrv._reach_frame(st, now),
                                 g.twin.sync.position(g._ms(now)) if g else None))
            if halt_t is None:
                h = [s for s in sent if s[1] == OP_HALT]
                if h:
                    halt_t, out["halt_t"], out["halt_at"] = h[0][0], h[0][0], p
                    out["before_halt"] = prev
            for d in (1.1, 2.5):
                if (halt_t is not None and d not in out["probe"]
                        and abs(t - (halt_t + d)) < F9_STEP / 2):
                    shot = authsrv.launch_player_projectile(lambda *a, **k: None, st, 1,
                                                            {"target": FOE}, how)
                    st["player_projectiles"].remove(shot)
                    out["probe"][d] = shot["arrives_at"] - now
        out["sent"] = sent
        out["follow_t"] = next(s[0] for s in sent if s[1] == OP_FOLLOW)
        out["flights"] = [f9_flight(v) for _t, op, v in sent if op == OP_LAUNCH]
        out["avoid"] = [r for r in rec.rows
                        if r["kind"] == "kbd_leg" and r.get("act") == "avoid-halt"]
        out["n_avoid"] = st["agtrack_guard"].mirror.sync.n_avoid_halt
        out["speed"] = how["speed"]
    return out


def f9_reapproach(**flags):
    """RUN-T's re-approach on THIS tree, on the desk. After the third start, a keyboard
    move 33 ms into its windup (RUN-T's 0x003D came 33 ms after 16.8829), a 1.512 s
    back-pedal 281.7 u, the stop, and the re-press 1.86 s later. The keyboard arms' state
    writes are EMULATED (RECONSTRUCTION of the 0x003D/0x0047 arms: the latches, the stop
    report, and a 0x002C at the stop standing in for RUN-T's APPROACH RE-PIN); the cancel
    is the real cancel_on_move, and the swing clock is the real attack_tick. The body's
    point at the move is read off the mirror, so the drive needs MIRROR_PARKS_ON_STOP: under
    --no-mirror-stop that "body" is the walked-in mirror and the re-press is in reach.
    -> (late s past the re-approach's own eta, the mirror's distance to FOE at its halt)"""
    with f9_rig(MIRROR_PARKS_ON_STOP=True, **flags):
        st, rec, sent, send = f9_world()
        authsrv.begin_attack(send, st, FOE, 1, rec=rec)
        t = 0.0
        while len([s for s in sent if s[1] == OP_START]) < 3 and t < 20.0:
            t = round(t + F9_STEP, 6)
            f9_tick(st, rec, send, t)
        third = [s for s in sent if s[1] == OP_START][2][0]
        t = third + 0.033
        authsrv.time.t = F9_T0 + t
        body = authsrv._npc_mirror_pos(st, authsrv.time.t)
        st["kbd_moving_at"], st["click_moving_at"] = authsrv.time.t, None
        authsrv.cancel_on_move(send, st, 1, moved=50.0)
        stop_at = t + 1.512
        while t < stop_at:
            t = round(t + F9_STEP, 6)
            f9_tick(st, rec, send, t)
        stop = (body[0] - 281.7, body[1])
        st["kbd_moving_at"], st["dest"], st["pos"] = None, None, stop
        st["last_report"] = (stop[0], stop[1], True, authsrv.time.t)
        send(OP_REPIN, [PLAYER, list(stop), 0], "the stop, re-pinned (RUN-T's RE-PIN)")
        press_at = t + 1.86
        while t < press_at:
            t = round(t + F9_STEP, 6)
            f9_tick(st, rec, send, t)
        st["attack_press_at"] = authsrv.time.t
        authsrv.begin_attack(send, st, FOE, 1, rec=rec)
        pressed = t
        while t < pressed + 4.0:
            t = round(t + F9_STEP, 6)
            f9_tick(st, rec, send, t)
            if [s for s in sent if s[1] == OP_HALT and s[0] > pressed]:
                break
        fol = [s for s in sent if s[1] == OP_FOLLOW and s[0] > pressed]
        halt = [s for s in sent if s[1] == OP_HALT and s[0] > pressed]
        row = [r for r in rec.rows if r["kind"] == "approach" and r.get("act") == "send"
               and r["t"] > pressed - 1e-9]
        if not (fol and halt and row):
            return None, None
        m = authsrv._npc_mirror_pos(st, F9_T0 + halt[0][0])
        late = (halt[0][0] - fol[0][0]) - float(row[0]["run"]) / authsrv.DEFAULT_RUN_SPEED
        return late, math.hypot(1800.0 - m[0], m[1])


def section_mirror_stop():
    print("\n6. RANGERLOOP-F9 on our server: the halt's 0x0028 parks the AgTrack mirror")
    reach = 1498.0
    on, bad = f9_drive(True), f9_drive(False)
    ht = on.get("halt_t")
    hx = on.get("halt_at") or (math.inf, math.inf)
    d_halt = math.hypot(1800.0 - hx[0], hx[1])
    pre = on.get("before_halt") or (0.0, 0.0)
    d_pre = math.hypot(1800.0 - pre[0], pre[1])
    eta = (1800.0 - reach) / authsrv.DEFAULT_RUN_SPEED
    late = None if ht is None else ht - on["follow_t"] - eta
    check(ht is not None and reach - 15.0 <= d_halt <= reach < d_pre
          and late is not None and 0.0 <= late <= F9_STEP + 1e-6,
          "6a. THE W2g GUARD: the first swing still opens AT range -- the batch on the "
          "first tick the mirror is inside 1498 u (the tick before it was outside), at the "
          "leg's eta plus at most one tick; the park cannot move the start",
          {"halt_d": round(d_halt, 1), "prev_d": round(d_pre, 1),
           "late_s": None if late is None else round(late, 3)})
    after = [(t, p, fr, tw) for t, p, fr, tw in on["track"]
             if ht is not None and ht <= t <= ht + 5.0 + 1e-6]
    worst = max((math.hypot(p[0] - hx[0], p[1] - hx[1]) for _t, p, _f, _w in after),
                default=math.inf)
    frame_off = max((math.hypot(f[0] - p[0], f[1] - p[1]) for _t, p, f, _w in after),
                    default=math.inf)
    twin_off = max((math.hypot(w[0] - p[0], w[1] - p[1]) for _t, p, _f, w in after),
                   default=math.inf)
    check(len(after) >= 100 and worst <= 15.0 and frame_off < 1e-6 and twin_off < 1e-6,
          "6b. HEADLINE: for 5 s after the halt the mirror (_npc_mirror_pos) stays within "
          "15 u of where the halt found it, _reach_frame reads that same point, and the "
          "twin stands on it too -- the client's two copies stopped there",
          {"ticks": len(after), "worst_u": round(worst, 2), "frame_off": frame_off,
           "twin_off": twin_off})
    want = d_halt / on.get("speed", 1600.0)
    probes = on.get("probe", {})
    check(set(probes) == {1.1, 2.5}
          and all(abs(probes[d] - want) <= 0.05 * want for d in probes),
          "6c. launch_player_projectile's flight at the halt +1.1 s and +2.5 s is "
          "hypot(target - halt point) / speed within 5 % -- the arrow flies from where "
          "the body stands",
          {"want_s": round(want, 3), **{f"+{d}": round(v, 3) for d, v in probes.items()}})
    fl = on.get("flights", [])
    check(len(fl) >= 2 and all(abs(f - want) <= 0.05 * want for f in fl)
          and not on["avoid"] and on["n_avoid"] == 0,
          "6d. the chain's own launches agree (RUN-T's prediction: roughly constant, "
          "~0.93 s each), and no `kbd_leg avoid-halt` row fires after the halt -- the "
          "mirror never walks into the target's disc, so 1z-dj never re-parks the model",
          {"flights": [round(f, 3) for f in fl], "avoid_rows": len(on["avoid"])})
    bad_after = [p for t, p, _f, _w in bad["track"]
                 if bad.get("halt_t") is not None and abs(t - (bad["halt_t"] + 2.5)) < 0.026]
    walked = (math.hypot(bad_after[0][0] - bad["halt_at"][0], bad_after[0][1] - bad["halt_at"][1])
              if bad_after else 0.0)
    bp = bad.get("probe", {})
    bfl = bad.get("flights", [])
    check(walked > 600.0 and set(bp) == {1.1, 2.5}
          and all(bp[d] < 0.85 * want for d in bp)
          and len(bfl) >= 2 and bfl[0] > bfl[1] + 0.3
          and bad["avoid"] and bad["avoid"][0].get("model_moved", 0.0) > 1000.0,
          "6e. KNOWN-BAD ARM (--no-mirror-stop): the same drive reads the walk-in -- the "
          "mirror 2.5 s after the halt is over 600 u past it, the probes fly short, the "
          "chain's flights shrink as RUN-T's did (0.728 -> 0.282 s), and the mirror's "
          "avoidance halt re-parks the model over 1,000 u from the body",
          {"walked_u": round(walked, 1), "probes": {d: round(v, 3) for d, v in bp.items()},
           "flights": [round(f, 3) for f in bfl],
           "avoid": [(r.get("model_moved"), r.get("point")) for r in bad["avoid"]]})
    today, today_d = f9_reapproach()
    then, then_d = f9_reapproach(SWING_CLOCK_CHARGES_MOVING=True,
                                 CANCELLED_SWING_FREES_CLOCK=False)
    check(today is not None and 0.0 <= today <= F9_STEP + 1e-6
          and reach - 15.0 <= today_d <= reach,
          "6f. RANGERLOOP-F11 on this tree: the RE-APPROACH after a move that cancelled a "
          "swing in its windup halts at its own leg's eta plus at most one tick, inside "
          "range by under 15 u -- the cancelled swing holds no clock (1z-ds.13) and the "
          "clock is not charged for moving (1z-ds.11). The keyboard arms are emulated "
          "(RECONSTRUCTION); the cancel and the clock are the real ones",
          {"late_s": None if today is None else round(today, 3),
           "mirror_d": None if today_d is None else round(today_d, 1)})
    check(then is not None and then >= 0.2 and then_d < reach - 50.0,
          "6g. KNOWN-BAD, the 2026-09-30 swing clock (--swing-clock-charges-moving "
          "--cancelled-swing-holds-clock): the same re-approach halts late and inside "
          "range -- RUN-T's 1.207 s against 0.742, 134 u in, the late halt F9 recorded",
          {"late_s": None if then is None else round(then, 3),
           "mirror_d": None if then_d is None else round(then_d, 1)})


# --------------------------------------------------------------------------- 7
def section_mirror_stop_tape():
    print("\n7. RANGERLOOP-F9 on the tape: S16 RUN-T's capture through the real guard")
    gdir = vaultpath.vault_path(*F9_CAP[:-1])
    if not os.path.isdir(gdir):
        LEDGER.skip("RANGERLOOP-F9's tape", f"no {gdir} (bare machine)")
        return
    path = vaultpath.vault_path(*F9_CAP)
    if not os.path.isfile(path):
        check(False, "7. the S16 RUN-T capture is present (the vault has gamesrv captures "
              "but not this one)", path)
        return
    with open(path, encoding="utf-8") as fh:
        rows = [json.loads(line) for line in fh]
    moves = []                 # (t, opcode, values): the player's movement sends, in order
    launches = []              # (t, flight)
    for r in rows:
        if r.get("kind") != "sent" or r.get("opcode") not in (
                0x0027, OP_HALT, 0x0029, OP_FOLLOW, 0x002B, OP_REPIN, OP_LAUNCH):
            continue
        op, v, _ = authsrv.codec.decode_one("GAME_SMSG", bytes.fromhex(r["plain"]))
        if v[1] != PLAYER:
            continue
        if op == OP_LAUNCH:
            launches.append((r["t"], f9_flight(v[1:])))
        else:
            moves.append((r["t"], op, v[1:]))
    appr = [r for r in rows if r.get("kind") == "approach" and r.get("act") == "send"]
    halts = [m for m in moves if m[1] == OP_HALT]
    folls = [m for m in moves if m[1] == OP_FOLLOW]
    report = next((r for r in rows if r.get("kind") == "decoded" and r.get("opcode") == 0x003D
                   and halts and r["t"] > halts[0][0]), None)
    drift = next((r for r in rows if r.get("kind") == "position_report"
                  and report is not None and r["t"] >= report["t"]), None)
    check(len(appr) == 2 and len(halts) == 2 and len(folls) == 2
          and 1.0 <= halts[0][0] - folls[0][0] <= 1.2 and report is not None
          and drift is not None and drift["drift"] > 1400.0 and len(launches) == 3,
          "7a. the tape, read with the codec: two approaches, two APPROACH HALT 0x0028s "
          "(the first 1.0-1.2 s after its 0x002A), three launches, and the server's own "
          "position_report at the client's first post-halt 0x003D reading the defect -- "
          "drift over 1,400 u (the 1z-dj park at the target's disc)",
          {"halts": [round(h[0], 3) for h in halts],
           "drift": None if drift is None else drift["drift"]})
    if not (appr and report is not None and launches):
        return
    origin = tuple(appr[0]["origin"])
    target = tuple(appr[0]["at"])
    client = tuple(report["values"][1])

    def replay(park):
        """Every player movement send on the tape through _agtrack_shadow_emit, a fresh
        guard seeded at the first approach's origin. -> (mirror off the client's report,
        [flights the mirror predicts at the three launch instants])"""
        g_st = {}
        saved = authsrv.MIRROR_PARKS_ON_STOP
        authsrv.MIRROR_PARKS_ON_STOP = park
        try:
            import agtrack_guard as _ag
            g = _ag.AgTrackGuard()
            g.on_placement(origin[0], origin[1], 0, folls[0][0] - 1.0)
            g_st["agtrack_guard"] = g
            events = sorted([(t, 0, op, v) for t, op, v in moves]
                            + [(report["t"], 1, "report", None)]
                            + [(t, 1, "launch", f) for t, f in launches])
            off, pred = None, []
            for t, _k, what, v in events:
                if what == "report":
                    p = g.mirror.sync.position(g._ms(t))
                    off = math.hypot(p[0] - client[0], p[1] - client[1])
                elif what == "launch":
                    p = g.mirror.sync.position(g._ms(t))
                    pred.append(math.hypot(target[0] - p[0], target[1] - p[1]) / 1600.0)
                else:
                    authsrv._agtrack_shadow_emit(g_st, what, list(v), None, now=t)
        finally:
            authsrv.MIRROR_PARKS_ON_STOP = saved
        return off, pred
    off_bad, pred_bad = replay(False)
    off_on, pred_on = replay(True)
    check(off_bad is not None and off_bad > 1400.0 and off_on is not None and off_on <= 15.0,
          "7b. HEADLINE, the tape: fed every movement send but blind to the halt, the mirror "
          "stands over 1,400 u from the client's first post-halt 0x003D; parked by on_stop "
          "at the halt's instant, within 15 u of it",
          {"unfed_u": None if off_bad is None else round(off_bad, 1),
           "parked_u": None if off_on is None else round(off_on, 1)})
    tape = [f for _t, f in launches]
    check(len(pred_bad) == 3 and all(abs(p - f) <= 0.02 * f for p, f in zip(pred_bad, tape))
          and len(pred_on) == 3 and all(p > 0.84 for p in pred_on),
          "7c. the known-bad arm IS the tape: the blind mirror reproduces all three of "
          "RUN-T's flights (0.728, 0.282, 0.648 s) within 2 %; the parked mirror predicts "
          "~0.93, 0.93 and 0.85 s -- the flights the runsheet scores",
          {"tape": [round(f, 3) for f in tape], "blind": [round(p, 3) for p in pred_bad],
           "parked": [round(p, 3) for p in pred_on]})
    # RANGERLOOP-F11 re-derived from the same rows: the re-approach's start is the swing
    # clock's, not the leg's -- last start + interval + the chain-pause charge.
    starts = [r["t"] for r in rows if r.get("kind") == "sent" and r.get("opcode") == OP_START
              and r.get("label", "").startswith("attack_started: player")]
    pause = [r for r in rows if r.get("kind") == "chain_pause"]
    second = halts[1][0] if len(halts) > 1 else None
    prior = max((s for s in starts if second is not None and s < second - 0.01), default=None)
    due = (None if prior is None or len(pause) < 2
           else prior + pause[1]["interval"] + pause[1]["charged"])
    walk_on = (None if second is None or len(appr) < 2
               else (second - folls[1][0] - appr[1]["run"] / authsrv.DEFAULT_RUN_SPEED)
               * authsrv.DEFAULT_RUN_SPEED)
    check(due is not None and abs(due - second) <= 0.01
          and walk_on is not None and 120.0 <= walk_on <= 150.0,
          "7d. RANGERLOOP-F11 from the tape's own rows: the late halt (1.207 s against "
          "eta 0.742) is the 2026-09-30 swing clock -- the cancelled start before it + "
          "interval + the chain-pause charge lands on it to 10 ms, and the body walked "
          "~134 u past the range point while it waited",
          {"prior": prior, "due": None if due is None else round(due, 4),
           "halt": second, "walk_on_u": None if walk_on is None else round(walk_on, 1)})


def main():
    print("test_approachroute -- ROUTE-A: a ranged approach's swing holds the walk gate "
          "and halts the body (RANGERPRE-S16); ROUTE-B: a held interact is served at the "
          "follow disc (RANGERPRE-S17)")
    t0 = time.time()
    batches = section_server()
    section_flag()
    section_tape(batches)
    section_route_b_server()
    section_route_b_tape()
    section_mirror_stop()
    section_mirror_stop_tape()
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
