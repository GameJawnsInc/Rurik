"""Prove an agent can leave the world, and that a desynced stream stops the server.

Two fixes from studies/divergence/FINDINGS.md, the first live capture's divergence
analysis. They are tested together because they are the same defect wearing two
hats: in both cases the server carried on past a state it had no way to reason
about, and produced confident output about it.

  1. **WORLD_REMOVE_AGENT (0x0021)** -- D1, the highest-ranked protocol gap.
     ArenaNet sent it 416 times in one session; our server had sent it 0 times in
     271,449 recorded messages, so `state["agents"]` only ever grew and an agent id
     could never be reused without the client holding a stale object under it. The
     interesting assertions here are the REFUSALS, because the send itself is one
     line: removing a never-created id, and double-removing, are each 0 of 416 in
     the live capture, and the client bounds-checks the dword as an array index
     (`Array:587 "index < m_count"` at 0x005FD2F0), so a bad id asserts inside the
     client, far from the cause.

  2. **The desync close** -- D9(b). An unframeable opcode used to set
     `pending = b""` and continue, which is not recovery: with no length prefix
     nothing knows where the bad message ended, so every later read was framed from
     a non-boundary. This asserts the framer's own contract (it stops, it does not
     resynchronise) and that garbage does NOT accidentally frame -- the property
     the old code was quietly relying on being false.

standard library only.

    python toolkit/authsrv/test_agentlife.py
"""
import inspect
import math
import os
import struct
import time
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agents  # noqa: E402
import checks  # noqa: E402
from codec import Codec  # noqa: E402

LEDGER = checks.Ledger("agent lifetime", floor=172)


def main():
    import authsrv
    import probes

    codec = Codec()

    # ---- 1. the message is the shape the live capture and the client agree on --
    print("1. WORLD_REMOVE_AGENT is 6 bytes carrying one agent id")
    LEDGER.ok(authsrv.GAME_SMSG_WORLD_REMOVE_AGENT == 0x0021,
              "the opcode is 0x0021", "OBSERVED 416 times in the live capture")
    blob = codec.encode("GAME_SMSG", 0x0021, [725])
    LEDGER.ok(len(blob) == 6, "it encodes to exactly 6 bytes on the wire",
              f"{len(blob)}B: {blob.hex()} -- the client's RECV table says 6, and "
              f"at 2 or 10 the live stream does not frame")
    LEDGER.ok(blob[:2] == b"\x21\x00", "with the opcode first, little-endian",
              blob[:2].hex())
    msgs, consumed, err = codec.decode_stream("GAME_SMSG", blob)
    LEDGER.ok(err is None and consumed == 6 and msgs[0][1][1] == 725,
              "and it round-trips back to the agent id it was given",
              str(msgs))

    # ---- 2. the world state actually loses the agent ---------------------------
    print("\n2. removal is a world-state operation, not just a send")
    sent = []
    send = lambda op, vals, why="": sent.append((op, vals, why))
    state = {"agents": {10: {"name": "hatcher", "dead": False},
                        11: {"name": "other", "dead": False}}}

    entry = authsrv.remove_agent(send, state, 10, "test")
    LEDGER.ok(10 not in state["agents"],
              "the removed agent is GONE from state['agents']",
              "the dict only ever grew before this -- an id could never be reused")
    LEDGER.ok(11 in state["agents"], "and its neighbour is untouched")
    LEDGER.ok(entry["name"] == "hatcher",
              "the removed bookkeeping is returned, so a respawn can carry it")
    LEDGER.ok(sent and sent[0][0] == 0x0021 and sent[0][1] == [10],
              "and exactly the removal message went out", str(sent[0][:2]))
    LEDGER.ok(state.get("removed_agents") == [10],
              "the removal is recorded, so id reuse is auditable")

    # ---- 3. THE REFUSALS, which are the whole point ----------------------------
    print("\n3. the two removals ArenaNet never performs are refused")
    before = len(sent)
    try:
        authsrv.remove_agent(send, state, 10, "again")
        double = ""
    except authsrv.AgentLifetimeError as ex:
        double = str(ex)
    LEDGER.ok(bool(double),
              "double-removing an id is REFUSED, not sent",
              "0 of 416 live removals double-remove without an intervening create")
    LEDGER.ok(len(sent) == before,
              "and nothing went on the wire when it was refused",
              "a refusal that still sends is not a refusal")

    try:
        authsrv.remove_agent(send, state, 9999, "never existed")
        never = ""
    except authsrv.AgentLifetimeError as ex:
        never = str(ex)
    LEDGER.ok(bool(never), "removing a never-created id is REFUSED",
              "0 of 416 live -- and the client bounds-checks this dword as an "
              "index, so a bad id asserts inside the client, not here")
    LEDGER.ok("9999" in never and "live ids" in never,
              "and the refusal names the bad id and what IS live", never[:90])

    # ---- 4. id reuse, which removal exists to unlock ---------------------------
    print("\n4. an id can be reused once, and only once, it has been removed")
    state["agents"][10] = {"name": "hatcher-2", "dead": False}
    LEDGER.ok(10 in state["agents"],
              "a removed id can be created again",
              "301 of 301 live re-creations were preceded by a removal of that id")
    entry2 = authsrv.remove_agent(send, state, 10, "cycle")
    LEDGER.ok(entry2["name"] == "hatcher-2" and state["removed_agents"] == [10, 10],
              "and the cycle can repeat, each removal recorded")

    # ---- 5. the probe exists and states a prediction ---------------------------
    print("\n5. the probe that settles what the client does with a removal")
    LEDGER.ok("agent_removal" in probes.PROBES,
              "an agent_removal probe is registered")
    p = probes.PROBES["agent_removal"](1, (100.0, 200.0, 0))
    LEDGER.ok(bool(p.question) and bool(p.predicts),
              "and it states a question AND a prediction before it runs",
              "a probe with no stated expectation can be rationalised into "
              "agreeing with anything afterwards")
    LEDGER.ok([s.opcode for s in p.steps] == [0x0021, 0x0056, 0x0057, 0x0020, 0x0020],
              "its steps remove, then re-create with the FULL spawn burst, then control",
              str([hex(s.opcode) for s in p.steps]))

    # ---- 6. the desync close ---------------------------------------------------
    print("\n6. an unframeable opcode stops the framer and does not resynchronise")
    # 0x9201 is the real one: OBSERVED 7 times in our own corpus, one byte before
    # a VALID GAME_CMSG 0x0092 -- an off-by-one the old `pending = b""` hid.
    bad = bytes.fromhex("019280700000000000000000")
    msgs, consumed, err = codec.decode_stream("GAME_CMSG", bad, mask=0x8000)
    LEDGER.ok(err is not None and "no opcode" in err,
              "the framer REPORTS an unknown opcode rather than skipping it", err)
    LEDGER.ok(consumed == 0,
              "and consumes NOTHING, so the caller cannot mistake it for progress",
              f"consumed={consumed}")
    LEDGER.ok(not msgs,
              "no message is invented out of the undecodable bytes",
              "this is the property the old buffer-discard relied on being false: "
              "it cleared the buffer and framed the NEXT read from a non-boundary")

    # ---- 6b. what the SERVER does with that answer -----------------------------
    # Section 6 asserts what the codec does. That is not the fix. The defect was
    # that the codec was right and the CALLER mishandled it, so the policy is
    # extracted into frame_pending and asserted here directly -- without this,
    # every check above passes with the buffer-discard bug fully restored.
    print("\n6b. frame_pending: the server's own framing policy")
    whole = bytes.fromhex("019280700000000000000000")
    m, rest, desync = authsrv.frame_pending(codec, "GAME_CMSG", whole, 0x8000)
    LEDGER.ok(desync is not None,
              "an unframeable opcode is reported to the caller as a desync", str(desync))
    LEDGER.ok(rest == whole,
              "and its bytes are LEFT IN THE BUFFER, not discarded",
              "the old code set pending = b'' here, which framed every later read "
              "from a non-boundary while ARC4 kept the bytes looking plausible")

    # A partial trailing message is the NORMAL case and must not read as a desync.
    okmsg = codec.encode("GAME_SMSG", 0x0021, [7])
    m2, rest2, desync2 = authsrv.frame_pending(codec, "GAME_SMSG", okmsg + okmsg[:3], 0)
    LEDGER.ok(desync2 is None,
              "a half-arrived trailing message is NOT a desync",
              "a TCP read is not a message boundary; treating this as fatal would "
              "kill healthy connections constantly")
    LEDGER.ok(len(m2) == 1 and rest2 == okmsg[:3],
              "its bytes are carried forward for the next read", f"{len(m2)} msg, "
              f"{len(rest2)}B carried")
    m3, rest3, desync3 = authsrv.frame_pending(codec, "GAME_SMSG", okmsg * 3, 0)
    LEDGER.ok(desync3 is None and len(m3) == 3 and rest3 == b"",
              "and a clean buffer of whole messages consumes exactly, with no desync",
              f"{len(m3)} msgs, {len(rest3)}B left")

    section_named_builders(codec)
    section_pool_fraction()
    section_swing_back()
    section_chase()
    section_facing()
    section_enemy_skill()
    section_constants()
    section_probe_encoding()
    section_spawn_profession()
    section_unlock_bitmap()
    return LEDGER.verdict()


def _world(dist=100.0, **over):
    """A player at the origin and one hostile `dist` units away."""
    import authsrv
    entry = {"name": "hatcher", "dead": False, "died_at": 0.0,
             "health": 100.0, "max_health": 100.0, "last_hit": 0.0,
             "pos": (dist, 0.0), "plane": 0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": True,
             "skills": authsrv.ENEMY_SKILL_BAR,
             "skill_ready": [0.0] * len(authsrv.ENEMY_SKILL_BAR)}
    entry.update(over)
    return {"agents": {10: entry}, "pos": (0.0, 0.0)}


def _swings(state, n=1, gap=0.0):
    """Run enemy_attack_tick n times and return everything it sent."""
    import authsrv
    sent = []
    for _ in range(n):
        if gap:
            time.sleep(gap)
        authsrv.enemy_attack_tick(
            lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
            state, 1)
    return sent


def section_swing_back():
    """R4a's other half: a hostile agent attacks the player, and the player dies.

    Until 2026-08-11 every combat message this server sent flowed one way. PLAN.md
    3's R4a row has said "nothing swings back and the player cannot die" since
    2026-08-06, and both clauses were properties of the code: no sweep aimed a
    swing at the player, and the server did not track the player's health at all
    after telling the client about it once at spawn.

    THE CHECK THAT MATTERS IS THE ROLE CHECK. `hit_enemy` carries a comment about
    an early version that put the ENEMY in slot 1 of GV_ATTACK_STARTED -- the
    client animated the enemy and then asserted on `m_attackInterval`, which is how
    slot 1 was identified as the swinger. `hit_player` is that mistake made
    deliberately, so the one way to get it wrong now is to write it the way
    `hit_enemy` is written and animate the PLAYER attacking themselves. Two checks
    below fail on exactly that, and they are the reason this section exists rather
    than a count of messages.
    """
    import authsrv

    # THE SKILL IS OFF THROUGHOUT THIS SECTION. `_world` carries production
    # defaults, and in production a hostile opens with its skill -- so every
    # fixture here would measure a cast instead of a swing. section_enemy_skill
    # owns that path; this one owns the swing, and mixing them was how the two
    # checks below first went red.
    def _sworld(**kw):
        w = _world(**kw)
        w["agents"][10]["skills"] = ()
        return w

    # 1. A SWING IS TWO PHASES SEPARATED BY A WINDUP, which is the shape ArenaNet
    #    uses and the shape the first version of this code got wrong: it sent all
    #    three messages in the same instant, so the damage number landed on the
    #    frame the animation started.
    state = _sworld()
    sent = _swings(state)
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION,
                      authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET],
              "a swing opens by TURNING and then ATTACK_STARTED, with no damage",
              f"{[hex(o) for o in ops]} -- damage arriving here is the "
              "instant-swing bug: 0.899 s of animation with the number already on "
              "screen. The turn is forced on every swing because an agent landing "
              "a hit with its back to you is the one thing here a person would "
              "call broken without being told")
    LEDGER.ok(not _swings(state, n=4),
              "and nothing lands while the windup is still running",
              f"swing_lands_at is {state['agents'][10].get('swing_lands_at')!r} "
              "-- four more ticks inside the window must stay silent")

    # now let the windup elapse, and the landing must be FINISHED then DAMAGE
    state["agents"][10]["swing_lands_at"] = time.time() - 0.001
    land = _swings(state)
    ops = [op for op, _v, _l in land]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT,
                      authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET],
              "and the landing is MELEE_ATTACK_FINISHED and then the damage",
              f"{[hex(o) for o in ops]} -- ArenaNet sends finished BEFORE damage, "
              "adjacent in one payload, 6 of 6 swings checked by byte offset. "
              "hit_enemy sends them the other way round and is left alone: the "
              "claim about how the CONTROLLED agent's landings are marked was "
              "refuted under review, so there is no verified model to copy")
    sent = sent + land

    started = [v for op, v, _l in sent
               if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET][0]
    LEDGER.ok(started[0] == agents.GV_ATTACK_STARTED and started[1] == 10,
              "and slot 1 of attack_started is the AGENT, not the player",
              f"{started} -- slot 1 is the body the client animates. Writing this "
              "the way hit_enemy is written puts PLAYER_AGENT_ID here and animates "
              "the player swinging at themselves, which is the mirror of the bug "
              "hit_enemy's own comment records")
    LEDGER.ok(started[2] == authsrv.PLAYER_AGENT_ID,
              "and slot 2 is the player, who is being swung at",
              f"{started}")

    dmg = [v for op, v, _l in sent
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET][0]
    LEDGER.ok(dmg[0] == agents.PROP_DAMAGE and dmg[1] == authsrv.PLAYER_AGENT_ID
              and dmg[2] == 10,
              "and the damage names the player as DAMAGED and the agent as CAUSE",
              f"{dmg[:3]} -- 0x00A3 is [prop, target, cause, value], the opposite "
              "order to attack_started, which is why both are checked here")

    val = struct.unpack("<f", struct.pack("<I", dmg[-1]))[0]
    LEDGER.ok(-1.0 <= val < 0.0,
              "and the value is a negative fraction inside the client's bound",
              f"{val!r} -- positive would trip CharPool.cpp:84 `fraction <= 1.0f`")
    LEDGER.ok(state["player_health"] < agents.PLAYER_HEALTH,
              "and the server's own bookkeeping went down with it",
              f"{state['player_health']} of {agents.PLAYER_HEALTH} -- nothing "
              "tracked this at all before this rung")

    # 2. the four refusals. Each is a hostile that must NOT swing.
    for why, world in (
            ("out of aggro range", _sworld(dist=authsrv.AGGRO_RANGE + 1.0)),
            ("dead", _sworld(dead=True)),
            ("attacks_back off", _sworld(attacks_back=False)),
            ("mid-burrow", _sworld(effects=agents.EFFECT_TRANSITION)),
            ("not hostile", _sworld(allegiance=agents.ALLEGIANCE_ENEMY + 100))):
        LEDGER.ok(not _swings(world),
                  f"a hostile that is {why} does not swing",
                  "silence is the whole assertion here")

    # AND A PENDING LANDING DOES NOT SURVIVE ITS SWINGER. ArenaNet's own seventh
    # swing in the Lakeside tape was truncated exactly this way -- the player
    # killed the worm 0.24 s into a 0.899 s windup and no damage followed.
    for why, kill in (("dies", lambda a: a.update(dead=True)),
                      ("leaves range",
                       lambda a: a.update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0)))):
        mid = _sworld()
        _swings(mid)                                    # opens a swing
        assert mid["agents"][10]["swing_lands_at"] is not None
        kill(mid["agents"][10])
        mid["agents"][10]["swing_lands_at"] = time.time() - 1.0   # long overdue
        before = mid["player_health"]
        LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
                  f"a swing in flight does not land if the swinger {why}",
                  "an overdue landing plus three ticks, and no damage -- the "
                  "pending swing has to be dropped, not merely postponed")

    # 3. enough swings kill the player -- and the KILL is the effects bit, because
    #    property 16 floors at 1 and cannot do it. Drive it with the interval
    #    forced to zero rather than by sleeping through ten real swings.
    #    Driven through hit_player directly rather than by ticking: the swing
    #    timer reads time.time(), whose resolution on Windows is coarse enough
    #    that forty ticks at a 1 ms interval all landed inside one clock tick and
    #    produced a single swing. A test that has to outrun the clock to measure
    #    anything is measuring the clock.
    state = _sworld()
    sent = []
    keep = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    needed = int(math.ceil(1.0 / authsrv.ENEMY_HIT_FRACTION))
    for _ in range(needed):
        authsrv.land_swing(keep, state, 10, state["agents"][10], 1)
    LEDGER.ok(state["player_dead"] and state["player_health"] == 0.0,
              f"{needed} swings at {authsrv.ENEMY_HIT_FRACTION} of the pool kill "
              "the player",
              f"health {state['player_health']}, dead {state['player_dead']}")
    kills = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
             and v == [authsrv.PLAYER_AGENT_ID, agents.EFFECT_DEAD]]
    LEDGER.ok(len(kills) == 1,
              "and the death is ONE effects-bit message on the player",
              f"{len(kills)} -- damage cannot kill (PROP_DAMAGE floors at 1), so "
              "the bit is the death; more than one means the corpse is being "
              "re-killed every interval")

    # 4. and a corpse is left alone, in both directions
    before = len(sent)
    LEDGER.ok(not _swings(state, n=5),
              "nothing swings at a dead player",
              f"{before} messages before, none after")
    swung = []
    state["attacking"] = 10
    authsrv.attack_tick(lambda op, v, label="", quiet=False: swung.append(op),
                        state, 1)
    LEDGER.ok(not swung,
              "and a dead player stops swinging back",
              "attack_tick reads state['player_dead'] -- without it the corpse "
              "keeps hitting the thing that killed it")

    # 5. the revive, and that it does not fire early
    authsrv.player_revive_due(lambda *a, **k: None, state, 1)
    LEDGER.ok(state["player_dead"],
              "the revive does not fire before its timer",
              f"died_at {state['player_died_at']}, needs "
              f"{authsrv.PLAYER_REVIVE_AFTER}s")

    state["player_died_at"] = time.time() - authsrv.PLAYER_REVIVE_AFTER - 1.0
    rev = []
    authsrv.player_revive_due(
        lambda op, v, label="", quiet=False: rev.append((op, v)), state, 1)
    LEDGER.ok(not state["player_dead"]
              and state["player_health"] == float(agents.PLAYER_HEALTH),
              "and then it stands the player back up at full health",
              f"{state['player_health']}")
    cleared = [v for op, v in rev if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS]
    LEDGER.ok(cleared == [[authsrv.PLAYER_AGENT_ID, 0]],
              "clearing the effects bit it set",
              f"{cleared}")
    refill = [struct.unpack("<f", struct.pack("<I", v[-1]))[0] for op, v in rev
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(refill == [1.0],
              "and refilling the pool with 1.0, the SETTER's full-bar value",
              f"{refill} -- max_health here is what crashed the client on "
              "2026-08-11, and the same guard covers this call site")

    # 6a. a mis-declared agent does not swing every tick. Attack speed 0 is the
    #     value that took the client down on m_attackInterval, and `or` sends it
    #     to a real interval rather than to "no wait at all".
    zero = _sworld()
    zero["agents"][10]["attack_speed"] = 0.0
    LEDGER.ok(len(_swings(zero, n=8)) == 2,
              "an agent declaring attack speed 0 falls back to a real interval",
              "8 ticks, ONE swing opening (a turn and an attack_started) -- 0.0 "
              "is falsy, and treating it as "
              "'unset' is deliberate: it is the value behind the "
              "m_attackInterval assert. One message rather than three because a "
              "swing now opens and lands separately")

    # 6. the swing honours the AGENT's declared speed, not the player's. The
    #    client was told this agent's attack speed at spawn and animates to it.
    state = _sworld()
    state["agents"][10]["attack_speed"] = 10.0
    n = len(_swings(state, n=6))
    LEDGER.ok(n == 2,
              "and a slow weapon swings once, not once per tick",
              f"{n} message(s) over 6 ticks at a 10 s interval -- an opening is a "
              "turn plus an attack_started, so anything above 2 means the timer is "
              "not being read")


def _walk(state, n=1, elapsed=1.0):
    """Run enemy_move_tick n times, each pretending `elapsed` seconds passed."""
    import authsrv
    sent = []
    for _ in range(n):
        for a in state.get("agents", {}).values():
            a["moved_at"] = time.time() - elapsed
        authsrv.enemy_move_tick(
            lambda op, vals, label="", quiet=False: sent.append((op, vals, label)),
            state, 1)
    return sent


class _Wall:
    """A pathmap that refuses to let anything WEST of x = 400.

    The agent starts east of the player and walks toward the origin, so the wall
    clamps from below. The first version clamped from above and never blocked
    anything -- a fixture that cannot fail is the same defect as a check that
    cannot fail, one layer down.
    """

    def __init__(self):
        self.asked = 0

    def clip(self, x0, y0, x1, y1, step=16.0):
        self.asked += 1
        return (max(x1, 400.0), y1)


def section_chase():
    """It walks toward the player, and stops where it can reach them.

    THE BUG THIS RUNG FIXES IS ONE OF OURS. `AGGRO_RANGE` was doing two jobs --
    when a hostile NOTICES the player and when it can REACH them -- so a Hatcher
    rooted to its spawn point swung at anything within 1200 units. It hit people
    across a courtyard it never crossed. Splitting reach from notice is what makes
    the chase necessary rather than decorative: without the walk, raising the reach
    to a melee distance would simply mean nothing could ever hit anybody.

    All three constants are ours and the docstring at the call site says so.
    """
    import authsrv

    far = authsrv.ENEMY_MELEE_RANGE + 450.0

    # 1. it starts moving, announces a rate and a destination, and does NOT swing
    state = _world(dist=far)
    sent = _walk(state)
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_AGENT_UPDATE_SPEED,
                      authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION,
                      authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT],
              "a hostile out of reach announces a rate, a facing and a destination",
              f"{[hex(o) for o in ops]}")
    rate = [v for op, v, _l in sent
            if op == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED][0]
    LEDGER.ok(rate[0] == 10 and 0.0 < rate[1] <= agents.AGENT_MAX_MOVE_SPEED,
              "and the rate is a FRACTION inside the client's own asserted bounds",
              f"{rate} -- units/s here is the named mistake; "
              f"{authsrv.ENEMY_MOVE_RATE} x {agents.DEFAULT_RUN_SPEED} = "
              f"{authsrv.ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s")
    dest = [v for op, v, _l in sent
            if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT][0]
    LEDGER.ok(dest[0] == 10 and dest[1] == [0.0, 0.0],
              "and the destination is where the player is standing",
              f"{dest}")
    LEDGER.ok(not _swings(state),
              "and it does not swing from out there",
              f"{far:.0f} units, reach is {authsrv.ENEMY_MELEE_RANGE:.0f} -- this "
              "is the courtyard bug, and it read AGGRO_RANGE until today")

    # 2. it actually closes the distance
    state = _world(dist=far)
    before = math.hypot(*state["agents"][10]["pos"])
    _walk(state, n=3, elapsed=0.5)
    after = math.hypot(*state["agents"][10]["pos"])
    LEDGER.ok(after < before - 100.0,
              "and over three half-seconds it closes real ground",
              f"{before:.0f} -> {after:.0f} units at "
              f"{authsrv.ENEMY_MOVE_RATE * agents.DEFAULT_RUN_SPEED:.0f} u/s")

    # 3. IT STOPS AT REACH RATHER THAN WALKING THROUGH THE PLAYER. A long step is
    #    the interesting case: without the cap the agent overshoots to distance 0
    #    and stands inside them.
    state = _world(dist=far)
    _walk(state)                       # tick one only announces the intent
    LEDGER.ok(math.hypot(*state["agents"][10]["pos"]) == far,
              "the tick that starts the walk does not also move the agent",
              "moved_at is stamped when the walk begins, so the first step is "
              "measured from then -- an agent cannot have travelled before it set off")
    _walk(state, n=1, elapsed=30.0)
    d = math.hypot(*state["agents"][10]["pos"])
    LEDGER.ok(abs(d - authsrv.ENEMY_MELEE_RANGE) < 1.0,
              "and a huge step stops it exactly at reach, not on top of the player",
              f"{d:.1f} against a reach of {authsrv.ENEMY_MELEE_RANGE:.0f} -- "
              "uncapped, a 30 s step lands at 0 and the agent stands inside them")
    state["agents"][10]["skills"] = ()       # the swing path, not the skill path
    LEDGER.ok(bool(_swings(state)),
              "and having arrived, it can swing",
              "the walk is only worth anything if the fight starts at the end of it")

    # 4. the stop is an ARRIVAL, never a zero rate -- agent_update_speed refuses
    #    anything under AGENT_MIN_MOVE_SPEED and that refusal is a ValueError on
    #    the world tick.
    stop = _walk(state, n=2)
    stop_ops = [op for op, _v, _l in stop]
    LEDGER.ok(authsrv.GAME_SMSG_AGENT_UPDATE_SPEED not in stop_ops,
              "stopping never sends a speed message",
              f"{[hex(o) for o in stop_ops]} -- speed 0.0 is below the client's own "
              f"floor of {agents.AGENT_MIN_MOVE_SPEED} (AgAgent.cpp:2366) and "
              "agent_update_speed raises on it")
    LEDGER.ok(len([o for o in stop_ops
                   if o == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT]) == 1,
              "and it announces its arrival exactly once, not every tick",
              f"{len(stop_ops)} message(s) over two ticks standing still")

    # 5. the destination is not re-announced every tick while chasing
    state = _world(dist=far)
    _walk(state)                                   # first announcement
    quiet = _walk(state, n=4, elapsed=0.05)
    LEDGER.ok(not [op for op, _v, _l in quiet
                   if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT],
              "a stationary player is not re-announced on every tick",
              f"{len(quiet)} message(s) over four ticks -- 20 a second is what "
              "'tell the client where to go' becomes if this is not gated")
    state["pos"] = (0.0, authsrv.ENEMY_DEST_RESEND + 50.0)
    moved = _walk(state, elapsed=0.05)
    LEDGER.ok(bool([op for op, _v, _l in moved
                    if op == authsrv.GAME_SMSG_AGENT_MOVE_TO_POINT]),
              "but a player who has walked far enough IS re-announced",
              f"moved {authsrv.ENEMY_DEST_RESEND + 50.0:.0f} units, threshold is "
              f"{authsrv.ENEMY_DEST_RESEND:.0f}")

    # 6. the refusals
    for why, world in (("past the leash", _world(dist=authsrv.AGGRO_RANGE + 50.0)),
                       ("dead", _world(dist=far, dead=True)),
                       ("passive", _world(dist=far, attacks_back=False)),
                       ("mid-burrow",
                        _world(dist=far, effects=agents.EFFECT_TRANSITION))):
        LEDGER.ok(not _walk(world),
                  f"a hostile that is {why} does not give chase",
                  "silence is the whole assertion")
    dead_player = _world(dist=far)
    dead_player["player_dead"] = True
    dead_player["player_health"] = 0.0
    LEDGER.ok(not _walk(dead_player),
              "and nothing chases a corpse",
              "the player is face-down; walking to them is the wrong picture "
              "and the swing that follows is worse")

    # 7. A WALL STOPS IT. pathmap.clip is sampled rather than solved, and it is
    #    the whole of our collision story -- pathmap.route is an A* and is NOT
    #    wired in, so an agent meets a wall and waits there.
    state = _world(dist=900.0)
    state["pathmap"] = _Wall()
    _walk(state)                       # announce, then walk
    _walk(state, n=4, elapsed=1.0)
    x = state["agents"][10]["pos"][0]
    LEDGER.ok(state["pathmap"].asked >= 1 and x >= 400.0,
              "a hostile is stopped by the pathmap rather than walking through it",
              f"x={x:.0f} against a wall at 400, clip asked "
              f"{state['pathmap'].asked} time(s)")


def section_facing():
    """It turns to look at you, on an angle nobody in this repo invented.

    `GAME_SMSG_AGENT_UPDATE_ROTATION` (0x002E) sat defined and documented in
    authsrv.py for days without ever being sent. Everything about how to fill it
    was already measured off ArenaNet's own traffic, which is why this rung needed
    no new discovery:

      * atan2(y, x) -- test_rotate.py scores the client's OWN 0x0040 sends against
        atan2 of a nearby 0x003D direction vector, beating a null model built from
        the same corpus. Its first version paired against the POSITION vec2 and
        scored 0 of 163, because a position has a plausible atan2 too.
      * absolute, in [-pi, pi], with +/-inf as the client's free-spin sentinels.
      * a turn rate that is per-CREATURE and quantised; 2*pi/3 is ArenaNet's
        largest, to the bit.

    Both payload fields are marshalled `dword` and hold float32 -- the same trap
    that made an early test_smsgnames compare garbage against pi and pass a
    turn-rate check vacuously. Every check here reinterprets before asserting, and
    the last one fails if the code stops doing so.
    """
    import authsrv

    # INDEX FROM THE SENT PAYLOAD, NOT FROM A DECODED ONE. test_smsgnames reads
    # 0x002E's angle at values[2] because a DECODED list carries the raw header at
    # index 0; what `send` is handed has no header, so the same field is at index
    # 1. Getting this wrong is silent in the usual way -- the first version of
    # this section read index 2 and got 2.0944, the TURN RATE, which is a
    # perfectly plausible angle (120 degrees) and would have been asserted as one.
    def angle_of(vals):
        return struct.unpack("<f", struct.pack("<I", vals[1]))[0]

    def rate_of(vals):
        return struct.unpack("<f", struct.pack("<I", vals[2]))[0]

    def rots(sent):
        return [v for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_UPDATE_ROTATION]

    # the fixture puts the agent due EAST of the player, so it must look WEST
    state = _world(dist=600.0)
    r = rots(_walk(state))
    LEDGER.ok(len(r) == 1 and r[0][0] == 10,
              "setting off, the agent announces a facing for itself",
              f"{len(r)} rotation(s)")
    LEDGER.ok(abs(angle_of(r[0])) < 1e-5,
              "the emitted angle is the bearing to the player PLUS pi",
              f"{angle_of(r[0]):.5f} rad = {math.degrees(angle_of(r[0])):.0f} deg. "
              "The agent is due EAST of the player, so the bearing TO the player "
              "is +/-pi and the emitted value is 0. THE PLUS PI IS MEASURED, not "
              "derived: atan2(dy, dx) is correct by every derivation available "
              "(test_rotate scores the client's own 0x0040 sends against exactly "
              "that) and sending it turned the agent to face AWAY, observed by the "
              "owner watching the screen. Which is the only instrument that sees "
              "it -- the wire cannot tell a facing from its opposite")
    # THE BOUND HAS TO BE FLOAT32's pi, NOT float64's. Due west is exactly +pi,
    # and float32(pi) = 3.14159274 is GREATER than math.pi = 3.14159265 by 9e-8 --
    # so the obvious `-math.pi <= a <= math.pi` marks a legitimate facing
    # out-of-range. test_smsgnames' version of this check is over LIVE samples,
    # none of which land exactly on the seam, so it never had to notice.
    f32_pi = struct.unpack("<f", struct.pack("<f", math.pi))[0]
    LEDGER.ok(-f32_pi <= angle_of(r[0]) <= f32_pi,
              "and it is inside the range every live sample sits in",
              f"{angle_of(r[0]):.8f} against float32 pi {f32_pi:.8f} (float64 pi "
              f"is {math.pi:.8f}, which due west overshoots by 9e-8)")
    LEDGER.ok(abs(rate_of(r[0]) - 2.0 * math.pi / 3.0) < 1e-6,
              "and the turn rate is ArenaNet's own quantised maximum, 2*pi/3",
              f"{rate_of(r[0]):.7f} -- a per-creature constant, not a per-message "
              "value")

    # a quarter turn: player due NORTH of the agent must give +pi/2
    north = _world(dist=600.0)
    north["agents"][10]["pos"] = (0.0, -600.0)
    r = rots(_walk(north))
    LEDGER.ok(abs(angle_of(r[0]) + math.pi / 2.0) < 1e-5,
              "a player due north of the agent emits -pi/2, not +pi/2 or 0",
              f"{angle_of(r[0]):.5f} -- bearing +pi/2, emitted -pi/2. This is the "
              "check that separates atan2(y, x) from atan2(x, y), which the "
              "due-east case above cannot: swapping the arguments emits +pi here")

    # 2. it is NOT re-announced when nothing has changed
    quiet = rots(_walk(state, n=5, elapsed=0.02))
    LEDGER.ok(not quiet,
              "a facing that has not changed is not re-announced",
              f"{len(quiet)} over five ticks -- ungated this is 20 rotation "
              "messages a second at an agent already looking the right way")

    # 3. THE WRAP. An agent looking near due west is the case where a naive
    #    difference reads 6.2 radians instead of 0.08 and re-announces forever.
    # SOUTH, not north. The agent is looking at +pi and the seam is crossed only
    # when the angle goes NEGATIVE -- a hair north gives +3.139, which an unwrapped
    # difference reads as 0.003 and stays quiet about anyway. This check passed
    # against a sabotaged (unwrapped) server until that was noticed: it was
    # asserting silence in a case where both versions are silent.
    state["pos"] = (0.0, -1.0)                    # a hair SOUTH: angle flips to -pi
    wrapped = rots(_walk(state, n=3, elapsed=0.02))
    LEDGER.ok(not wrapped,
              "and a facing that crosses the +/-pi seam is still 'unchanged'",
              f"{len(wrapped)} -- the shortest way round from +3.1416 to -3.1383 "
              "is 0.003 rad, not 6.28. Unwrapped, this agent re-announces on every "
              "tick forever, and this check goes red when the wrap is removed")

    # 4. a real turn IS announced
    state["pos"] = (0.0, 900.0)
    turned = rots(_walk(state, n=1, elapsed=0.02))
    LEDGER.ok(len(turned) == 1,
              "but a player who has actually moved round does get a new facing",
              f"{len(turned)}")

    # 5. standing exactly on the player has no direction, and atan2(0, 0) is 0.0
    #    rather than an error -- so an ungurded version silently means "face east"
    # CALLED DIRECTLY, because enemy_move_tick never gets there: an agent standing
    # on the player is inside melee range, so the chase returns before facing is
    # considered and the check passed without executing the code it names.
    on_top = _world(dist=600.0)
    on_top["agents"][10]["pos"] = (0.0, 0.0)
    direct = []
    authsrv.face_player(
        lambda op, v, label="", quiet=False: direct.append((op, v, label)),
        on_top, 10, on_top["agents"][10], 1, force=True)
    LEDGER.ok(not direct,
              "and an agent standing exactly on the player announces no facing",
              "atan2(0, 0) returns 0.0 rather than raising, so the unguarded "
              "version silently turns to face due east. force=True here, so the "
              "epsilon cannot be what produces the silence")

    # 6. the fields are FLOAT BITS in dword slots. Read raw, the angle check
    #    above compares garbage to pi -- the exact failure test_smsgnames records.
    # a NORTH fixture, not the due-east one: due east emits exactly 0.0, whose
    # float bits are 0x00000000, and a bit-pattern check against zero proves
    # nothing about marshalling either way.
    bits_world = _world(dist=600.0)
    bits_world["agents"][10]["pos"] = (0.0, -600.0)
    raw = rots(_walk(bits_world))[0]
    LEDGER.ok(raw[1] > (1 << 30) and raw[2] > (1 << 29),
              "and both fields go out as float BITS, not as small integers",
              f"angle=0x{raw[1]:08X}, rate=0x{raw[2]:08X} -- a dword field holding "
              "an IEEE float is the ROTATE_PLAYER trap, and a codec change that "
              "started marshalling these as real numbers would show up here")


def section_enemy_skill():
    """It fights back with a SKILL, announced the way ArenaNet announces one.

    THE CORPUS REFUSED THE OBVIOUS ANSWER, which is why this section exists. Our
    server already had a skill message -- GAME_SMSG 0x00E3, which it sends when
    the PLAYER casts -- and reusing it for an NPC would have been the natural
    move. All 6 of the 0x00E3 in the entire live corpus name the player, because
    0x00E3 confirms a cast the CLIENT initiated; the client even logs "Pending
    skill %u copy %d not found" when the echo is wrong, and an NPC's cast has
    nothing to confirm.

    What the corpus does carry is one NPC skill activation, on the int channel:
    0x009F [value 60 = GV_SKILL_ACTIVATED, agent 36, skill 83]. n=1. That is thin
    and it is stated as thin, but it is evidence and the alternative was invention.

    The skill, its activation and its recharge are ArenaNet's, out of the client's
    own table via skilltable.py: 276 matches the profession this server already
    declares for the Hatcher. Only the damage fraction is ours.
    """
    import authsrv

    def cast_msgs(sent):
        return [(op, v) for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT
                and v and v[0] == agents.GV_SKILL_ACTIVATED]

    def dmg_floats(sent):
        return [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
                for op, v, _l in sent
                if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]

    # 1. the opening cast
    state = _world()
    sent = _swings(state)
    casts = cast_msgs(sent)
    LEDGER.ok(len(casts) == 1 and casts[0][1][1] == 10
              and casts[0][1][2] == authsrv.ENEMY_SKILL_BAR[0][0],
              "a hostile opens with its SKILL, named on the int channel",
              f"{casts} -- [GV_SKILL_ACTIVATED, agent, skill]")
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(authsrv.GAME_SMSG_SKILL_ACTIVATED not in ops,
              "and NOT on 0x00E3, which is the player's own cast confirmation",
              f"{[hex(o) for o in ops]} -- all 6 0x00E3 in the live corpus name "
              "the player. Reusing it here is the mistake this section exists to "
              "prevent, and it is the one a reader of authsrv.py would make")
    LEDGER.ok(not dmg_floats(sent),
              "and the cast deals no damage until it lands",
              f"activation is {authsrv.ENEMY_SKILL_BAR[0][1]}s -- damage here is "
              "the instant-cast bug, the same shape the swing had")

    # 2. nothing else happens during the activation window
    LEDGER.ok(not _swings(state, n=4),
              "nothing swings while a cast is in flight",
              "a cast in flight beats everything; otherwise a slow tick lets an "
              "agent cast and swing on the same tick")

    # 3. it lands, and it hurts more than a swing
    state["agents"][10]["cast_lands_at"] = time.time() - 0.001
    land = _swings(state)
    fl = dmg_floats(land)
    LEDGER.ok(len(fl) == 1 and abs(fl[0] + authsrv.ENEMY_SKILL_FRACTION) < 1e-6,
              "and when it lands it deals the SKILL's fraction, not a swing's",
              f"{fl} against skill {-authsrv.ENEMY_SKILL_FRACTION} and swing "
              f"{-authsrv.ENEMY_HIT_FRACTION}")
    LEDGER.ok(authsrv.ENEMY_SKILL_FRACTION > authsrv.ENEMY_HIT_FRACTION,
              "and a skill is worth more than an auto-attack",
              f"{authsrv.ENEMY_SKILL_FRACTION} vs {authsrv.ENEMY_HIT_FRACTION} -- "
              "ours, both of them; the client carries every real number and we do "
              "not read it yet")
    land_ops = [op for op, _v, _l in land]
    LEDGER.ok(authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT not in land_ops,
              "and a landing cast sends no MELEE_ATTACK_FINISHED",
              f"{[hex(o) for o in land_ops]} -- that value names the end of a "
              "SWING, and 40 of the 42 in the live corpus are followed by a "
              "property-16 damage from the same agent. A cast is not a swing")

    # 4. THE NEXT CAST IS A DIFFERENT SKILL, not slot 1 again. This is where the
    #    bar stops being decorative: with one skill the agent would fall back to
    #    swinging here, and the two checks that used to sit in this spot asserted
    #    exactly that. They were correct for a single skill and wrong for a bar.
    state["agents"][10]["last_swing"] = time.time() - 100.0
    after = _swings(state, n=1)
    second = cast_msgs(after)
    LEDGER.ok(len(second) == 1
              and second[0][1][2] == authsrv.ENEMY_SKILL_BAR[1][0],
              "with slot 1 recharging it casts slot 2, not slot 1 again",
              f"{second} -- expected skill {authsrv.ENEMY_SKILL_BAR[1][0]}. "
              "Repeating the first skill is what a bar-shaped constant looks like "
              "when the selector is not really reading the bar")

    # and only when the WHOLE bar is down does it swing
    busy = _world()
    busy["agents"][10]["skill_ready"] = [time.time() + 999.0] * len(
        busy["agents"][10]["skills"])
    busy["agents"][10]["last_swing"] = time.time() - 100.0
    dry = _swings(busy, n=1)
    LEDGER.ok(not cast_msgs(dry)
              and any(op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                      for op, _v, _l in dry),
              "and with the whole bar recharging it goes back to swinging",
              "an agent with nothing ready that also stops swinging reads as a "
              "broken one")

    # 5. skill 0 turns it off, and the agent is on plain swings
    plain = _world()
    plain["agents"][10]["skills"] = ()
    p_sent = _swings(plain)
    LEDGER.ok(not cast_msgs(p_sent),
              "an empty bar leaves the agent on plain swings",
              "the content switch, so a probe can put a non-casting body in the "
              "world without editing code")
    LEDGER.ok(any(op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET
                  for op, _v, _l in p_sent),
              "and it still swings",
              "turning the skill off must not turn the agent off")

    # 6. a cast in flight does not survive its caster, the same as a swing
    for why, kill in (("dies", lambda a: a.update(dead=True)),
                      ("leaves range",
                       lambda a: a.update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0)))):
        mid = _world()
        _swings(mid)
        assert mid["agents"][10]["cast_lands_at"] is not None
        kill(mid["agents"][10])
        mid["agents"][10]["cast_lands_at"] = time.time() - 1.0
        before = mid["player_health"]
        LEDGER.ok(not _swings(mid, n=3) and mid["player_health"] == before,
                  f"a cast in flight does not land if the caster {why}",
                  "an overdue cast plus three ticks and no damage")

    # 7. the skill can kill, and the kill is still the effects bit
    kill_state = _world()
    sent = []
    keep = lambda op, vals, label="", quiet=False: sent.append((op, vals, label))
    needed = int(math.ceil(1.0 / authsrv.ENEMY_SKILL_FRACTION))
    for _ in range(needed):
        authsrv.land_skill(keep, kill_state, 10, kill_state["agents"][10], 1)
    LEDGER.ok(kill_state["player_dead"],
              f"{needed} skill hits kill the player",
              f"health {kill_state['player_health']}")
    kills = [v for op, v, _l in sent
             if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS
             and v == [authsrv.PLAYER_AGENT_ID, agents.EFFECT_DEAD]]
    LEDGER.ok(len(kills) == 1,
              "and the death is still ONE effects-bit message",
              f"{len(kills)} -- property 16 floors at 1 and cannot kill however "
              "it is dressed up")

    # 7b. THE BAR IS A BAR: it works down the slots rather than repeating slot 1.
    #     Every recharge is rolled back except the one under test, so what is
    #     being measured is the ORDER and not the clock.
    bar = _world()
    a = bar["agents"][10]
    picked = []
    for _ in range(len(a["skills"])):
        slot = authsrv.pick_skill(a, time.time())
        if slot is None:
            break
        picked.append(slot)
        a["skill_ready"][slot] = time.time() + 999.0      # "just cast it"
    LEDGER.ok(picked == list(range(len(a["skills"]))),
              "the bar is worked in order, one slot at a time",
              f"{picked} of {len(a['skills'])} slots -- a selector that always "
              "returned the first ready slot without the recharge moving would "
              "give [0, 0, 0, 0], and one that scanned backwards would reverse it")
    LEDGER.ok(authsrv.pick_skill(a, time.time()) is None,
              "and when every slot is recharging, nothing is picked",
              "None rather than slot 0 -- the agent falls through to swinging")

    # 7b-ii. ROUND ROBIN, and this is the check that separates it from the
    #        first-ready-in-order version it replaced. With EVERY slot ready, a
    #        first-ready selector returns slot 0 forever; round robin advances.
    rr = _world()
    r = rr["agents"][10]
    n = len(r["skills"])
    r["skill_ready"] = [0.0] * n
    order = []
    for _ in range(n + 1):
        slot = authsrv.pick_skill(r, time.time())
        order.append(slot)
        r["last_slot"] = slot            # what the cast site does
    LEDGER.ok(order == list(range(n)) + [0],
              "with every slot ready the cursor advances and wraps",
              f"{order} -- first-ready-in-order gives {[0] * (n + 1)} here, and "
              "that is the version this replaced")

    # and the WRAP specifically: the only ready slot sits BEHIND the cursor. The
    # modulo on `start` alone does not cover this -- every check above is
    # satisfied by a selector that sweeps from the cursor to the end of the bar
    # and gives up, which would strand a ready slot 1 whenever the cursor is
    # past it and everything after is recharging.
    wr = _world()
    w = wr["agents"][10]
    later = time.time() + 999.0
    w["skill_ready"] = [0.0] + [later] * (len(w["skills"]) - 1)
    w["last_slot"] = len(w["skills"]) - 2      # cursor points at the last slot
    LEDGER.ok(authsrv.pick_skill(w, time.time()) == 0,
              "and the scan wraps to reach a ready slot behind the cursor",
              "cursor at the end of the bar, only slot 1 ready -- a sweep that "
              "stops at the end returns None here and the agent swings instead "
              "of casting a skill that is up")

    # 7b-iii. THE DEFECT ITSELF, as a regression. 11.5 measured a live run where
    #         slot 4 NEVER fired: recharges of 2, 5, 8, 2 mean a priority list
    #         never walks past slot 3, because slot 1 is back every 2.0 s. Drive
    #         the real bar against a clock and require every slot to get a turn.
    sim = _world()
    sm = sim["agents"][10]
    sm["skill_ready"] = [0.0] * len(sm["skills"])
    clock, fired = 0.0, set()
    for _ in range(400):
        slot = authsrv.pick_skill(sm, clock)
        if slot is not None:
            fired.add(slot)
            sm["skill_ready"][slot] = clock + sm["skills"][slot][2]
            sm["last_slot"] = slot
            clock += sm["skills"][slot][1]     # the activation
        clock += 0.05
    LEDGER.ok(fired == set(range(len(sm["skills"]))),
              "and over a simulated fight EVERY slot on the bar gets used",
              f"fired {sorted(fired)} of {len(sm['skills'])} slots. The live run "
              "in 11.5 produced {276: 6, 253: 3, 312: 3, 289: 0} -- one slot never "
              "used at all -- and this is that defect as a regression check")

    # 7c. RECHARGE IS PER SLOT, not per agent and not per skill id. A bar may
    #     legitimately carry the same skill twice and the second copy must not
    #     inherit the first's cooldown.
    dup = _world()
    d = dup["agents"][10]
    d["skills"] = (authsrv.ENEMY_SKILL_BAR[0], authsrv.ENEMY_SKILL_BAR[0])
    d["skill_ready"] = [0.0, 0.0]
    first = authsrv.pick_skill(d, time.time())
    d["skill_ready"][first] = time.time() + 999.0
    LEDGER.ok(first == 0 and authsrv.pick_skill(d, time.time()) == 1,
              "a bar carrying the same skill twice recharges the two separately",
              "keyed by SLOT, not by id -- keying by id makes the second copy "
              "share the first's cooldown and the bar quietly one shorter")

    # 7d. the ids and timings are the client's, not ours
    LEDGER.ok(len(authsrv.ENEMY_SKILL_BAR) >= 2
              and len({r[0] for r in authsrv.ENEMY_SKILL_BAR})
                  == len(authsrv.ENEMY_SKILL_BAR)
              and len({r[2] for r in authsrv.ENEMY_SKILL_BAR}) > 1,
              "the bar holds several DISTINCT skills with DIFFERENT recharges",
              f"{authsrv.ENEMY_SKILL_BAR} -- varied recharges are what make the "
              "order observable rather than decorative. Ids and timings are "
              "ArenaNet's from skilltable.py; WHICH four, and the priority order, "
              "are ours, and studies/presearing MANIFEST 7 found no base skill bar "
              "on any Pre-Searing creature page it read, so this bar is a fixture "
              "and not a claim about a Hatcher")

    # 8. the content key reaches the entry, same rule as the other two
    LEDGER.ok("skills" in inspect.getsource(authsrv.spawn_enemy),
              "and spawn_enemy carries the skill from the content row",
              "`entry` is a closed literal; a key that is not named there never "
              "arrives, however it is spelled in world.toml")


def section_constants():
    """Every combat constant, against a LITERAL written here.

    WHY A LITERAL. On 2026-08-11 studies/monsterai/FINDINGS.md 5 sabotaged this
    server's combat constants one at a time and re-ran this file. TWELVE OF
    FOURTEEN could be set to a wrong value with all 125 checks still green:

        SWING_WINDUP      0.899 -> 0.2      125/125 PASS
        ENEMY_MELEE_RANGE 150.0 -> 400.0    125/125 PASS
        AGGRO_RANGE      1200.0 -> 1100.0   125/125 PASS
        ENEMY_TURN_RATE   2pi/3 -> 1.0      RED     <- the only one

    That is not an accident of coverage, it is a shape: every other section
    computes its expectation FROM the symbol under test, so the symbol is free to
    move and the test moves with it. A symbol appearing in a test file is not a
    check. `test_burrow.py` is the model that got this right -- it writes 2.00 in
    the test file and compares.

    So this section is deliberately dumb. It carries the number, not the name.
    Changing a constant now costs a second edit HERE, and that edit is where you
    have to say what changed and why -- which is the whole point, because two of
    these are measured, one is corroborated to the bit, and the rest are ours.

    IT IS NOT A CLAIM THAT THE VALUES ARE RIGHT. Most of them are invented and the
    `why` column says so. It is a claim that they cannot change SILENTLY.
    """
    import authsrv

    # (name, literal, label, why)
    PINNED = (
        ("ATTACK_RANGE", 1500.0, "OURS",
         "how far the PLAYER may reach. Nothing measured it"),
        ("AGGRO_RANGE", 1200.0, "OURS",
         "when a hostile notices, and its leash. GWW says the aggro bubble is "
         "1012 and that named creatures differ in BOTH directions, so this is "
         "not even the right SHAPE -- it should be per-creature "
         "(studies/monsterai 4.2)"),
        ("ENEMY_MELEE_RANGE", 150.0, "OURS",
         "reach. Refuted from both sides at once: ArenaNet's own models strike "
         "from ~65, ~599 and ~706 units, so no single number is right "
         "(studies/monsterai 3.3)"),
        ("ENEMY_HIT_FRACTION", 0.10, "OURS", "damage per swing"),
        ("HIT_FRACTION", 0.15, "OURS", "the player's own swing"),
        ("REVIVE_AFTER", 8.0, "OURS", "how long an agent stays dead"),
        ("PLAYER_REVIVE_AFTER", 10.0, "OURS",
         "a timer, not a resurrection shrine. n=0 player deaths in the corpus"),
        ("ENEMY_MOVE_RATE", 0.75, "OURS",
         "216 u/s. NEVER sent to a hostile in the corpus -- ArenaNet's hostiles "
         "take 0.2778, 0.3333, 0.3472 and 1.0 (studies/monsterai 3.4)"),
        ("ENEMY_DEST_RESEND", 120.0, "OURS", "bandwidth, not mechanics"),
        ("ENEMY_FACING_EPSILON", 0.15, "OURS", "bandwidth, not mechanics"),
        ("ENEMY_SKILL_FRACTION", 0.25, "OURS",
         "flat for every skill on the bar, on purpose"),
        ("ENEMY_ATTACK_SPEED", 1.33, "UPSTREAM",
         "agents.ATTACK_SPEED['axe']. The base x modifier FORMULA is corroborated "
         "against the client's own fmul; the 1.33 itself is the wiki's"),
        ("SWING_WINDUP_RATIO", 0.4458, "OBSERVED",
         "mean of 42 paired windups over both live captures. THIS ONE IS "
         "MEASURED -- see the band checks below"),
    )
    for name, literal, label, why in PINNED:
        got = getattr(authsrv, name)
        LEDGER.ok(got == literal,
                  f"{name} is still {literal} ({label})",
                  f"{got} against the literal in this file -- {why}")

    LEDGER.ok(abs(authsrv.ENEMY_TURN_RATE - 2.0 * math.pi / 3.0) < 1e-12,
              "ENEMY_TURN_RATE is still 2*pi/3 (CORROBORATED)",
              f"{authsrv.ENEMY_TURN_RATE!r} -- ArenaNet's own largest quantised "
              "turn rate, bit-identical, and the ONLY constant in this list the "
              "suite could already catch")

    # --- the windup, which is a ratio because a constant was refuted -----------
    #
    # The band is ArenaNet's, measured over both captures. A ratio outside it is
    # not a tuning choice, it is a value no observation supports.
    OBSERVED_MIN, OBSERVED_MAX = 0.4263, 0.4600
    LEDGER.ok(OBSERVED_MIN <= authsrv.SWING_WINDUP_RATIO <= OBSERVED_MAX,
              "the windup ratio sits inside the band ArenaNet's own swings drew",
              f"{authsrv.SWING_WINDUP_RATIO} in [{OBSERVED_MIN}, {OBSERVED_MAX}] "
              "-- 42 paired windups, 4 attackers, 2 declared speeds, both live "
              "captures. The two windup CLUSTERS do not overlap (86 ms apart); "
              "the two RATIO bands do, which is the whole argument")
    LEDGER.ok(not hasattr(authsrv, "SWING_WINDUP"),
              "and the fixed SWING_WINDUP constant is GONE, not merely unused",
              "0.899 s paired with our declared 1.33 implies a ratio of 0.6759 -- "
              "47% above the largest ratio ever observed. Leaving the name bound "
              "invites a future call site to reach for it")
    slow, fast = authsrv.swing_windup(2.0), authsrv.swing_windup(1.0)
    LEDGER.ok(slow > fast and abs(slow / fast - 2.0) < 1e-9,
              "and a slower declared weapon winds up proportionally longer",
              f"{fast:.4f}s at 1.0 against {slow:.4f}s at 2.0 -- a windup that "
              "does NOT move with the declared speed is the refuted model, and "
              "this check is what makes reverting to it cost a red run")
    LEDGER.ok(abs(authsrv.swing_windup(1.33) - 0.5929) < 1e-3,
              "our own Hatcher's windup is 0.593 s, not the 0.899 it shipped with",
              f"{authsrv.swing_windup(1.33):.4f}s -- the number that actually "
              "changed on the wire, named here so the behaviour change is visible "
              "in the test and not only in the diff")

    # --- the bar against the client's OWN table, not against our comment -------
    #
    # This is the check that would have caught the elite error: authsrv.py claimed
    # all four bar skills were "campaign 1, non-elite" and 276 is elite. Nothing
    # read the table, so the comment was the only witness and it was wrong.
    try:
        import pathlib
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "clientscan"))
        import skilltable
        exe, _why = skilltable.find_exe()
        data = pathlib.Path(exe).read_bytes()
        base, count, _score = skilltable.locate_table(data)
        rows = {i: skilltable.parse_record(data, base, i) for i in range(count)}
    except Exception as ex:                                    # pragma: no cover
        # NAMED, not swallowed. The first version of this handler said "no
        # readable client build" for every failure and its actual cause was a
        # method name that does not exist -- a skip that lies about WHY is worse
        # than a red check, because it reads as an environment problem forever.
        LEDGER.skip("the bar vs the client's own skill table",
                    f"{type(ex).__name__}: {ex}")
        rows = None

    if rows:
        bar = authsrv.ENEMY_SKILL_BAR
        missing = [sid for sid, _a, _r in bar if sid not in rows]
        LEDGER.ok(not missing,
                  "every skill on the bar exists in the client's own table",
                  f"missing {missing} of {[b[0] for b in bar]}")
        bad = [(sid, a, rows[sid]["activation"]) for sid, a, _r in bar
               if sid in rows and abs(rows[sid]["activation"] - a) > 1e-6]
        LEDGER.ok(not bad,
                  "and each activation matches the table to the millisecond",
                  f"{bad or 'all four agree'} -- a typo'd activation passed every "
                  "check in this file before this line existed")
        bad_r = [(sid, r, rows[sid]["recharge"]) for sid, _a, r in bar
                 if sid in rows and abs(rows[sid]["recharge"] - r) > 1e-6]
        LEDGER.ok(not bad_r,
                  "and so does each recharge",
                  f"{bad_r or 'all four agree'}")
        elite = sorted(sid for sid, _a, _r in bar
                       if sid in rows and rows[sid]["elite"])
        LEDGER.ok(elite == [276],
                  "and exactly one bar skill is elite, which is 276",
                  f"{elite} -- authsrv.py claimed all four were non-elite until "
                  "2026-08-11. This is not a rule about what a bar may contain; "
                  "it is a pin so the COMMENT and the TABLE cannot drift apart "
                  "again. flags bit 2 is set on 391 of 3,443 rows, so it is a "
                  "real field and not a one-row artifact")
        prof = sorted({rows[sid]["profession"] for sid, _a, _r in bar
                       if sid in rows})
        LEDGER.ok(prof == [3],
                  "and all four share the profession the Hatcher is declared with",
                  f"{prof} against the 3 sent at spawn in 0x00A6 -- the one "
                  "non-arbitrary thing about this selection")


def section_named_builders(codec):
    """The five messages named 2026-08-10 and first sent 2026-08-11.

    Each builder enforces a bound the CLIENT asserts on itself, so what these
    guard against is an assert dialog mid-session rather than a wrong pixel.
    The refusals are checked one by one: a guard nothing exercises rots into a
    comment, and every one of these is a mistake a caller can plausibly make.
    """
    built = {
        0x002B: agents.agent_update_speed(7, 0.5),
        0x002E: agents.agent_update_rotation(7, math.pi / 2, 2.0943952),
        0x0026: agents.agent_update_flags(7, agents.AGENT_KIND_NPC),
        0x00A6: agents.agent_set_profession(7, 4),
        0x0048: agents.agent_set_tabard_visible(7, False),
    }
    bad = []
    for op, vals in built.items():
        raw = codec.encode("GAME_SMSG", op, vals)
        msgs, used, _rest = codec.decode_stream("GAME_SMSG", raw)
        if used != len(raw) or len(msgs) != 1 or list(msgs[0][1][1:]) != list(vals):
            bad.append(f"0x{op:04X}")
    LEDGER.ok(not bad,
              "the five newly-sendable messages encode and read back unchanged",
              f"mismatched: {bad}" if bad else
              "0x002B, 0x002E, 0x0026, 0x00A6, 0x0048 -- each through the real "
              "catalog, consuming exactly its own bytes. Before 2026-08-11 this "
              "server could not send any of them: 0x0026 had a constant and no "
              "send site, the other four were not even defined")

    # 0x002E's payload is two u32s carrying float32 bits. If someone "fixes" the
    # catalog to float -- which the values invite, and which nearly happened to
    # GAME_CMSG 0x0040 -- this goes red instead of the wire silently changing.
    ang = agents.agent_update_rotation(7, math.pi / 2, 2.0943952)
    back = struct.unpack("<f", struct.pack("<I", ang[1]))[0]
    LEDGER.ok(all(isinstance(v, int) for v in ang[1:])
              and abs(back - math.pi / 2) < 1e-6,
              "0x002E marshals its two floats as u32 and the bits survive",
              f"angle bits {ang[1]:#010x} decode to {back:.6f} rad -- the values "
              f"are floats and the marshalling is not, exactly as for GAME_CMSG "
              f"0x0040 ROTATE_PLAYER, where 'correcting' the type would have "
              f"broken a message we understand")

    refusals = [
        ("a speed in units/s, which is the obvious caller error",
         agents.agent_update_speed, (7, 288.0)),
        ("a speed under the client's own floor",
         agents.agent_update_speed, (7, 0.001)),
        ("a facing outside AGENT_FACING_MASK",
         agents.agent_update_speed, (7, 0.5, 0x10)),
        ("an angle outside +/-pi",
         agents.agent_update_rotation, (7, 10.0, 1.0)),
        ("an angle of NaN, which is not the sentinel",
         agents.agent_update_rotation, (7, float("nan"), 1.0)),
        ("a turn rate of zero",
         agents.agent_update_rotation, (7, 0.0, 0.0)),
        ("flags inside the mask the client keeps for itself",
         agents.agent_update_flags, (7, 0x10000)),
        ("a primary profession of 0, which does NOT mean 'none'",
         agents.agent_set_profession, (7, 0)),
        ("a secondary profession equal to the primary",
         agents.agent_set_profession, (7, 4, 4)),
        ("a custom profession WITHOUT the opt-in",
         agents.agent_set_profession, (7, 12)),
        ("a custom SECONDARY without the opt-in",
         agents.agent_set_profession, (7, 4, 12)),
        ("a profession past the u8 the wire carries, even WITH the opt-in",
         agents.agent_set_profession, (7, 256, 0, True)),
    ]
    for label, fn, args in refusals:
        try:
            fn(*args)
            ok = False
        except ValueError:
            ok = True
        LEDGER.ok(ok, f"and it refuses {label}",
                  "raised ValueError" if ok else
                  "ACCEPTED -- the client would have asserted instead")

    # The sentinel is a real value and must NOT be caught by the angle guard.
    spin = None
    try:
        spin = agents.agent_update_rotation(7, float("inf"), 1.0)
        ok = spin[1] == 0x7F800000
    except ValueError:
        ok = False
    LEDGER.ok(ok,
              "but +inf passes, because it is the client's own free-spin sentinel",
              f"angle bits {spin[1]:#010x} == +inf" if ok else
              "the guard swallowed the sentinel, which would make the message "
              "unusable for the one case it is most needed")

    # THE PROFESSION BOUND, against literals written here.
    #
    # This file's own §"combat constants" section exists because twelve of
    # fourteen constants could be set to a wrong value with every check green --
    # every other section computed its expectation FROM the symbol under test, so
    # the symbol was free to move and the test moved with it. Same trap here, so
    # the numbers are literals and not `agents.CHAR_PROFESSIONS`.
    LEDGER.ok(agents.CHAR_PROFESSIONS == 11,
              "the client's compiled profession bound is 11",
              f"{agents.CHAR_PROFESSIONS} -- ids 0..10, MEASURED on build 38797 "
              f"at 29 assert sites across 13 modules (studies/profession/)")
    LEDGER.ok(agents.PROFESSION_FIELD_MAX == 255,
              "and the wire field is a u8",
              f"{agents.PROFESSION_FIELD_MAX} -- 0x00A6 is 8 wire bytes and "
              f"0x00B7 is 9, both carrying profession as one byte")

    # The bound USED to be 6 -- the largest primary our (early-Prophecies) corpus
    # happened to contain -- and enforcing it refused four professions that ship
    # and that reach this function straight from content. This is the regression
    # check for that, and it is a positive: 7..10 must be ACCEPTED.
    shipped_ok = []
    for prof in (7, 8, 9, 10):
        try:
            agents.agent_set_profession(7, prof)
            shipped_ok.append(prof)
        except ValueError:
            pass
    LEDGER.ok(shipped_ok == [7, 8, 9, 10],
              "and professions 7..10 -- which SHIP -- are accepted",
              f"{shipped_ok} of [7, 8, 9, 10]. The old bound of 6 refused all "
              f"four; an Assassin NPC in content raised ValueError")

    custom = None
    try:
        custom = agents.agent_set_profession(7, 12, 0, custom=True)
    except ValueError:
        pass
    LEDGER.ok(custom == [7, 12, 0],
              "and a custom id passes WITH the opt-in, unchanged",
              f"{custom} -- the value must reach the wire as sent; a guard that "
              f"clamped it would make the probe measure our clamp, not the client")


def section_probe_encoding():
    """Every probe step must ENCODE, and nothing in the suite checked that.

    `probes.check_encodable()` exists precisely because a probe that fails to
    encode wastes a whole client run -- the client has to be launched, logged in
    and walked into a map before the first packet fires. It was reachable only
    from `probes.py`'s own `__main__`, so the suite never ran it and a broken
    probe would have been discovered by spending the run.
    """
    import probes
    failures = probes.check_encodable(quiet=True)
    LEDGER.ok(failures == 0,
              "every step of every probe encodes",
              f"{failures} failures -- an unencodable step is only discovered "
              f"by launching a client, which is the most expensive way to find "
              f"a typo in this repo")


def section_unlock_bitmap():
    """Bit 0 of the unlock bitmap, which is the whole profession-arc crash.

    OBSERVED (build 38797): 0x00DB's payload becomes a bitmap at
    ctx[0x2c]+0x710, and the skills panel enumerates it with a
    find-next-set-bit iterator that forms `id = (word << 5) + bit` and asserts
    the id NON-ZERO -- `*skill`, ChCliSkill.cpp:1022. So a set bit 0 asserts
    the client the instant the panel opens, at ANY profession: the walk reads
    no profession, and no profession value branches anything on the path.

    OBSERVED (our own vault): 242 of 242 0x00DB sends across every capture we
    have ever taken carry bit 0 -- `db 00 80 00 ff ff ff ff`. Six client
    sessions were spent building and refuting profession stories for it.

    THE NEGATIVE CONTROL IS THE POINT. `range(1, N)` and `range(N)` differ by
    one character, and a test that only reads the current output would pass
    against either if it computed its expectation from the function under test
    -- this file's own combat-constants section exists because twelve of
    fourteen constants could be set wrong with every check green. So the OLD
    version is rebuilt here and required to DIFFER, and the bit count is
    asserted against a literal.
    """
    import authsrv

    words = authsrv.unlock_all_words()
    LEDGER.ok(not (words[0] & 1),
              "bit 0 is CLEAR in the unlock bitmap -- skill id 0 is not a skill",
              "a set bit 0 makes the client's own panel iterator enumerate id "
              "0 and assert *skill (ChCliSkill.cpp:1022) the moment the "
              "Skills panel opens, at every profession")
    n_set = sum(bin(w).count("1") for w in words)
    LEDGER.ok(n_set == 3442,
              "and exactly 3442 ids are unlocked, ids 1..3442",
              f"{n_set} -- literal, not computed from SKILL_TABLE_ROWS, so "
              f"the count cannot move silently with the constant")
    ids = [s for s in range(len(words) * 32)
           if words[s // 32] >> (s % 32) & 1]
    LEDGER.ok(ids[0] == 1 and ids[-1] == authsrv.SKILL_TABLE_ROWS - 1,
              "the lowest unlocked id is 1 and the highest is the last table row",
              f"{ids[0]}..{ids[-1]} against 1..{authsrv.SKILL_TABLE_ROWS - 1}")

    # The old version, rebuilt. It must DIFFER, and differ in exactly bit 0 --
    # a check that merely reproduced the current output would pass against the
    # defect it exists to catch.
    old = [0] * authsrv.UNLOCK_WORDS
    for sid in range(authsrv.SKILL_TABLE_ROWS):
        old[sid // 32] |= 1 << (sid % 32)
    LEDGER.ok(old != words and (old[0] & 1) and old[0] ^ words[0] == 1,
              "NEGATIVE CONTROL: the pre-fix version sets bit 0 and this one "
              "does not, differing in exactly that bit",
              f"old word0 {old[0]:#010x} vs {words[0]:#010x} -- if these ever "
              f"match, the fix has been reverted and every session is back to "
              f"asserting on panel open")

    # The explicit-list arm has ALWAYS skipped id 0; the regression is that
    # the two arms disagreed, so both are checked from here on.
    explicit, _ = authsrv.build_unlock_bitmap("0,1,316")
    LEDGER.ok(not (explicit[0] & 1) and (explicit[0] >> 1 & 1),
              "and the explicit-list arm still drops id 0 while keeping id 1",
              f"word0 {explicit[0]:#010x} -- this arm's `sid <= 0` guard was "
              f"correct all along; only the 'all' arm was wrong")
    _, label = authsrv.build_unlock_bitmap("all")
    LEDGER.ok("3442" in label,
              "and the banner reports 3442, so an operator reading the log "
              "sees the real count",
              f"{label!r} -- it said 3443 while sending a bit that is not a "
              f"skill")

    # THE STARTUP REFUSAL. A regression here costs a launch, a login and a map
    # load to observe, so it must die before the socket opens -- and it must
    # die rather than silently repair, or the next bad producer ships unseen.
    refused = None
    try:
        authsrv.refuse_skill_zero(old, "all")
    except SystemExit as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None and "1022" in refused,
              "a bitmap with bit 0 set is REFUSED at startup, naming the "
              "client assert it would cause",
              f"{refused!r} -- without this the failure surfaces as a client "
              f"crash twelve seconds into a session, which is how it survived "
              f"seven of them")
    # POSITIVE CONTROL: a guard that refuses everything protects nothing,
    # because the server never starts.
    passed = authsrv.refuse_skill_zero(list(words), "all")
    empty = authsrv.refuse_skill_zero([0] * authsrv.UNLOCK_WORDS, "none")
    LEDGER.ok(passed == words and empty[0] == 0,
              "while the real bitmap and an empty one pass untouched",
              "the guard must not clear the bit or reject legitimate input -- "
              "it reports, it does not repair")
    both_arms = 0
    for spec in ("all", "bar", "none", "316,317"):
        w, _ = authsrv.build_unlock_bitmap(spec)
        both_arms += 0 if (w[0] & 1) else 1
    LEDGER.ok(both_arms == 4,
              "and every --unlocks arm routes through the guard clean",
              f"{both_arms}/4 -- 'all' and the explicit arm are separate code "
              f"paths and only one of them was ever wrong")


def section_spawn_profession():
    """--spawn-profession: the burst's 0x00B7, built through the guard.

    RUNS.md section 8: a mid-session SKILLBAR_UPDATE followed by opening the
    skills panel asserts the client at a LEGAL profession, so the only clean
    delivery of a custom profession is the spawn burst itself. This section
    pins the payload builder, the pairing warning, and -- on the syntax tree --
    that the burst's send site actually calls the builder, because a literal
    list restored there would silently disconnect the flag while every other
    check stayed green.
    """
    import ast
    import authsrv

    LEDGER.ok(authsrv.spawn_profession_values() == [1, 1, 0, 0],
              "the default burst payload is unchanged: profession 1, agent 1",
              f"{authsrv.spawn_profession_values()} -- [agent_id, primary, "
              f"secondary, is_pvp]; the flag must not move the default path")
    LEDGER.ok(authsrv.spawn_profession_values(3) == [1, 3, 0, 0],
              "an in-band override threads through unchanged",
              f"{authsrv.spawn_profession_values(3)}")
    LEDGER.ok(authsrv.spawn_profession_values(12) == [1, 12, 0, 0],
              "and an out-of-band id passes -- custom is DERIVED, not defaulted",
              f"{authsrv.spawn_profession_values(12)} -- the builder computes "
              f"custom from the value, so 12 traverses the guard's u8 ceiling "
              f"rather than bypassing the guard")
    refused = None
    try:
        authsrv.spawn_profession_values(0)
    except ValueError as ex:
        refused = str(ex)
    LEDGER.ok(refused is not None,
              "a primary of 0 is still refused THROUGH the builder",
              f"{refused!r} -- 0 never occurs in the corpus and does not mean "
              f"'none'; a builder that bypassed the guard would send it")

    # The pairing warning, in both directions -- a warning that fires either
    # way is noise (the enemy warning's rule).
    warn = authsrv.spawn_probe_warning("profession_spawn", False)
    LEDGER.ok(warn is not None and "--spawn-profession" in warn,
              "profession_spawn without the flag WARNS",
              f"{warn!r} -- without it the session measures the default "
              f"profession, which run 2 already covered")
    LEDGER.ok(authsrv.spawn_probe_warning("profession_spawn", True) is None
              and authsrv.spawn_probe_warning("profession_ab", False) is None,
              "and the warning is silent when paired, and for other probes",
              "a warning that fires on a correctly-invoked run trains the "
              "operator to ignore it")

    # The send site, on the SYNTAX TREE: the call that sends 0x00B7 in the
    # spawn burst must take its values from spawn_profession_values(), not
    # from a literal list. A grep cannot tell a call site from this comment.
    with open(authsrv.__file__, encoding="utf-8") as f:
        tree = ast.parse(f.read())
    wired = False
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "send" and node.args
                and isinstance(node.args[0], ast.Name)
                and node.args[0].id == "GAME_SMSG_PLAYER_UPDATE_PROFESSION"):
            wired = any(isinstance(inner, ast.Call)
                        and isinstance(inner.func, ast.Name)
                        and inner.func.id == "spawn_profession_values"
                        for inner in ast.walk(node.args[1]))
    LEDGER.ok(wired,
              "the burst's 0x00B7 send site calls the builder (syntax tree)",
              "a literal list restored at the send site would disconnect "
              "--spawn-profession while the builder's own checks stay green")


def section_pool_fraction():
    """The 0x00A3 float channel, and the crash that hid behind a `<=`.

    OBSERVED 2026-08-11: the client asserted `fraction <= 1.0f` at
    `CharPool.cpp:84` two seconds after the first kill this server drove all the
    way to a revive. `revive_due` had sent property 34 with `max_health` --
    100.0 -- where the client wanted a FRACTION of a pool. The crash trace
    carries our own message three frames under the assert.

    WHY NOTHING CAUGHT IT, and it is the reason this section is worth its
    checks: the client's bound is `<=`, so it can only fire on a POSITIVE value,
    and every number this server had ever put on that channel was damage --
    `-HIT_FRACTION`, and the -50.0 behind `GV_HEALTH`'s comment. A negative
    passes `fraction <= 1.0f` however absurd it is. Twenty sessions of damage
    testing exercised that bound VACUOUSLY. So the checks below deliberately
    push on the positive side, which is the side no earlier test could reach.

    The last two are the ones that would have caught it: they drive the REAL
    `revive_due` and `hit_enemy` and read the float back off the wire, rather
    than asking `_fraction` about itself. Putting `max_health` back where 1.0
    now sits turns them red.
    """
    import authsrv

    # 1. the exact value that crashed the client, and its neighbours
    for bad in (100.0, 1.5, -1.0001, float("inf")):
        try:
            authsrv._fraction(bad, agents.GV_HEALTH, "test")
            refused = None
        except ValueError as ex:
            refused = str(ex)
        LEDGER.ok(refused is not None and "CharPool" in refused,
                  f"{bad!r} on the float channel is REFUSED, and the refusal "
                  f"names the client assert",
                  refused.split(":")[0] if refused else
                  "ACCEPTED -- this is the shape that took the client down")

    # 2. and the legitimate range still passes, unchanged. A guard that CLAMPED
    #    would also stop the crash and would be worse: it turns a wrong number
    #    into a plausible one and the next caller never learns. So the accepted
    #    values must come back as the same bits _f32 would give.
    for good in (1.0, 0.0, -authsrv.HIT_FRACTION, -1.0):
        LEDGER.ok(authsrv._fraction(good, agents.GV_HEALTH, "t") ==
                  authsrv._f32(good),
                  f"{good!r} passes through with its bits untouched",
                  f"0x{authsrv._f32(good):08X} -- a guard, not a transform")

    # 3. THE CHECK THAT WOULD HAVE CAUGHT IT. Drive the real revive and read the
    #    emitted float back off the wire.
    sent = []
    state = {"agents": {10: {"name": "hatcher", "dead": True, "died_at": 0.0,
                             "health": 0.0, "max_health": 100.0,
                             "last_hit": 0.0}}}
    authsrv.revive_due(lambda op, vals, label="": sent.append((op, vals, label)),
                       state, 1)
    floats = [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
              for op, v, _l in sent
              if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(bool(floats),
              "a real revive puts a value on the 0x00A3 float channel",
              f"{len(sent)} message(s): "
              f"{[hex(op) for op, _v, _l in sent]}")
    LEDGER.ok(floats and all(-1.0 <= f <= 1.0 for f in floats),
              "and every one of them satisfies the client's own bound",
              f"{floats} -- this read 100.0 until 2026-08-11 and crashed the "
              f"client on CharPool.cpp:84. max_health here is 100.0 on purpose, "
              f"so restoring the old code makes this red rather than merely "
              f"different")

    # 4. the damage side too -- same channel, and the side that was always safe.
    #    Worth a check anyway: it is the one that pinned HIT_FRACTION as a
    #    fraction in the first place, and it now shares the guard.
    sent2 = []
    state2 = {"agents": {10: {"name": "hatcher", "dead": False, "died_at": 0.0,
                              "health": 100.0, "max_health": 100.0,
                              "last_hit": 0.0}}}
    authsrv.hit_enemy(lambda op, vals, label="": sent2.append((op, vals, label)),
                      state2, 10, 1)
    dmg = [struct.unpack("<f", struct.pack("<I", v[-1]))[0]
           for op, v, _l in sent2
           if op == authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_FLOAT_TARGET]
    LEDGER.ok(dmg and all(-1.0 <= f <= 1.0 for f in dmg),
              "and so does the damage a real swing sends",
              f"{dmg} against HIT_FRACTION={authsrv.HIT_FRACTION}")


if __name__ == "__main__":
    sys.exit(main())
