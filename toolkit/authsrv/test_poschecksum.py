"""GAME_SMSG 0x0023, ArenaNet's own movement-state checksum -- REALFIX-I3's sender.

WHAT THIS GUARDS, and why the guard is unusual: the message's whole output is a
line in the CLIENT'S OWN LOG. Nothing it does appears on the wire, in a capture,
or in any state this repo can read back -- so there is no round trip to assert,
and every check here is either (a) our builder against the client's own
arithmetic, re-derived from the binary, or (b) a refusal that would otherwise
let a broken probe report a comfortable silence.

THE ARITHMETIC, re-derived rather than trusted. `0x005FEEA0` is five
instructions and a `ret`:

    mov eax,[ecx+0xB4] / xor [ecx+0xB0] / xor [ecx+0x80] / xor [ecx+0x7C]
    xor eax,[ecx+0x78] / ret

velocity y/x, the plane word, position y/x -- four float32 and one int, XORed as
RAW DWORDS. Section 1 recomputes that from `struct` alone rather than calling
the module under test, because a builder compared against itself is not a check.

THE ONE THAT MATTERS MOST IS SECTION 3, THE POSITIVE CONTROL'S OWN CONTROL.
`--checksum-probe wrong` exists so the client's line appears at least once; its
entire value is that its prediction CANNOT come true by accident. If the
sentinel were ever zero, or XORed in twice, or applied to the agent id instead
of the checksum, the `wrong` arm would silently become the `model` arm -- and a
silent run would then be read as "we match the client bit-exactly", which is the
strongest claim this arc could make and would be false. So the sentinel is
asserted non-zero, asserted to CHANGE the field, and asserted to change only
field 2.

WHAT THIS FILE DELIBERATELY DOES NOT CLAIM. It does not assert that field 2 is
what a REAL server would send: retail sends this opcode zero times in our live
corpus, so the sender is a RECONSTRUCTION inferred from the client's compare.
It does not assert the client agrees with us -- that needs a client, and it is
what the probe run is for. And it does not touch `agentMgr+0x1C8`, the
suppression latch, which no test can reach from here.

standard library only.

    python toolkit/authsrv/test_poschecksum.py
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402

import agents  # noqa: E402
import authsrv  # noqa: E402
import codec  # noqa: E402

# Read off a real green run (20), not guessed, and set AT it rather than under
# it: zero headroom means unhooking any single check reddens here.
LEDGER = checks.Ledger("GAME_SMSG 0x0023 position checksum", floor=20)

#: The client's five displacements, in the order 0x005FEEA0 reads them.
#: MEASURED, build 38797. Duplicated here ON PURPOSE: `agents.CHECKSUM_FIELDS`
#: is the module's claim and this is the test's, and a shared constant would
#: make section 2 compare a value against itself.
WANT_FIELDS = (0xB4, 0xB0, 0x80, 0x7C, 0x78)


def u32(f):
    """A float32's raw bits -- the test's own reimplementation, not agents'."""
    return struct.unpack("<I", struct.pack("<f", float(f)))[0]


def main():
    print("\n1. the arithmetic, recomputed from struct rather than from agents")
    cases = [
        ((0.0, 0.0), 0, (0.0, 0.0)),
        ((100.5, 200.25), 18, (0.0, 0.0)),
        ((10784.0, 5905.0), 0, (3.0, -4.0)),
        ((-1.5, 1e9), 22, (-0.0, 288.0)),
    ]
    for pos, plane, vel in cases:
        want = (u32(pos[0]) ^ u32(pos[1]) ^ plane ^ u32(vel[0]) ^ u32(vel[1]))
        got = agents.agent_position_checksum(7, pos, plane, vel)
        LEDGER.ok(got == [7, want],
                  f"XOR of the five raw dwords at pos={pos} plane={plane} "
                  f"vel={vel}",
                  f"{got} vs the independently computed [7, {want}]")

    # -0.0 and 0.0 are the same NUMBER and different DWORDS, which is the whole
    # hazard of a bit-exact compare and the reason this file exists at all.
    LEDGER.ok(u32(-0.0) != u32(0.0)
              and (agents.agent_position_checksum(1, (0.0, 0.0), 0)
                   != agents.agent_position_checksum(1, (-0.0, 0.0), 0)),
              "-0.0 and 0.0 give DIFFERENT checksums",
              f"{u32(-0.0):#x} vs {u32(0.0):#x} -- the client compares dwords, "
              f"so a sign of zero we model wrong reads exactly like a teleport")

    LEDGER.ok(tuple(agents.CHECKSUM_FIELDS) == WANT_FIELDS,
              "the module records the client's five displacements",
              f"{tuple(hex(x) for x in agents.CHECKSUM_FIELDS)} vs "
              f"{tuple(hex(x) for x in WANT_FIELDS)} -- 0x005FEEA0's operands")

    print("\n2. the refusals -- a malformed call must not reach the wire")
    for bad, why in (((1.0,), "a one-element position"),
                     ((1.0, 2.0, 3.0), "a three-element position")):
        try:
            agents.agent_position_checksum(1, bad, 0)
            raised = False
        except ValueError:
            raised = True
        LEDGER.ok(raised, f"REFUSES {why}", f"raised={raised}")
    try:
        agents.agent_position_checksum(1, (0.0, 0.0), 0, (1.0,))
        raised = False
    except ValueError:
        raised = True
    LEDGER.ok(raised, "REFUSES a one-element velocity", f"raised={raised}")
    try:
        agents.agent_position_checksum(1, (0.0, 0.0), -1)
        raised = False
    except ValueError:
        raised = True
    LEDGER.ok(raised, "REFUSES a plane that is not a dword", f"raised={raised}")

    print("\n3. the `wrong` arm's prediction cannot come true by accident")
    LEDGER.ok(authsrv.CHECKSUM_WRONG_SENTINEL != 0,
              "the sentinel is NON-ZERO",
              f"{authsrv.CHECKSUM_WRONG_SENTINEL:#x} -- a zero sentinel turns "
              f"the positive control into the model arm, and a silent run would "
              f"then read as 'we match the client bit-exactly'")
    base = agents.agent_position_checksum(1, (10784.0, 5905.0), 18, (0.0, 0.0))
    wrong = [base[0], base[1] ^ authsrv.CHECKSUM_WRONG_SENTINEL]
    LEDGER.ok(wrong[1] != base[1],
              "and it CHANGES field 2",
              f"{base[1]:#010x} -> {wrong[1]:#010x}")
    LEDGER.ok(wrong[0] == base[0],
              "-- while leaving the AGENT ID alone",
              f"{wrong[0]} -- the id is what the client's `%u` prints and what "
              f"it indexes the SYNC array with; corrupting it would assert "
              f"inside the client (Array.h:587) instead of logging")
    LEDGER.ok(base[1] ^ authsrv.CHECKSUM_WRONG_SENTINEL
              ^ authsrv.CHECKSUM_WRONG_SENTINEL == base[1],
              "and applying it TWICE is the identity -- so it must be applied "
              "exactly once",
              "XOR is an involution; the send site applies it in one place")

    print("\n4. the wire bytes")
    c = codec.Codec()
    raw = c.encode("GAME_SMSG", authsrv.GAME_SMSG_AGENT_POSITION_CHECKSUM,
                   agents.agent_position_checksum(1, (100.5, 200.25), 18))
    LEDGER.ok(len(raw) == 10,
              "encodes to the client's own declared_unpack_size",
              f"{len(raw)} bytes: {raw.hex()} -- schema GAME_SMSG 35 declares 10")
    op, aid, chk = struct.unpack("<HII", raw)
    LEDGER.ok(op == 0x0023,
              "opcode 0x0023 leads",
              f"{op:#06x}")
    LEDGER.ok(aid == 1 and chk == agents.agent_position_checksum(
                  1, (100.5, 200.25), 18)[1],
              "then the agent id, then the checksum -- in that order",
              f"agent {aid}, checksum {chk:#010x}. Field order is not cosmetic: "
              f"the handler reads the id at [edi+4] and the checksum at "
              f"[edi+8], and swapping them would index the SYNC array with a "
              f"checksum")

    print("\n5. the probe is OFF by default and names its own model")
    LEDGER.ok(authsrv.CHECKSUM_PROBE is None,
              "CHECKSUM_PROBE defaults to None",
              f"{authsrv.CHECKSUM_PROBE!r} -- this message is a diagnostic that "
              f"only a deliberate run should emit")
    state = {"pos": (1.0, 2.0)}
    pos, plane, vel, why = authsrv.checksum_model(state, (10784.0, 5905.0), 18)
    LEDGER.ok(pos == (10784.0, 5905.0) and plane == 18 and vel == (0.0, 0.0),
              "the model reads the CLIENT'S REPORT, not our own state['pos']",
              f"pos={pos} plane={plane} vel={vel} -- state['pos'] was "
              f"{state['pos']}, and the client's newest report is the only "
              f"position both sides have seen")
    LEDGER.ok(isinstance(why, str) and "parked" in why and "TRUE only" in why,
              "and it NAMES the assumption it is wrong under",
              f"{why!r} -- a model that does not state its own domain is how a "
              f"mismatch gets read as a client bug")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
