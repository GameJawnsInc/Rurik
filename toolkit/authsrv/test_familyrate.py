"""REALFIX-A1's family-rate probe: the table, the sender, the cells, the locks.

The probe's whole output is a stream of 0x002B frames on the wire and a
`movespeed` column in a movetap tape -- nothing here can assert the CLIENT's
half (that the handler stores the float to sync +0x60; that is the owner
run's job, and its prediction is registered in REALFIX.md sec.0.3 and on the
startup banner). What this file CAN refuse to let rot: the CONTESTED table's
shape, the sender's loud-skip guard (an unknown movementType must never
KeyError a live connection and never be guessed past), the wire bytes the
codec actually produces, the composition cells that keep the run
unconfoundable, and the source locks on the one gate and one call site --
the 2026-08-25 review's lesson that an unpinned rebind survives every test.

What this file deliberately does NOT claim: that FAMILY_RATE is retail's
true table (CONTESTED -- ~71-72% modal attribution over n=1,049, two live
single-frame witnesses, 214 distinct floats corpus-wide; THE PROBE RUN IS
THE DECIDER), or that sending the float changes anything in the client.
"""
import contextlib
import io
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "schema"))

import agents      # noqa: E402
import authsrv     # noqa: E402
import checks      # noqa: E402
import codec       # noqa: E402

# MEASURED from a real green run on 2026-08-25: 26 checks, no fixture, no
# vault, no client. Set AT the run per the house rule -- zero headroom, so
# unhooking any single check reddens here. (History: the first draft
# declared 26 from a count in the author's head and the ledger went red on
# the 22 that actually ran -- the rule working; the review pass then added
# the ordering/operand locks and the checksum pairwise cell, and the
# measured count landed back on 26 by coincidence, re-read off the run.)
LEDGER = checks.Ledger("the REALFIX-A1 family-rate probe", floor=26)
check = checks.adopt(LEDGER)


class FakeSend:
    """Captures (opcode, values, label) the way the wire would see them."""

    def __init__(self):
        self.sent = []

    def __call__(self, opcode, values, label, quiet=False):
        self.sent.append((opcode, list(values), label))


def main():
    # ---------------------------------------------------------------- 1
    print("1. the CONTESTED table: domain, values, and the two wire witnesses")
    check(set(authsrv.FAMILY_RATE) == set(range(1, 9)),
          f"FAMILY_RATE covers movementType 1..8 exactly "
          f"({sorted(authsrv.FAMILY_RATE)})",
          "the corpus census is 9,463 of 9,463 decoded reports inside 1..8; "
          "a table row outside that range would never fire, and a missing "
          "row inside it would skip a family the run needs")
    check(all(authsrv.FAMILY_RATE[mt] == 1.00 for mt in (1, 2, 3)),
          "forward rows 1-3 carry 1.00",
          "1.0 is the only float this server ever sent (621/621), so the "
          "probe's forward sends are indistinguishable from the baseline -- "
          "the SIGNAL rows are the non-forward ones")
    check(authsrv.FAMILY_RATE[4] == 0.66 and authsrv.FAMILY_RATE[8] == 0.75,
          "and the two rows with live single-frame wire witnesses match "
          "them: 4 -> 0.66 (CANCELWALK-F4, t=108.376, to the player) and "
          "8 -> 0.75 (t=43.262, same capture, to agent 1019 -- the OTHER "
          "connection's agent, disclosed so nobody reads it as a player "
          "frame)",
          "these are the only rows retail has confirmed frame-by-frame; a "
          "drifted value here would send a float no witness supports")
    check(all(agents.AGENT_MIN_MOVE_SPEED <= r <= agents.AGENT_MAX_MOVE_SPEED
              for r in authsrv.FAMILY_RATE.values()),
          f"every rate sits inside the client's own asserted bounds "
          f"[{agents.AGENT_MIN_MOVE_SPEED}, {agents.AGENT_MAX_MOVE_SPEED}]",
          "AgAgent.cpp:2366-2367 -- a value outside them is an assert "
          "dialog mid-run, not a measurement")

    # ---------------------------------------------------------------- 2
    print("\n2. the builder passes the table through, and refuses the "
          "mistakes a caller can make")
    for mt, rate in sorted(authsrv.FAMILY_RATE.items()):
        got = agents.agent_update_speed(authsrv.PLAYER_AGENT_ID, rate, mt)
        if got != [authsrv.PLAYER_AGENT_ID, rate, mt]:
            check(False, f"builder round-trip for mt {mt}", f"{got}")
            break
    else:
        check(True,
              "agent_update_speed(player, rate, mt) == [player, rate, mt] "
              "for all 8 rows",
              "the facing byte IS the movementType, retail's own encoding "
              "([0.66, 4] and [0.75, 8] witnessed)")
    try:
        agents.agent_update_speed(1, 288.0, 4)
        u_per_s = False
    except ValueError:
        u_per_s = True
    check(u_per_s,
          "a units/s value (288.0) is refused by the builder",
          "0x002B's float is a FRACTION of run speed; the u/s channel is "
          "0x0027 AGENT_UPDATE_SPEED_BASE, and confusing them is the "
          "mistake the client's own [0.01, 1.0] assert exists for")

    # ---------------------------------------------------------------- 3
    print("\n3. the sender: one send per known family, a LOUD skip once for "
          "an unknown one, never a KeyError")
    wire, state = FakeSend(), {}
    ok = authsrv._send_family_rate(wire, state, 4)
    check(ok is True and len(wire.sent) == 1,
          f"mt 4 sends exactly one message ({len(wire.sent)})")
    op, values, label = wire.sent[0]
    check(op == authsrv.GAME_SMSG_AGENT_UPDATE_SPEED == 0x002B,
          "on the right opcode", f"0x{op:04x}")
    check(values == [authsrv.PLAYER_AGENT_ID, 0.66, 4],
          "carrying [player, 0.66, 4] -- the F4 witness's exact shape",
          f"{values}")
    check("REALFIX-A1" in label and "movespeed" in label,
          "and the label names the rung and the readout column",
          f"{label!r} -- the capture is the dose record, so the row must "
          f"say what it was for")
    wire, state = FakeSend(), {}
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        r1 = authsrv._send_family_rate(wire, state, 9)
        r2 = authsrv._send_family_rate(wire, state, 12)
    prints = buf.getvalue().count("UNKNOWN movementType")
    check(r1 is False and r2 is False and wire.sent == [] and prints == 1,
          f"unknown movementTypes send NOTHING and print ONCE "
          f"(sends={len(wire.sent)}, prints={prints})",
          "the corpus says mt is strictly 1..8; a bare FAMILY_RATE[mt] "
          "would kill the connection handler on the first counterexample, "
          "and a silent skip would let the census go stale unnoticed")
    wire2, state2 = FakeSend(), {}
    ok2 = authsrv._send_family_rate(wire2, state2, 7)
    check(ok2 is True and wire2.sent[0][1] == [authsrv.PLAYER_AGENT_ID,
                                               0.75, 7],
          "a fresh state sends the side-family row [player, 0.75, 7]",
          f"{wire2.sent}")

    # ---------------------------------------------------------------- 4
    print("\n4. the wire bytes: the codec encodes what the builder makes, "
          "11 bytes, and they decode back")
    c = codec.Codec()
    fields = agents.agent_update_speed(1, 0.66, 4)
    raw = c.encode("GAME_SMSG", 0x2B, fields)
    check(len(raw) == 11,
          f"the frame is 11 bytes ({raw.hex()})",
          "u16 header + u32 agent + f32 rate + u8 facing -- "
          "declared_unpack_size 11 in the schema")
    frames, size, err = c.decode_stream_at("GAME_SMSG", raw, 0)
    vals = frames[0][2] if frames else []
    check(err is None and size == 11 and len(frames) == 1
          and vals[0] == 0x2B and vals[1] == 1
          and abs(vals[2] - 0.66) < 1e-6 and vals[3] == 4,
          f"and decodes back to [43, 1, ~0.66, 4] ({vals})",
          "f32 quantization makes 0.66 -> 0.6600000262; the tolerance is "
          "the float's, not the check's")

    # ---------------------------------------------------------------- 5
    print("\n5. the composition cells: unconfoundable or refused")
    why, _ = authsrv.zero_lead_composition(zero_lead=False,
                                          family_rate_probe=True)
    check(why is not None and "--family-rate-probe requires --zero-lead"
          in why,
          "probe without --zero-lead: refused -- the gate is the zero-lead "
          "verdict, so the flag would be inert with an on-looking log",
          f"{why!r}")
    for mode in ("suppress", "retail-lead"):
        why, _ = authsrv.zero_lead_composition(zero_lead=True,
                                              cancel_answer=mode,
                                              family_rate_probe=True)
        check(why is not None
              and "--family-rate-probe and --cancel-answer" in why,
              f"probe with --cancel-answer={mode}: refused pairwise",
              f"{why!r} -- the lead arms hardcode a rival [1.0, mt] 0x002B "
              f"on the same client field")
    why, _ = authsrv.zero_lead_composition(zero_lead=False,
                                          cancel_answer="suppress",
                                          family_rate_probe=True)
    check(why is not None and "--family-rate-probe and --cancel-answer"
          in why,
          "and the pairwise cell OUTRANKS requires-zero-lead when both "
          "would fire",
          f"{why!r} -- 'you passed two levers' is the more useful refusal, "
          f"the plane/arrival pair's own precedent")
    why, notes = authsrv.zero_lead_composition(zero_lead=True,
                                              family_rate_probe=True)
    check(why is None and any("--family-rate-probe" in n and "[1.0, 1]" in n
                              for n in notes),
          "probe with --zero-lead: ALLOWED, and the note prices the "
          "click-site hazard by its exact signature",
          f"notes={notes}")
    why, notes = authsrv.zero_lead_composition(zero_lead=True, resync=True,
                                              family_rate_probe=True)
    check(why is None,
          "and it composes with --resync (different opcode, different "
          "field; _note_wire_move ignores 0x002B)",
          f"{why!r} -- A1's protocol does not use resync, but a refusal "
          f"here would have no mechanism behind it")

    # ---------------------------------------------------------------- 6
    print("\n6. source locks: the gate, the rebind, the one call site")
    src = open(os.path.join(HERE, "authsrv.py"), encoding="utf-8").read()
    check(src.count("FAMILY_RATE_PROBE = False") == 1
          and src.count("FAMILY_RATE_PROBE = True") == 1
          and "family_rate_probe=a.family_rate_probe" in src,
          "the global defaults False, main() rebinds it exactly once, and "
          "the flag is threaded into the composition matrix",
          "the 2026-08-25 review's lesson: an unpinned rebind survives "
          "every test while the console claims an arm the server is not "
          "running")
    check(src.count("if FAMILY_RATE_PROBE and zero_ok:") == 1
          and src.count("_send_family_rate(") == 2,
          "ONE gate, on the zero-lead verdict, and ONE call site plus the "
          "def",
          "a second send site would double the dose invisibly; a gate not "
          "on zero_ok could put a bare 0x002B outside every witnessed "
          "retail burst shape")
    # The 2026-08-25 review's REAL: string COUNTS pin neither position nor
    # operand -- relocating the gate below the 0x0029 send (wire becomes
    # 0x0025, 0x0029, 0x002B: a shape retail never produced) or hardcoding
    # the call's mt (every send [1.0, 1], the click-confound signature)
    # survived every count. So the slot and the operand are pinned by
    # ORDER and by VERBATIM text.
    gate_at = src.index("if FAMILY_RATE_PROBE and zero_ok:")
    check(src.index("GAME_SMSG_AGENT_MOVE_DIRECTION,\n",
                    src.index("dir_src = (")) < gate_at
          < src.index("if HEADING_GRANT:", gate_at),
          "the gate sits BETWEEN the 0x0025 send and the first grant "
          "block -- the burst slot itself is pinned, not just the gate's "
          "existence",
          "relocated below the 0x0029, every count stays green while the "
          "wire shows 0x0029-then-0x002B, a shape with zero retail "
          "witnesses")
    check("_send_family_rate(send, state, moving)" in src,
          "and the call site passes the report's own movementType, "
          "verbatim",
          "with the operand hardcoded the probe sends [1.0, 1] forever -- "
          "the exact click-confound signature the hazard note prices -- "
          "and no count reddens")

    # ---------------------------------------------------------------- 7
    print("\n7. the checksum pairwise cell (the review's burst-purity gap)")
    why, _ = authsrv.zero_lead_composition(zero_lead=True,
                                          family_rate_probe=True,
                                          checksum_probe="model")
    check(why is not None
          and "--family-rate-probe and --checksum-probe" in why,
          "probe with --checksum-probe: refused -- the 0x0023 rides the "
          "same breath ungated and retail sends that opcode zero times",
          f"{why!r} -- before this cell the pair ran unrefused and the "
          f"burst-shape half of A1's registration was breakable by a "
          f"flag the matrix had never met")
    why, _ = authsrv.zero_lead_composition(zero_lead=True,
                                          checksum_probe="wrong")
    check(why is None,
          "while --checksum-probe alone stays unrefused, as before",
          "the cell is pairwise, not a new licence regime for a flag "
          "whose handler logs and returns 1")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
