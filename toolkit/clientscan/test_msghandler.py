r"""The receive-handler classifier: the loopback sweep's prediction, and its controls.

`studies/reconstruction/FINDINGS.md` §4.11 proposes sending every catalogued GAME_SMSG
opcode ArenaNet has never shown us to a real client on loopback and recording what
happens. A sweep with no stated prediction is a fishing trip, so `msghandler --classify`
computes the prediction from the binary first. This file is what stops that prediction
from being unfalsifiable.

THREE THINGS IT PINS, and each one corrected a claim that was in circulation:

  1. **Every receive-table entry dispatches.** 477 of 477 carry a non-null handler
     pointer, so there is no "inert by construction" bucket and a silent sweep result is
     a fact about the READOUT, never about reachability. The sweep's design assumed such
     a bucket existed.

  2. **The denominator is 324, not 332.** 332 is `487 - 155` over `schema/messages.json`;
     the client's receive table holds 477, and 153 of the 155 observed opcodes are in it.
     Two denominators, both defensible, and the difference is exactly the ten opcodes
     the schema carries with no receive entry.

  3. **"Absent from the table" does NOT mean "inert",** and the counterexample was
     already in hand: `0x000C` and `0x000D` are two of those ten, ArenaNet sends them
     145 and 144 times, and they are the latency round trip that drives the client's net
     graph (`toolkit/authsrv/test_ping.py`). They are handled below the message table.

AND ONE RESULT THAT IS NOT ABOUT THE SWEEP AT ALL. `toolkit/authsrv/agents.py` records
GWCA's four generic-value message shapes -- int/float x no-target/with-target -- and
says of the middle two: "INFERRED from the field shapes matching; nothing has confirmed
them on the wire." The client's own dispatch table confirms them structurally: 0x009F
and 0x00A0 forward to ONE function, 0x00A2 and 0x00A3 forward to a DIFFERENT one, and
the field counts differ by exactly the target slot. That is a witness which was not
consulted to make the claim.

Needs capstone and pefile (CLAUDE.md's read-only client-analysis carve-out) and the
pinned client. Without either, every section skips and the floor takes the run red.

    python toolkit/clientscan/test_msghandler.py
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
import checks  # noqa: E402

# Floor 9, measured from a green run on 2026-08-11: 3 table + 3 denominator +
# 3 generic-value. Every one needs the disassembler and the pinned client, so a machine
# without them declares its skips and lands under the floor -- the classifier's whole
# output is a claim about one specific binary and a run that could not open it has
# checked nothing.
LEDGER = checks.Ledger("msghandler: receive-handler classification", floor=9)

# MEASURED on build 38797, 2026-08-11, and written as literals rather than recomputed
# from the module under test. A symbol appearing in a test file is not a check.
RECV_ENTRIES = 477
SCHEMA_OPCODES = 487
NOT_IN_TABLE = {0x000A, 0x000B, 0x000C, 0x000D, 0x000E, 0x004F, 0x0055, 0x007F,
                0x014A, 0x01DA}
# 241 forwarders share only 215 distinct callees, and just 8 callees are shared at all.
# That rarity is what makes the generic-value pairing below evidence rather than noise.
SHARED_CALLEES = 8


def main():
    try:
        import msghandler as mh
    except SystemExit:
        LEDGER.skip("the classifier runs", "capstone/pefile not installed")
        return LEDGER.verdict()
    try:
        img = mh.Image()
    except (SystemExit, OSError) as exc:
        LEDGER.skip("the classifier runs", f"no pinned client to read ({exc})")
        return LEDGER.verdict()

    table = mh.classify(img)

    # ---- 1. every entry dispatches ------------------------------------------
    print("1. the receive table")
    LEDGER.ok(len(table) == RECV_ENTRIES,
              f"{RECV_ENTRIES} receive-table entries", f"{len(table)}")
    LEDGER.ok(all(v["handler"] for v in table.values()),
              "every one carries a non-null dispatch pointer",
              "so the sweep has NO 'inert by construction' bucket, and a silent result "
              "is a fact about the readout rather than about reachability")
    kinds = {v["class"] for v in table.values()}
    LEDGER.ok(kinds == {"FORWARDER", "BODY"},
              "and the partition is exactly FORWARDER | BODY", f"{sorted(kinds)}")

    # ---- 2. the denominator, and the counterexample it comes with ------------
    print("\n2. the denominator")
    repo = os.path.dirname(HERE)
    with open(os.path.join(os.path.dirname(repo), "schema", "messages.json"),
              encoding="utf-8") as fh:
        schema = {int(k) for k in json.load(fh)["channels"]["GAME_SMSG"]["messages"]}
    LEDGER.ok(len(schema) == SCHEMA_OPCODES,
              f"the schema catalogues {SCHEMA_OPCODES} GAME_SMSG opcodes",
              f"{len(schema)}")
    LEDGER.ok(schema - set(table) == NOT_IN_TABLE,
              "exactly ten are catalogued with no receive-table entry",
              f"{sorted(hex(o) for o in schema - set(table))}")
    # The correction that matters, and it needs no capture to state: two of those ten
    # are the ping pair, which the client unmistakably acts on. So the sweep must not
    # predict silence from table-absence. test_ping.py owns the behaviour; this owns
    # the structural half.
    LEDGER.ok({0x000C, 0x000D} <= NOT_IN_TABLE
              and not ({0x000C, 0x000D} & set(table)),
              "and 0x000C/0x000D are among them -- the latency round trip, which the "
              "client demonstrably acts on",
              "'absent from the table' therefore does not mean 'inert'; they are "
              "handled below the message table, which is where a keepalive belongs")

    # ---- 3. the generic-value pairing ---------------------------------------
    print("\n3. GWCA's four generic-value shapes, confirmed by the dispatch table")
    ints = (table[0x009F], table[0x00A0])
    floats = (table[0x00A2], table[0x00A3])
    LEDGER.ok(ints[0]["callees"] and ints[0]["callees"] == ints[1]["callees"],
              "0x009F and 0x00A0 forward to the SAME function",
              f"0x{ints[0]['callees'][0]:08x} -- the two int shapes")
    LEDGER.ok(floats[0]["callees"] and floats[0]["callees"] == floats[1]["callees"]
              and floats[0]["callees"] != ints[0]["callees"],
              "0x00A2 and 0x00A3 forward to a DIFFERENT one",
              f"0x{floats[0]['callees'][0]:08x} -- the two float shapes. agents.py has "
              f"the middle two of the four marked INFERRED, 'nothing has confirmed them "
              f"on the wire'; this is a witness that was not consulted to make the claim")
    # THE CONTROL. If callees were shared widely, two opcodes sharing one would mean
    # nothing at all. Measured: 241 forwarders over 215 distinct callees, only 8 shared.
    shared = {}
    for opcode, v in table.items():
        if v["class"] == "FORWARDER":
            shared.setdefault(v["callees"][0], []).append(opcode)
    n_shared = sum(1 for ops in shared.values() if len(ops) > 1)
    LEDGER.ok(n_shared == SHARED_CALLEES,
              f"CONTROL: only {SHARED_CALLEES} callees are shared by more than one "
              f"opcode at all",
              f"{n_shared} of {len(shared)} -- sharing is rare, so the two pairings "
              f"above are evidence rather than a property of the table")

    return LEDGER.verdict()


if __name__ == "__main__":
    sys.exit(main())
