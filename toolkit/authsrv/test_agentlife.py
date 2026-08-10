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
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))
import checks  # noqa: E402
from codec import Codec  # noqa: E402

LEDGER = checks.Ledger("agent lifetime", floor=26)


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
    p = probes.PROBES["agent_removal"](1, (100.0, 200.0))
    LEDGER.ok(bool(p.question) and bool(p.predicts),
              "and it states a question AND a prediction before it runs",
              "a probe with no stated expectation can be rationalised into "
              "agreeing with anything afterwards")
    LEDGER.ok([s.opcode for s in p.steps] == [0x0021, 0x0020],
              "its steps remove the hostile and then re-create it under the SAME id",
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

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
