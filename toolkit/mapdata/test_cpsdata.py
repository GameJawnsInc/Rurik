r"""The composite table decoder, its refusals, and the two-witness join.

    python toolkit/mapdata/test_cpsdata.py

WHAT THIS IS REALLY CHECKING. `cpsdata.py` decodes Gw.dat file `0x33EA` into
the id lists and records that name a PLAYER's files. The decode itself is
cheap to make green -- a wrong reading of a self-terminating format still
produces records -- so almost every check here is either a rival that MUST
fail or a witness that shares no method with the decoder.

THE HEADLINE IS THE TWO-WITNESS JOIN (§3). Resolving composite type 1 across
every `(group, profession)` cell and taking the sex slots yields twenty file
ids; an INDEPENDENT FFNA chunk walk over the archive must classify all twenty
as composited -- FA1 present, FA0 absent. Then type 2's twenty must have node
counts equal to type 1's element for element, on skeletons with an order of
magnitude fewer sequences. One witness parses a client data file off disk, the
other walks chunk tables in the archive; nothing is shared but the file ids.

AND THE SABOTAGE THAT MATTERS IS §4, because the obvious acceptance criterion
is vacuous. "Every shell this names is composited and walks" is ALSO true of
the hatcher 116228, a monster shell that is composited and does walk. A
set-based check cannot tell them apart. Only the composite table can, and the
test requires it to: 116228, 116703, 116377 and 116366 must all be ABSENT from
the 16,567 distinct file ids. If that check ever passes them, §4 is measuring
nothing and the floor should not save it.

A DEFECT THIS TEST FOUND IN ITS OWN ACCEPTANCE CRITERION, kept because it is
the repo's "a check that cannot fail is not a check" rule arriving in person.
§2 was first written to assert that a wrong slot-mask width leaves a NON-ZERO
residue. It does not. Every record consumes `4 + 4*popcount` bytes, so a walk
at 9, 10, 11, 12 or 13 slots lands on the exact final byte alike -- the test
went red against a correct module. The assertion is now inverted (the vacuity
itself is checked, so nobody re-derives it) and sits beside the two checks that
do discriminate: record count against section 1's id count, and cross-half type
agreement.

Every literal below was measured on the study archive 2026-08-19 through this
module, and reproduced from scratch by a second script before it was written.
"""

import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, file_id_table  # noqa: E402
from skelfile import Skeleton  # noqa: E402
from cpsdata import (CompositeTable, CpsDataError, PROFESSIONS,  # noqa: E402
                     TYPES, SLOTS, TYPE_SHIFT, COMPOSITE_FILE_ID)
import checks  # noqa: E402
import vaultpath  # noqa: E402

GEOMETRY_CHUNK = 0x00000FA0
SKELETON_CHUNK = 0x00000FA1

#: MEASURED 2026-08-19, study archive, build-independent facts of the file.
SIZE = 105531
N_GROUPS = 4
CELLS = 880
RECORDS = 3803
SECTION1_END = 9367
FILE_REFS = 20238
DISTINCT_FILES = 16567
GEOMETRY_SLOTS = [0, 5, 10]
FFNA_REFS = 6703
ATEX_REFS = 13535

#: The twenty and the twenty. Element order is `sorted((group, profession))`.
SHELLS_T1 = [(0, 1, 15018, 16271), (0, 2, 16049, 12818), (0, 3, 16202, 16267),
             (0, 4, 16203, 15719), (0, 5, 16377, 16257), (0, 6, 15490, 16258),
             (1, 7, 161426, 161433), (1, 8, 161898, 161906),
             (2, 9, 203708, 203713), (2, 10, 204020, 204032)]
SHELLS_T2 = [(0, 1, 18393, 18394), (0, 2, 18395, 18396), (0, 3, 18397, 18398),
             (0, 4, 18399, 18400), (0, 5, 18401, 18402), (0, 6, 18403, 18404),
             (1, 7, 161418, 161428), (1, 8, 161907, 161908),
             (2, 9, 203714, 203715), (2, 10, 204010, 204027)]

#: Type 1's sequence counts are 220-289. Type 2's are 10-17 -- EXCEPT shell
#: 18402, which carries 115. That outlier is real and was found by re-running
#: the claim; the bound below is deliberately loose enough to hold it and
#: tight enough that type 2 could still fail to be the low-animation set.
T1_SEQ_MIN = 200
T2_SEQ_MAX = 130

#: The sabotage set: monster files that ARE composited and DO walk.
MONSTER_FILES = [116228, 116703, 116377, 116366]


# ---------------------------------------------------------------------------
# Section 0: synthetic fixtures, built from their own byte literals. No
# ArenaNet bytes. If cpsdata's arithmetic drifts from this builder, red.
# ---------------------------------------------------------------------------

def synth(n_groups=1, cells=None, records=None):
    """Build a whole composite payload.

    `cells` maps (group, profession, type) -> list of record indices; every
    other cell is empty. `records` is a list of (hdr_extra_bits, {slot: fid}).
    """
    cells = dict(cells or {})
    records = list(records or [])
    out = bytearray()
    out.append(n_groups)
    for g in range(n_groups):
        for prof in range(PROFESSIONS):
            for ty in range(TYPES):
                ids = cells.get((g, prof, ty), ())
                out += struct.pack("<H", len(ids))
                for i in ids:
                    out += struct.pack("<H", i)
    for ty, files in records:
        mask = 0
        for slot in sorted(files):
            mask |= 1 << slot
        out += struct.pack("<I", mask | (ty << TYPE_SHIFT))
        for slot in sorted(files):
            out += struct.pack("<I", files[slot])
    return bytes(out)


def section0(check):
    print("\n-- 0. synthetic fixtures ------------------------------------")

    pay = synth(cells={(0, 3, 7): [0], (0, 4, 7): [1]},
                records=[(7, {0: 1000, 5: 2000}), (7, {10: 3000})])
    t = CompositeTable.decode(pay)
    check(t.n_groups == 1 and len(t.lists) == PROFESSIONS * TYPES,
          "a synthetic payload decodes to its own shape",
          f"groups {t.n_groups}, cells {len(t.lists)}")
    check(len(t.records) == 2 and t.size == len(pay),
          "and closes on its own final byte", f"{t.size} B")
    check(t.records[0].files == {0: 1000, 5: 2000},
          "the slot mask selects exactly the present slots")
    check(t.records[0].type == 7 and t.records[0].mask == 0x21,
          "type comes from bits 22.., mask from bits 0..10")

    check(t.records[0].base_file(0) == 1000 and t.records[0].base_file(1) == 2000,
          "base_file picks the sex slot")
    check(t.records[1].base_file(0) == 3000 and t.records[1].base_file(1) == 3000,
          "and falls back to the shared slot 10 when a sex slot is absent",
          "which is how a sex-invariant record is stored")

    check(t.partition_violations() == {},
          "both synthetic records are referenced exactly once")
    check(t.type_disagreements() == [],
          "and the cell's type axis agrees with each record's own header")

    # A record referenced twice is a FINDING, not a decode failure -- decode
    # must accept it and the closure method must report it. Note the fixture:
    # TWO records and TWO ids, so decode's count equality is satisfied while
    # the partition is violated. That is exactly the case the docstring says
    # the count check cannot see, built here so the claim is tested.
    pay2 = synth(cells={(0, 3, 7): [0], (0, 4, 7): [0]},
                 records=[(7, {0: 1}), (7, {0: 2})])
    t2 = CompositeTable.decode(pay2)
    check(t2.partition_violations() == {0: 2, 1: 0},
          "a record used twice while another goes unused DECODES, and the "
          "partition method reports both",
          "count equality is satisfied here -- partition is strictly stronger")

    pay3 = synth(cells={(0, 3, 7): [0]}, records=[(9, {0: 1})])
    t3 = CompositeTable.decode(pay3)
    check(len(t3.type_disagreements()) == 1
          and t3.type_disagreements()[0][2:] == (7, 9),
          "and a type-axis disagreement is reported with both types")

    check(t.records[0].unnamed == 0,
          "the undecoded header field 11..21 reads zero when unset")
    pay4 = bytearray(synth(cells={(0, 0, 0): [0]}, records=[(3, {0: 7})]))
    hdr_at = 1 + PROFESSIONS * TYPES * 2 + 2
    hdr, = struct.unpack_from("<I", pay4, hdr_at)
    struct.pack_into("<I", pay4, hdr_at, hdr | (1 << 18))
    check(CompositeTable.decode(bytes(pay4)).records[0].unnamed == (1 << (18 - SLOTS)),
          "and carries bit 18 when the file sets it",
          "bits 11..21 are NOT DECODED and must survive a round trip")


def section1(check):
    print("\n-- 1. refusals: the decoder must refuse, not guess ----------")

    check_refuses(check, b"", "an empty payload")
    check_refuses(check, bytes([0]), "nGroup == 0")
    check_refuses(check, bytes([200]) + b"\x00" * 16, "an absurd nGroup")

    good = synth(cells={(0, 0, 0): [0]}, records=[(0, {0: 1})])
    check_refuses(check, good + b"\x00", "one trailing byte -- the closure")
    check_refuses(check, good[:-1], "one byte short of a record's slot")

    truncated = good[:1 + 40]
    check_refuses(check, truncated, "section 1 cut mid-list")

    over = bytearray(good)
    struct.pack_into("<H", over, 1, 60000)
    check_refuses(check, bytes(over), "a list declaring 60,000 entries")

    # The count closure, as a refusal, on a fixture that residue CANNOT catch:
    # two ids, one record, every record a whole number of dwords.
    short = synth(cells={(0, 0, 0): [0, 1]}, records=[(0, {0: 1})])
    check(len(short) % 4 == 1,
          "the mis-framed fixture is dword-consistent in section 2",
          "so residue alone would accept it")
    check_refuses(check, short, "2 section-1 ids framed as 1 record")

    t = CompositeTable.decode(good)
    try:
        t.records[0].base_file(2)
        check(False, "base_file refuses a sex outside 0/1")
    except CpsDataError:
        check(True, "base_file refuses a sex outside 0/1")


def check_refuses(check, payload, what):
    try:
        CompositeTable.decode(payload)
        check(False, f"decode REFUSES {what}", "it returned a table instead")
    except CpsDataError as e:
        check(True, f"decode refuses {what}", str(e)[:78])


# ---------------------------------------------------------------------------
# Section 2: the real table, and the rivals that must fail on it.
# ---------------------------------------------------------------------------

def rival_slots(payload, n_slots):
    """The record parser with the wrong number of file slots.

    Implemented here from its own arithmetic so the module never carries a
    wrong rule as dead code. Returns `(residue, n_records, n_section1_ids,
    type_disagreements)`.

    NOTE WHAT THE RESIDUE DOES NOT DO, because the first version of this test
    asserted it and was wrong. Every record consumes `4 + 4*popcount` bytes, so
    ANY dword-consuming walk lands exactly on the payload end: residue is 0 at
    9, 10, 11, 12 and 13 slots alike. It is not a discriminator and it is
    returned here only so the checks below can SHOW that it is not.
    """
    cur = 1
    n_groups = payload[0]
    lists, total_ids = {}, 0
    for g in range(n_groups):
        for prof in range(PROFESSIONS):
            for ty in range(TYPES):
                n, = struct.unpack_from("<H", payload, cur)
                cur += 2
                lists[(g, prof, ty)] = struct.unpack_from("<%dH" % n, payload, cur)
                cur += 2 * n
                total_ids += n
    hdrs = []
    while cur < len(payload):
        if cur + 4 > len(payload):
            break
        hdr, = struct.unpack_from("<I", payload, cur)
        cur += 4
        cur += 4 * bin(hdr & ((1 << n_slots) - 1)).count("1")
        hdrs.append(hdr)
    bad = 0
    for (g, prof, ty), ids in lists.items():
        for i in ids:
            if i >= len(hdrs) or (hdrs[i] >> TYPE_SHIFT) != ty:
                bad += 1
    return cur - len(payload), len(hdrs), total_ids, bad


def rival_type_shift(table, shift):
    """Cross-half agreement under a wrong type shift."""
    bad = 0
    for (g, prof, ty), ids in table.lists.items():
        for i in ids:
            if (table.records[i].hdr >> shift) != ty:
                bad += 1
    return bad


def section2(check, ar, idt):
    print("\n-- 2. the real table, and two rivals that must fail ---------")

    payload = ar.read(ar.row(idt[COMPOSITE_FILE_ID]))
    check(len(payload) == SIZE,
          f"file 0x{COMPOSITE_FILE_ID:X} is {SIZE} bytes", f"{len(payload)}")

    t = CompositeTable.decode(payload)
    check(t.n_groups == N_GROUPS, f"nGroup == {N_GROUPS}", f"{t.n_groups}")
    check(len(t.lists) == CELLS, f"{CELLS} section-1 cells", f"{len(t.lists)}")
    check(len(t.records) == RECORDS, f"{RECORDS} records", f"{len(t.records)}")
    check(t.section1_end == SECTION1_END,
          f"section 1 ends at {SECTION1_END}",
          "1 + 880*2 + 3803*2 -- the arithmetic closes on the measured offset")

    check(t.partition_violations() == {},
          "every record is referenced by EXACTLY ONE cell",
          "a partition over 3,803 records, not a pool")
    check(t.type_disagreements() == [],
          "and every id's type axis equals its record's own header type",
          "3803/3803 across DISJOINT halves of the file -- two encodings "
          "of one fact agreeing, not one restated")

    refs = list(t.file_refs())
    check(len(refs) == FILE_REFS, f"{FILE_REFS} file references", f"{len(refs)}")
    check(len(t.distinct_file_ids()) == DISTINCT_FILES,
          f"{DISTINCT_FILES} distinct file ids", f"{len(t.distinct_file_ids())}")
    check(t.unresolved_refs(idt) == [],
          "and every one of them resolves in the archive's id table",
          f"{len(refs)}/{len(refs)}")

    kinds = t.slot_kinds(ar, idt)
    geo = sorted(s for s, c in kinds.items() if set(c) == {b"ffna"})
    tex = sorted(s for s, c in kinds.items() if set(c) == {b"ATEX"})
    check(geo == GEOMETRY_SLOTS,
          f"geometry slots MEASURED as {GEOMETRY_SLOTS}, not imported",
          "the client's s_fileFlags says the same; this derived it from "
          "the archive, so the module owes Gw.exe nothing")
    check(len(geo) + len(tex) == SLOTS,
          "and every slot is purely one kind or the other",
          "zero exceptions in either direction")
    n_ffna = sum(sum(kinds[s].values()) for s in geo)
    n_atex = sum(sum(kinds[s].values()) for s in tex)
    check((n_ffna, n_atex) == (FFNA_REFS, ATEX_REFS),
          f"{FFNA_REFS} ffna refs and {ATEX_REFS} ATEX refs",
          f"{n_ffna} / {n_atex}")

    # RIVAL A: the wrong slot count -- and FIRST, the demonstration that the
    # obvious check cannot catch it. This block is here because the test's own
    # first version asserted residue and went red against a correct module.
    residues = {n: rival_slots(payload, n)[0] for n in (9, 10, 11, 12, 13)}
    check(set(residues.values()) == {0},
          "RESIDUE IS VACUOUS for the slot count: 9, 10, 11, 12 and 13 slots "
          "ALL close on the exact final byte",
          "every record is a whole number of dwords, so any dword-consuming "
          "walk lands here -- do not cite residue as pinning the framing")

    true_res, true_n, true_ids, true_bad = rival_slots(payload, SLOTS)
    check((true_n, true_bad) == (true_ids, 0),
          f"what DOES pin it: at {SLOTS} slots the record count equals "
          f"section 1's id count and type agreement is total",
          f"{true_n} records, {true_ids} ids, {true_bad} disagreements")
    for n_slots in (9, 10, 12, 13):
        _, n_rec, n_ids, bad = rival_slots(payload, n_slots)
        check(n_rec != n_ids and bad > RECORDS // 2,
              f"RIVAL: {n_slots} slots mis-frames -- count AND type agreement fail",
              f"{n_rec} records against {n_ids} ids, {bad} type disagreements")

    # RIVAL B: the wrong type shift.
    check(rival_type_shift(t, TYPE_SHIFT) == 0,
          f"cross-half agreement is total at shift {TYPE_SHIFT}")
    for shift in (21, 23):
        bad = rival_type_shift(t, shift)
        check(bad > RECORDS // 2,
              f"RIVAL: shift {shift} collapses cross-half agreement",
              f"{bad} of {RECORDS} disagree")

    return t


# ---------------------------------------------------------------------------
# Section 3: the two-witness join.
# ---------------------------------------------------------------------------

def classify(ar, idt, fid):
    """The INDEPENDENT witness: walk the file's own FFNA chunk table."""
    data = ar.read(ar.row(idt[fid]))
    chunks = {c: (o, s) for c, o, s in ffna_chunks(data)}
    if SKELETON_CHUNK not in chunks:
        return None
    off, size = chunks[SKELETON_CHUNK]
    sk = Skeleton.decode(bytes(data[off:off + size]))
    return {"composited": GEOMETRY_CHUNK not in chunks,
            "n2c": len(sk.anims()), "seq": sk.seq_count}


def section3(check, ar, idt, t):
    print("\n-- 3. the two-witness join ----------------------------------")

    got = {}
    for ty, expect in ((1, SHELLS_T1), (2, SHELLS_T2)):
        shells = t.shells(ty)
        rows = [(g, p, bysex.get(0), bysex.get(1))
                for (g, p), bysex in sorted(shells.items())]
        check(rows == expect,
              f"composite type {ty} resolves to the pinned twenty, "
              f"in the same sex pairing",
              f"{len(rows)} cells")
        info = {}
        for g, p, f0, f1 in rows:
            for fid in (f0, f1):
                info[fid] = classify(ar, idt, fid)
        check(all(v and v["composited"] for v in info.values()),
              f"and all {len(info)} are COMPOSITED -- FA1 present, FA0 absent",
              "witness two: an FFNA chunk walk that never saw the "
              "composite table")
        got[ty] = [info[f] for g, p, f0, f1 in rows for f in (f0, f1)]

    n1 = [v["n2c"] for v in got[1]]
    n2 = [v["n2c"] for v in got[2]]
    check(n1 == n2,
          "type 2's node counts equal type 1's ELEMENT FOR ELEMENT",
          f"{len(n1)}/{len(n1)}: {n1[:6]}...")
    check(len(set(n1)) > 1,
          "and the node counts are not all equal, so that match is a claim",
          f"{len(set(n1))} distinct counts across the twenty")

    s1 = [v["seq"] for v in got[1]]
    s2 = [v["seq"] for v in got[2]]
    check(min(s1) >= T1_SEQ_MIN,
          f"type 1 carries >= {T1_SEQ_MIN} sequences everywhere",
          f"min {min(s1)}, max {max(s1)}")
    check(max(s2) <= T2_SEQ_MAX,
          f"type 2 carries <= {T2_SEQ_MAX} -- the low-animation set",
          f"min {min(s2)}, max {max(s2)} -- the max is shell 18402, the "
          f"outlier that re-running the claim found; the rest are 10-17")
    check(max(s2) < min(s1),
          "and the two sets do not overlap in sequence count",
          "same skeletons, different animation")


# ---------------------------------------------------------------------------
# Section 4: the sabotage that makes section 3 mean something.
# ---------------------------------------------------------------------------

def section4(check, ar, idt, t):
    print("\n-- 4. the sabotage: a monster shell must be REJECTED --------")

    ids = t.distinct_file_ids()
    for fid in MONSTER_FILES:
        info = classify(ar, idt, fid)
        walks = info is not None
        check(fid not in ids,
              f"monster file {fid} is ABSENT from the composite table",
              f"composited={info['composited'] if walks else '?'} -- "
              f"it walks, so only THIS table can reject it")

    hatcher = classify(ar, idt, 116228)
    check(hatcher is not None and hatcher["composited"],
          "and 116228 really is composited and really does walk",
          "which is why a set-based 'is it composited' check would have "
          "passed it as a player shell and measured nothing")


def main():
    led = checks.Ledger("the composite table (Gw.dat 0x33EA)", floor=FLOOR)
    check = checks.adopt(led)

    section0(check)
    section1(check)

    dat = os.path.join(
        vaultpath.require_dir("dat_study", why="the composite table"),
        "Gw.dat")
    with Archive(dat) as ar:
        idt = file_id_table(ar, raw=True)
        t = section2(check, ar, idt)
        section3(check, ar, idt, t)
        section4(check, ar, idt, t)

    sys.exit(led.verdict())


#: Floor from the real green run, 2026-08-19: 58 checks, nothing optional and
#: no section that can legitimately skip, so the floor IS the count. Set AFTER
#: the run, never before -- a declared-24 floor against a 20-check run is how
#: U8 shipped with the ledger refusing it.
FLOOR = 58

if __name__ == "__main__":
    main()
