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

import checks                                                # noqa: E402
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

# MEASURED, not guessed: a green run on build 38797 executes exactly 13 checks --
# 1 census + 4 oracles (MS.ORACLE is a fixed four-entry dict) + 1 invariants, then
# 2 for the catalog comparison, 2 for the type tags, and 3 for the 0x00E3
# retraction. None of them are fixture-dependent: the per-message loop adds
# findings to `disagreed`, not checks, so the total does not drift with the
# catalog's size. A run that reports fewer has stopped executing a section.
# 13 -> 25 on 2026-10-01: per_build() adds two per vaulted build, six builds,
# read off the green run.
LEDGER = checks.Ledger("catalog vs client tables", floor=25)

# Same (ok, label, detail) order the call sites below already use.
check = checks.adopt(LEDGER)


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
    # A NAME-ONLY override merges; one carrying `fields` replaces. Same rule as
    # `codec.Codec.__init__`, deliberately restated here rather than imported: this
    # file's subject is OUR CATALOG against the client's own tables, and reading the
    # merged view out of the module that performs the merge would let a merge bug
    # decide what gets compared. A blind `update` -- which is what this was -- drops
    # the layout of every opcode that has only been NAMED, and the comparison below
    # then dies rather than reporting a disagreement.
    for key, row in over["channels"].get("GAME_SMSG", {}).items():
        if "fields" not in row and key in msgs:
            msgs[key] = {**msgs[key], **row}
        else:
            msgs[key] = row

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
    # Refined 2026-08-14: this said "needs no override entry" and went red the
    # day 0x00E3 gained a NAME row (the naming registry lives in overrides).
    # The hazard this check retracts was a FIELD disagreement, so what must
    # stay true is that no field correction exists -- a name-only row is the
    # registry doing its job, not the hazard returning.
    row = over["channels"].get("GAME_SMSG", {}).get(str(0x00E3), {})
    check("fields" not in row,
          "and needs no FIELD correction (name-only override rows are fine)",
          f"override row keys: {sorted(row) or 'none'}")

    per_build()
    return LEDGER.verdict()


# THE CATALOG AS EACH VAULTED BUILD NUMBERS IT (2026-10-01). Build 38974 put a
# new GAME_SMSG at 0x0194 and moved everything above it up one, so "our
# catalog against the client's tables" became a per-build question: this runs
# the comparison above over EVERY vaulted image, through the codec built for
# that image's build (codec.GAME_SMSG_RENUMBER), and requires zero disagreement
# on each. It goes through the Codec on purpose -- the translation is the thing
# under test -- where the pin section above restates the merge so a merge bug
# cannot choose what it compares. THE CONTROL is the same comparison through the
# PIN's numbering: it must disagree heavily on a renumbered build and not at
# all on the others, or the map is unneeded or the comparator blind.
#
# MEASURED 2026-10-01: every build through its own codec compares 477 messages
# (478 on 38974, its new 0x0194 included), and 38797 / 38833 / 38849 / 38888 /
# 38974 agree on every one. Through the pin's numbering 38974 disagrees on 66 --
# NOT on all 121 it moved: 55 of them have the same shape as the neighbour they
# slid onto, which is exactly the silent mislabel the translation exists to stop
# (no framing error would ever have flagged those). 38519 disagrees on 2 under
# either numbering, and they are LAYOUTS, not numbers: 0x008C
# MAP_EXPLORATION_MARK and 0x0092 COMPASS_PING each lack the trailing field the
# pin carries (a byte, a word). No tape is 38519, so the map does not carry
# them; they are pinned here so a change to either reads as a change.
EXPECT_SHARED_BY_BUILD = {38974: 478}       # every other vaulted build: EXPECT_SHARED
EXPECT_DISAGREES_BY_BUILD = {38519: 2}
EXPECT_PIN_DISAGREES_BY_BUILD = {38519: 2, 38974: 66}


def per_build():
    print("\nper build: the catalog through codec.Codec(client_build=...)")
    try:
        sys.path.insert(0, HERE)
        import codec as C                                    # noqa: PLC0415
        import vaultpath                                     # noqa: PLC0415
        root = vaultpath.vault_root()
    except (Exception, SystemExit) as exc:                   # noqa: BLE001
        LEDGER.skip("the per-build catalog", f"{type(exc).__name__}: {exc}")
        return
    images = [(b, os.path.join(root, "client", b.stamp, "Gw.exe")) for b in P.BUILDS]
    images = [(b, p) for b, p in images if os.path.exists(p)]
    if len(images) < 2:
        LEDGER.skip("the per-build catalog",
                    f"needs two vaulted builds; have {[b.number for b, _ in images]}")
        return
    pin_cod = C.Codec()
    for b, path in images:
        cod = C.Codec(client_build=b.number)
        shared = bad = pin_bad = 0
        first = None
        for op, direction, tva, _disp, cmds in MS.Image(path).messages():
            if direction != "RECV" or tva in AUTH_RECV_TABLES:
                continue
            try:
                want = [theirs(f) for f in MS.fields(cmds)]
            except MS.Undecodable:
                continue
            try:
                got = cod.fields_for("GAME_SMSG", cod.schema_opcode("GAME_SMSG", op))
            except C.Undecodable:
                continue
            shared += 1
            mine = [x for x in (ours(f) for f in got) if x is not None]
            if mine != want:
                bad += 1
                first = first or (op, mine, want)
            try:
                pm = [x for x in (ours(f) for f in pin_cod.fields_for("GAME_SMSG", op))
                      if x is not None]
            except C.Undecodable:
                pm = None
            pin_bad += pm != want
        n = EXPECT_SHARED_BY_BUILD.get(b.number, EXPECT_SHARED)
        nb = EXPECT_DISAGREES_BY_BUILD.get(b.number, 0)
        check(shared == n and bad == nb,
              f"{b.number}: {n} messages compared through its own numbering, "
              f"{nb} disagree", f"{shared} compared, {bad} disagree"
              + (f"; first 0x{first[0]:04X} ours {first[1]} binary {first[2]}"
                 if first else ""))
        k = EXPECT_PIN_DISAGREES_BY_BUILD.get(b.number, 0)
        check(pin_bad == k,
              f"{b.number}: CONTROL -- through the PIN's numbering, {k} disagree",
              f"{pin_bad} -- a renumbered build must disagree there, and one the "
              f"map does not name must not")


if __name__ == "__main__":
    sys.exit(main())
