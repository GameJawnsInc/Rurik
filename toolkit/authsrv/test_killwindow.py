"""The kill window, checked against ArenaNet's own kills.

Step 9 of studies/combat/PLAN.md. Our server sent one message when an agent
died -- `0x00F1` with the death bit -- where the real service sends three.
This file drives a kill on our own code, pulls every real kill out of the two
live captures, and asserts the two windows agree.

THE ORACLE IS THE CORPUS, not a literal in this file. Section 2 re-derives the
live template from `vault/captures/live/*` on every run, so the day a capture
is added or re-decoded the expectation moves with it rather than drifting into
a stale constant. Section 1's literals exist only so a vault-less machine still
checks something; where they overlap, section 2 is the authority.

WHAT THIS FILE IS REALLY GUARDING, and it is section 3. The corpus holds a
RICHER-looking template than the one we ship: a `0x00EE` PAIR, `[10, 0]`
followed byte-adjacent by `[0, X]`. It is not a kill shape. 6 of its 7
occurrences fire 6.8-31.5 s from any death, inside a recurring broadcast burst
always preceded by `0x009C [agent, 100]`; the seventh landed on the Wolf's kill
tick, and that tick carries the `0x009C` marker too, which is what gives the
coincidence away. Copying the pair would have looked like more fidelity and
been less. Section 3 asserts we do not send it.

Vault-less runs skip sections 2-4 loudly and keep section 1.
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "schema"))
sys.path.insert(0, os.path.join(HERE, ".."))
sys.path.insert(0, HERE)
import checks  # noqa: E402
from codec import Codec  # noqa: E402

CAPTURES = ("20260807T143055", "20260810T235916")
DEATH_BIT = 0x10

# FLOOR 6 = section 1 alone, which is what a machine with no vault runs. A
# green run WITH the vault scores more; setting the floor at the full count
# would turn "no captures" into a failure naming the wrong thing, the same
# reasoning as test_attribtable's archive-less floor.
LEDGER = checks.Ledger("kill window", floor=6)
check = LEDGER.ok


def our_kill_window():
    """Every message our server sends when an agent dies under one swing."""
    import authsrv
    sent = []
    send = lambda op, v, label="", quiet=False: sent.append((op, list(v), label))
    agent = {"name": "t", "dead": False, "last_hit": 0.0,
             "max_health": 10.0, "health": 1.0, "pos": (0.0, 0.0)}
    state = {"agents": {10: agent}, "pos": (0.0, 0.0)}
    authsrv.hit_enemy(send, state, 10, 0)
    assert agent["dead"], "fixture failed to kill"
    # The swing itself is three messages and is not this file's business.
    tail, seen_death = [], False
    for op, v, label in sent:
        if op == authsrv.GAME_SMSG_AGENT_UPDATE_STATUS:
            seen_death = True
        if seen_death:
            tail.append((op, v))
    return tail


def live_kills():
    """[(stamp, conn, t, agent, [(opcode, values)])] for every real death.

    A kill's window is every message on its own tick naming its own agent,
    plus the untargeted reward. Built from the captures, never from a literal.
    """
    import tape as T
    codec = Codec(overrides=os.path.join(HERE, "..", "..", "schema",
                                         "overrides.json"))
    out = []
    for stamp in CAPTURES:
        cap = T.resolve_capture(stamp)
        for conn in T.chain(cap):
            _meta, events = T.load_tape(cap, conn)
            seq, carry = [], b""
            for t, blob in events:
                buf = carry + blob
                msgs, used, _rest = codec.decode_stream("GAME_SMSG", buf)
                carry = buf[used:]
                seq += [(t, op, v) for op, v in msgs]
            for t, op, v in seq:
                if op != 0x00F1 or len(v) < 3 or not (v[2] & DEATH_BIT):
                    continue
                agent = v[1]
                # `vv[0]` is the opcode the codec echoes into the value list;
                # strip it so a live payload compares against what `send()`
                # takes. 0x00EE carries no agent id at all, and 0x009C names
                # the PLAYER rather than the corpse -- so both join the window
                # by opcode, and only the rest by agent. Filtering 0x009C by
                # agent is what made an earlier version of this file score the
                # Wolf's contaminated tick as clean.
                window = [(o, vv[1:]) for tt, o, vv in seq
                          if abs(tt - t) < 0.03
                          and (o in (0x00EE, 0x009C)
                               or (len(vv) > 1 and vv[1] == agent))]
                out.append((stamp, conn, t, agent, window))
    return out


def main():
    import authsrv

    print("1. our kill window is three messages, in ArenaNet's order")
    win = our_kill_window()
    ops = [op for op, _v in win]
    check(ops == [authsrv.GAME_SMSG_AGENT_UPDATE_STATUS,
                  authsrv.GAME_SMSG_AGENT_KILL_REWARD,
                  authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS],
          "status, then reward, then flags",
          f"{[hex(o) for o in ops]} -- the order two uncontaminated live kills "
          f"show (agents 278 and 40)")
    by_op = dict(win)
    check(by_op[authsrv.GAME_SMSG_AGENT_UPDATE_STATUS][1] & DEATH_BIT,
          "the status carries the death bit 0x10")
    check(by_op[authsrv.GAME_SMSG_AGENT_KILL_REWARD] == [0, 26],
          "the reward is a SINGLE [0, 26]",
          f"{by_op[authsrv.GAME_SMSG_AGENT_KILL_REWARD]}")
    check(by_op[authsrv.GAME_SMSG_AGENT_UPDATE_FLAGS][1]
          == authsrv.AGENT_FLAGS_KILLED == 8,
          "the flags byte is 8, not the 9 every create carries")
    # Byte level, because the values above could be right and the encoding wrong.
    codec = Codec()
    blob = codec.encode("GAME_SMSG", authsrv.GAME_SMSG_AGENT_KILL_REWARD, [0, 26])
    check(blob.hex() == "ee00000000001a000000",
          "and the reward encodes to ArenaNet's exact bytes",
          f"{blob.hex()} -- the live capture's own hex for this message")
    check(len([o for o in ops if o == authsrv.GAME_SMSG_AGENT_KILL_REWARD]) == 1,
          "exactly ONE reward message -- not the pair (see section 3)")

    try:
        kills = live_kills()
    except Exception as exc:                                   # noqa: BLE001
        LEDGER.skip("sections 2-4: the capture-backed kill checks",
                    f"sections 2-4: no readable captures ({exc!r}). Section 1's "
                    f"literals still ran, but nothing was checked against "
                    f"ArenaNet's own kills.")
        return LEDGER.verdict()

    print(f"\n2. conformance against {len(kills)} real deaths")
    check(len(kills) == 5,
          f"{len(kills)} deaths in the corpus",
          "5, not the 4 an earlier pass counted: agent 38 dies TWICE on the "
          "same connection (t=19.912 and t=24.259)")
    rewarded = [k for k in kills if any(o == 0x00EE for o, _v in k[4])]
    check(len(rewarded) == 4,
          f"{len(rewarded)} of them carry a reward",
          "agent 38's SECOND death carries neither reward nor flags -- a "
          "repeated EFFECT_DEAD on an already-dead agent awards nothing (n=1)")
    # The clean ones: a kill whose tick has no 0x009C burst marker.
    clean = [k for k in rewarded
             if not any(o == 0x009C for o, _v in k[4])]
    check(len(clean) == 3,
          f"{len(clean)} are CLEAN (no 0x009C burst on the tick)",
          "the fourth is the Wolf, whose tick carries the burst marker AND the "
          "pair -- which is what identifies it as a coincidence")
    for stamp, _conn, t, agent, window in clean:
        rewards = [v for o, v in window if o == 0x00EE]
        check(rewards == [[0, 26]],
              f"the clean kill of agent {agent} (t={t:.3f}) rewards [0, 26]",
              f"{rewards} -- exactly what our server now sends")
    for stamp, _conn, t, agent, window in rewarded:
        flags = [v for o, v in window if o == 0x0026]
        check(flags == [[agent, 8]],
              f"and its flags byte is [{agent}, 8] (t={t:.3f})",
              f"{flags}")

    print("\n3. the PAIR is not a kill shape, and we do not send it")
    pairs = [k for k in rewarded
             if len([v for o, v in k[4] if o == 0x00EE]) > 1]
    check(len(pairs) == 1,
          "exactly one death in the corpus shows the [10,0]+[0,X] pair",
          "the Wolf -- and its tick also carries 0x009C [agent, 100], the "
          "marker every one of the 6 NON-kill pair sightings carries too")
    for _s, _c, _t, _a, window in pairs:
        check(any(o == 0x009C for o, _v in window),
              "and that death's tick carries the 0x009C burst marker",
              "which is the evidence that the pair belongs to the burst rather "
              "than to the kill")
    check(all(v != [10, 0] for o, v in win if o == 0x00EE),
          "our server sends no [10, 0]",
          "copying the pair would have looked like more fidelity and been less")
    check(all(o != 0x009C for o, _v in win),
          "and no 0x009C -- n=1 as a kill signal, and it marks the OTHER "
          "mechanism")

    print("\n4. the flags value, re-counted over both captures")
    import tape as T
    codec2 = Codec(overrides=os.path.join(HERE, "..", "..", "schema",
                                          "overrides.json"))
    hist = {}
    for stamp in CAPTURES:
        cap = T.resolve_capture(stamp)
        for conn in T.chain(cap):
            _meta, events = T.load_tape(cap, conn)
            carry = b""
            for t, blob in events:
                buf = carry + blob
                msgs, used, _rest = codec2.decode_stream("GAME_SMSG", buf)
                carry = buf[used:]
                for op, v in msgs:
                    if op == 0x0026:
                        hist[v[2]] = hist.get(v[2], 0) + 1
    check(hist == {9: 200, 8: 4},
          f"0x0026 carries exactly two values: {hist}",
          "authsrv.py's comment said value 8 was seen 'exactly once -- on the "
          "Wolf'. That was one capture's count; over both it is 4, and all "
          "four are deaths. Corrected at the constant in the same commit")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
