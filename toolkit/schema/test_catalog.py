#!/usr/bin/env python3
"""Check our message catalog against the client's own message-format tables.

    python toolkit/schema/test_catalog.py

WHY THIS EXISTS. `schema/messages.json` is an import of ONE lineage's
reconstruction (OpenTyria's `msgdefs.c`) and `schema/overrides.json` corrects it
from the client's own tables. Two claims rest on that pair and nothing enforced
either one:

  * `messages.json`'s provenance note -- "applying every entry here leaves zero
    residual disagreement between our catalog and build 38797's tables".
  * `studies/msgtable/FINDINGS.md` -- 744 of 748 shared messages agree
    field-for-field, the four exceptions being exactly the overrides.

Unenforced, that decays in both directions. A schema edit can silently
reintroduce a disagreement, and -- this is the one that actually happened --
somebody can *believe* they found a disagreement that is not there. A pass
recorded `0x00E3 SKILL_ACTIVATED` as disagreeing with the binary and called it
a live hazard; the client's descriptor is `agent_id, word, dword`, field for
field what we carry, and acting on the report would have broken a working code
path. See studies/enemy/PLAN.md 6o.

WHAT MAKES THIS A CHECK RATHER THAN A RESTATEMENT. It compares against the
recovered tables, not against another copy of our own catalog, and it compares
every shared message rather than the one being argued about -- so a broken
comparator disagrees everywhere instead of agreeing where it is being asked to.
The comparison is on (kind, wire bytes), because the binary does not
distinguish an `agent_id` from a `dword` in its width; comparing on our NAMES
would manufacture disagreements the wire does not have. The type-0/type-1 tags
ARE compared, separately and by count, since those are the two semantic tags
the descriptors carry and mislabelling them is what produced the wrong report.

READ ONLY. Opens the exe for reading and nothing else.
"""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "toolkit"))
sys.path.insert(0, os.path.join(ROOT, "toolkit", "clientscan"))

import msgshape as MS                                        # noqa: E402
import pinned as P                                           # noqa: E402

FALLBACK_EXE = P.LIVE_INSTALL

# MEASURED on build 38797. A change in either number is a real event: the
# catalog moved, the recovery moved, or the client did.
EXPECT_SHARED = 477          # GAME_SMSG opcodes registered AND in our catalog
EXPECT_TYPE0 = 90            # binary type-0 fields among them
EXPECT_TYPE1 = 4             # binary type-1 fields among them

# The client's channel-3 RECV table is AUTH_SMSG, not the game catalog. Its
# entries would otherwise be compared against GAME_SMSG opcodes of the same
# number, which is the same class of mistake as masking an opcode to a byte.
AUTH_RECV_TABLES = (0x00BEC540, 0x00BEC394)

FAILED = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'}  {label}" + (f"   {detail}" if detail else ""))
    if not ok:
        FAILED.append(label)
    return ok


# `pinned.py` resolves AND identifies the client. The vault holds two copies of
# build 38797 at the same size -- pristine and our patched one -- so a local
# resolver naming one of them by directory was picking a file, not a build.
find_exe = P.find


def ours(field):
    """A catalog field -> (kind, wire bytes). None for the header."""
    t, n = field["type"], field["length"]
    if t == "msg_header":
        return None
    if t in ("agent_id", "dword", "float"):
        return ("scalar4", 4)
    if t == "byte":
        return ("scalar", 1)
    if t == "word":
        return ("scalar", 2)
    if t == "vec2":
        return ("vec2", 8)
    if t == "vec3":
        return ("vec3", 12)
    if t == "blob":
        return ("blob", n)
    if t == "string16":
        return ("wstring", 2 + 2 * n)
    if t in ("array8", "array16", "array32"):
        return ("array", 2 + n * {"array8": 1, "array16": 2, "array32": 4}[t])
    if t == "nested_struct":
        return ("nested", 1)
    raise SystemExit(f"unknown catalog field type {t!r}")


def theirs(f):
    """A recovered descriptor field -> the same (kind, wire bytes) pair."""
    if f.kind == "dword":                       # binary types 0 and 1
        return ("scalar4", 4)
    if f.kind == "uint":                        # type 4, count decides width
        return ("scalar4", 4) if f.wire == 4 else ("scalar", f.wire)
    if f.kind in ("vec2", "vec3"):
        return (f.kind, f.wire)
    if f.kind in ("blob", "wstring", "array"):
        return (f.kind, f.wire)
    if f.kind == "nested":
        return ("nested", 1)
    raise SystemExit(f"unknown descriptor kind {f.kind!r}")


def main():
    exe, why = find_exe()
    print(f"client: {exe}\n        ({why})\n")

    img = MS.Image(exe)

    # Guard: everything below is meaningless if the recovery itself has moved.
    print("the recovery this rests on")
    census = img.census()
    check(census == MS.CENSUS_38797, "cmd-slot census matches build 38797",
          f"{census}")
    for op, ok, got in img.oracle_check():
        check(ok, f"oracle 0x{op:04X}")
    check(not img.invariants(), "zero descriptor-invariant violations")

    catalog = json.load(open(os.path.join(ROOT, "schema", "messages.json")))
    over = json.load(open(os.path.join(ROOT, "schema", "overrides.json")))
    msgs = dict(catalog["channels"]["GAME_SMSG"]["messages"])
    msgs.update(over["channels"].get("GAME_SMSG", {}))

    print("\nGAME_SMSG: our catalog against the client's own tables")
    shared, disagreed = 0, []
    t0 = t1 = 0
    for op, direction, tva, disp, cmds in img.messages():
        if direction != "RECV" or tva in AUTH_RECV_TABLES:
            continue
        m = msgs.get(str(op))
        if m is None:
            continue
        try:
            fs = MS.fields(cmds)
        except MS.Undecodable:
            continue
        shared += 1
        mine = [x for x in (ours(f) for f in m["fields"]) if x is not None]
        if mine != [theirs(f) for f in fs]:
            disagreed.append((op, mine, [theirs(f) for f in fs]))
        # The two semantic tags, counted only where the field lists line up so
        # a length mismatch cannot be read as a mislabelling.
        if len(mine) == len(fs):
            for of, bf in zip([f for f in m["fields"]
                               if f["type"] != "msg_header"], fs):
                if bf.type == 0:
                    t0 += 1
                    check_name = of["type"] == "agent_id"
                elif bf.type == 1:
                    t1 += 1
                    check_name = of["type"] == "float"
                else:
                    continue
                if not check_name:
                    disagreed.append((op, f"type-{bf.type} tagged {of['type']}",
                                      "expected agent_id/float"))

    check(shared == EXPECT_SHARED, "shared messages compared",
          f"{shared}, expected {EXPECT_SHARED}")
    check(not disagreed, "every shared message agrees field-for-field",
          f"{len(disagreed)} disagree")
    for op, mine, binary in disagreed[:10]:
        print(f"        0x{op:04X}\n          ours   {mine}\n"
              f"          binary {binary}")

    # The type tags, which is the distinction msgshape used to print away.
    print("\nthe client's two semantic type tags")
    check(t0 == EXPECT_TYPE0, "type 0 fields, all tagged agent_id by us",
          f"{t0}, expected {EXPECT_TYPE0}")
    check(t1 == EXPECT_TYPE1, "type 1 fields, all tagged float by us",
          f"{t1}, expected {EXPECT_TYPE1}")

    # The opcode a pass recorded as a hazard. Pinned by name so the retraction
    # in studies/enemy/PLAN.md 6o cannot quietly stop being true.
    print("\n0x00E3 SKILL_ACTIVATED, the retracted hazard")
    hits = img.lookup(0x00E3, "RECV")
    check(len(hits) == 1, "registered exactly once")
    got = [repr(f) for f in MS.fields(hits[0][4])]
    check(got == ["agent_id", "u16", "u32"],
          "the client reads agent_id, u16, u32 -- what we send", f"{got}")
    check(str(0x00E3) not in over["channels"].get("GAME_SMSG", {}),
          "and needs no override entry")

    print()
    if FAILED:
        print(f"[FAIL] {len(FAILED)} check(s) failed:")
        for f in FAILED:
            print(f"  - {f}")
        return 1
    print("[PASS] all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
