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

LEDGER = checks.Ledger("agent lifetime", floor=74)


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
    return LEDGER.verdict()


def _world(dist=100.0, **over):
    """A player at the origin and one hostile `dist` units away."""
    import authsrv
    entry = {"name": "hatcher", "dead": False, "died_at": 0.0,
             "health": 100.0, "max_health": 100.0, "last_hit": 0.0,
             "pos": (dist, 0.0), "plane": 0,
             "allegiance": agents.ALLEGIANCE_HOSTILE,
             "attack_speed": authsrv.ENEMY_ATTACK_SPEED,
             "effects": 0, "attacks_back": True}
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

    # 1. A SWING IS TWO PHASES SEPARATED BY A WINDUP, which is the shape ArenaNet
    #    uses and the shape the first version of this code got wrong: it sent all
    #    three messages in the same instant, so the damage number landed on the
    #    frame the animation started.
    state = _world()
    sent = _swings(state)
    ops = [op for op, _v, _l in sent]
    LEDGER.ok(ops == [authsrv.GAME_SMSG_AGENT_PROPERTY_UPDATE_INT_TARGET],
              "the opening of a swing is ATTACK_STARTED and nothing else",
              f"{[hex(o) for o in ops]} -- damage arriving here is the "
              "instant-swing bug: 0.899 s of animation with the number already on "
              "screen")
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
            ("out of aggro range", _world(dist=authsrv.AGGRO_RANGE + 1.0)),
            ("dead", _world(dead=True)),
            ("attacks_back off", _world(attacks_back=False)),
            ("mid-burrow", _world(effects=agents.EFFECT_TRANSITION)),
            ("not hostile", _world(allegiance=agents.ALLEGIANCE_ENEMY + 100))):
        LEDGER.ok(not _swings(world),
                  f"a hostile that is {why} does not swing",
                  "silence is the whole assertion here")

    # AND A PENDING LANDING DOES NOT SURVIVE ITS SWINGER. ArenaNet's own seventh
    # swing in the Lakeside tape was truncated exactly this way -- the player
    # killed the worm 0.24 s into a 0.899 s windup and no damage followed.
    for why, kill in (("dies", lambda a: a.update(dead=True)),
                      ("leaves range",
                       lambda a: a.update(pos=(authsrv.AGGRO_RANGE + 9.0, 0.0)))):
        mid = _world()
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
    state = _world()
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
    zero = _world()
    zero["agents"][10]["attack_speed"] = 0.0
    LEDGER.ok(len(_swings(zero, n=8)) == 1,
              "an agent declaring attack speed 0 falls back to a real interval",
              "8 ticks, ONE attack_started -- 0.0 is falsy, and treating it as "
              "'unset' is deliberate: it is the value behind the "
              "m_attackInterval assert. One message rather than three because a "
              "swing now opens and lands separately")

    # 6. the swing honours the AGENT's declared speed, not the player's. The
    #    client was told this agent's attack speed at spawn and animates to it.
    state = _world()
    state["agents"][10]["attack_speed"] = 10.0
    n = len(_swings(state, n=6))
    LEDGER.ok(n == 1,
              "and a slow weapon swings once, not once per tick",
              f"{n} message(s) over 6 ticks at a 10 s interval -- an opening is 1 "
              "message, so anything above 1 means the timer is not being read")


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
