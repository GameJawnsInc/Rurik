"""test_approachroute -- the out-of-reach approach (ROUTE). This step ships ROUTE-A only:
a RANGED approach's first swing holds the walk gate and halts the body (RANGERPRE-S16,
2026-09-30). ROUTE-B (where a held interact is served), ROUTE-C (corner routing),
ROUTE-C2 and ROUTE-D are not built; each adds its own section here when it lands.

    python toolkit/authsrv/test_approachroute.py

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
socket and no client.
"""
import os
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

# Floor from the green run of 2026-09-30 with RURIK_VAULT at an EMPTY directory (section 3
# a declared skip): 21 (20 until the review follow-up added 1r). Section 3 adds 9 when
# the captures are present (30).
LEDGER = checks.Ledger("the approach (ROUTE-A)", floor=21)
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
           "APPROACH_START_HALTS", "LANDING_HOLD_RELEASE")


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
        st_b, _send_b, bad, _p = approach("starter_bow")
        batches["bad"] = list(bad)
        check(bad == [(OP_START, [4, PLAYER, FOE, 0])] and not st_b.get("approach_hold")
              and "approach_closed" not in st_b,
              "1k. KNOWN-BAD, --no-approach-start-halt: [4] alone, no hold, no halt -- this "
              "server until today, which retail's 12 of 12 refute", show(bad))
        authsrv.APPROACH_START_HALTS = True

        # 1l-1n: the controls
        _st, _s, sword, sword_press = approach("starter_sword")
        check(ops(sword_press) == [OP_FOLLOW] and sword == [(OP_START, [4, PLAYER, FOE, 0])],
              "1l. CONTROL, melee: a sword's approach arrives and its start is [4] alone -- "
              "retail's melee starts are mixed (:53756, 1 of 4) and are left as they were",
              show(sword))
        st_n, _s, near, near_press = approach("starter_bow", distance=800.0)
        check(near_press == [(OP_START, [4, PLAYER, FOE, 0])] and near == []
              and not st_n.get("approach_hold"),
              "1m. CONTROL, at rest: a bow press already in range opens [4] alone -- no "
              "approach, no halt (retail's at-rest starts: 37 of 37 carry neither)",
              show(near_press))
        authsrv.apply_party_character({"player_weapon": "starter_bow"})
        st_o = world(800.0)
        st_o["approach_closed"] = OTHER
        o_sent, o_send = collect()
        authsrv.begin_attack(o_send, st_o, FOE, 1)
        authsrv.attack_tick(o_send, st_o, 1)
        check(o_sent == [(OP_START, [4, PLAYER, FOE, 0])] and "approach_closed" not in st_o,
              "1n. an arrival marker naming ANOTHER target halts nothing, and the start "
              "consumes it anyway", show(o_sent))
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
        check(up and die_sent == [(OP_INT, [8, PLAYER, 0])] and "approach_hold" not in st_d
              and st_d.get("action_hold") == 0,
              "1r. the TARGET'S DEATH releases it: after the launch, attack_tick's "
              "target-gone site sends [8, me, 0] and forgets the approach's hold (retail "
              ":55934 384.3644, 0.79 s after agent 46 dies; :62994 86.2717)",
              f"held through the launch {up}; {show(die_sent)}")
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


def main():
    print("test_approachroute -- ROUTE-A: a ranged approach's swing holds the walk gate "
          "and halts the body (RANGERPRE-S16)")
    t0 = time.time()
    batches = section_server()
    section_flag()
    section_tape(batches)
    print(f"\n({time.time() - t0:.1f} s)")
    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
