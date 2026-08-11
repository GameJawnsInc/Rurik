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
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import agents  # noqa: E402
import checks  # noqa: E402
from codec import Codec  # noqa: E402

LEDGER = checks.Ledger("agent lifetime", floor=38)


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
    return LEDGER.verdict()


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


if __name__ == "__main__":
    sys.exit(main())
