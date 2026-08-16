r"""The reference-list decoder, its framing controls, and the sound-chain
oracle.

    python toolkit/mapdata/test_mdlrefs.py           # synthetics + anchors +
                                                     #   a strided corpus pass
    python toolkit/mapdata/test_mdlrefs.py --all     # every reference chunk
                                                     #   on every head row

THE HEADLINE IS THE RECORD RULE, and the control is a rival that must FAIL.
The client's scanner (`0x00908260`) ends a record at the first zero u16 word;
the obvious rival reading -- fixed 6-byte records `{id0, id1, pad}` -- closes
on every FA6/FA8/FAD chunk in the archive, because every record there happens
to be 2 wchars. What separates the framings is FA5's NULL SLOTS (a record
that is ONLY the terminator): the rival must fail exactly on the chunks that
carry one, in both directions -- a rival that fails somewhere else, or a
terminator rule that ever disagrees with it on a null-free chunk, is a
different bug. The synthetic section builds the null-slot payload from its
own byte literals so the discrimination is tested even if a sample carries
no nulls (the models arc's `test_modelexport.py` lesson).

CLOSURE IS OUR ASSERTION, NOT THE CLIENT'S: the per-list reader
(`0x00794B70`) copies exactly the bytes the records consumed and never
compares its cursor to the chunk end, and a malformed record makes the
client load an EMPTY list silently (error path `0x00794C27`, no assert).
So every green decode below is a check the artifact could have refused.

THE SOUND-CHAIN ORACLE re-runs the study's FA6 -> ffna type-8 -> MPEG
identification through the committed module: every FA6 record of the three
anchor files resolves to an ffna type-8 sound descriptor, and every entry of
those descriptors' own chunk-0x1 dependency lists lands on bytes whose first
four decode as a valid MPEG-1 Layer III frame header (field values only,
nothing copied). The study measured 231/231; the run pins the exact count.

Anchors: 116228 (hatcher shell: FA6 30 records, FA8 15, first link 15018),
116366 (worm: FA5 5, FA6 16), 116703 (hatcher body: FA5 3, no FA6/FA8),
15018 (the shell's first link, itself FA6+FA8-carrying).
"""

import argparse
import os
import struct
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.dirname(HERE))
from archive import Archive, ffna_chunks, ffna_type, \
    file_id_table  # noqa: E402
from mapchunks import dependency_pair  # noqa: E402
import mdlrefs  # noqa: E402
from mdlrefs import (RefList, Undecodable, decode_records,  # noqa: E402
                     record_file_id, record_text, ref_lists, type8_deps,
                     mpeg_frame_header, REF_CHUNKS, TEXTURE_CHUNK,
                     SOUND_CHUNK, LINK_CHUNK, SOUND_FFNA_TYPE,
                     TYPE8_DEP_CHUNK)
import checks  # noqa: E402
import vaultpath  # noqa: E402

HEAD_FLAGS = 515                 # "addressable model-file head" (unitmodels §2.1)
STRIDE = 53                      # default sample; prime, ~405 of 21,421 heads

ANCHOR_SHELL = 116228            # FA6(30) + FA1 + FA8(15), no FA0
ANCHOR_WORM = 116366             # FA0 + FA1 + FA5(5) + FA6(16)
ANCHOR_BODY = 116703             # FA0 + FA5(3) -- no FA6/FA8
ANCHOR_LINK = 15018              # the shell's first FA8 link
SHELL_FA6_N, SHELL_FA8_N = 30, 15
WORM_FA5_N, WORM_FA6_N = 5, 16
BODY_FA5_N = 3

#: --all literals, MEASURED 2026-08-16 through this module over every
#: flags=515 head row of the study archive (the U3 full-population sweep,
#: vault/research/mdlrefs/2026-08-16-u3/; 30,722 chunks, zero decode
#: failures). The FA6-first figure reproduces the recon's independent
#: prefix sweep exactly (388); FA5's count equals the FA0-first population
#: (20,661) -- every geometry-bearing head carries a texture list.
ALL_HEADS = 21421
ALL_FA6_FIRST = 388
ALL_CHUNKS = {"FA5": 20661, "FA6": 3734, "FA8": 252, "FAD": 6069, "FAE": 6}
ALL_FA5_NULL_CHUNKS = 5393       # FA5 chunks carrying >= 1 null slot
ALL_FA5_NULL_SLOTS = 11894       # total null slots archive-wide
ALL_FA8_RECORDS = 2467           # FA8 records archive-wide (252 chunks,
                                 # 394 distinct targets, all FA0-less)

#: The sound-chain oracle's pinned count over the three FA6 anchors
#: (distinct type-8 descriptors' chunk-0x1 entries, all MPEG-1 Layer III).
ORACLE_MPEG = 231


# ---------------------------------------------------------------------------
# Section 0 fixtures: a builder with ITS OWN byte literals. A record is its
# words plus an explicit two-byte terminator; the count is a u32. If
# mdlrefs.decode_records drifts from this arithmetic, the synthetics go red.
# ---------------------------------------------------------------------------

def synth_list(*records):
    out = bytearray(struct.pack("<I", len(records)))
    for rec in records:
        for w in rec:
            out += struct.pack("<H", w)
        out += b"\x00\x00"
    return bytes(out)


def rival_fixed6(payload):
    """The rival framing: u32 count then count * {u16, u16, u16 pad == 0}.

    Implemented HERE, from its own arithmetic, so the module never carries
    the wrong rule even as dead code.
    """
    if len(payload) < 4:
        return None
    n, = struct.unpack_from("<I", payload, 0)
    if 4 + 6 * n != len(payload):
        return None
    out = []
    for i in range(n):
        id0, id1, pad = struct.unpack_from("<HHH", payload, 4 + 6 * i)
        if pad != 0:
            return None
        out.append((id0, id1))
    return out


def section0(check):
    print("\n== section 0: synthetics (no vault) ==")

    check(decode_records(synth_list()) == [],
          "an empty list (count 0, 4 bytes) decodes to no records")

    # known ids round-trip through the dependency-pair formula
    fids = [116228, 15018, 8197]
    pairs = [dependency_pair(f) for f in fids]
    pay = synth_list(*pairs)
    rl = RefList.decode(pay)
    check(rl.file_ids() == fids,
          "2-wchar records decode to file ids via the dependency-pair "
          "formula, round-tripping dependency_pair")
    check(rival_fixed6(pay) is not None,
          "CONTROL (must pass): the fixed-6 rival also closes on an "
          "all-2-wchar payload -- the corpus shape separates nothing")

    # the null slot: the discriminating shape
    pay = synth_list(pairs[0], (), pairs[1])
    rl = RefList.decode(pay)
    check(rl.file_ids() == [fids[0], None, fids[1]]
          and rl.null_slots() == 1,
          "a null slot decodes as an empty record between two ids")
    check(rival_fixed6(pay) is None,
          "CONTROL (must fail): the fixed-6 rival mis-frames the null-slot "
          "payload -- FA5's nulls are why the terminator rule is the rule")

    # a 1-wchar record: never observed in the archive, decodable by the rule
    pay = synth_list((0x1234,))
    rl = RefList.decode(pay)
    check(rl.records == [(0x1234,)] and rl.file_ids() == [None]
          and record_text(rl.records[0]) == "ሴ",
          "a 1-wchar record decodes under the terminator rule (no file id; "
          "record_text reads it as the pathName wide string)")
    check(rival_fixed6(pay) is None,
          "CONTROL (must fail): the rival cannot frame a 4-byte record")

    # refusals, each at its named gate
    for label, pay, gate in [
        ("under 4 bytes", b"\x01\x00", "G00_count"),
        ("no terminator before the end",
         struct.pack("<IHH", 1, 3, 3), "G01_terminator"),
        ("count overruns the records present",
         struct.pack("<I", 3) + struct.pack("<HHH", 1, 2, 0),
         "G01_terminator"),
        ("a zero byte on the last byte is not a zero word (the scanner "
         "stops at end-1, 0x0090826B)",
         struct.pack("<IH", 1, 3) + b"\x00", "G01_terminator"),
        ("count 0 with trailing bytes", struct.pack("<I", 0) + b"\xAA\xAA",
         "G02_close"),
        ("odd trailing byte", synth_list((5, 6)) + b"\xAA", "G02_close"),
    ]:
        try:
            decode_records(pay)
            check(False, f"refusal: {label}")
        except Undecodable as e:
            check(e.gate == gate, f"refusal: {label} dies at {gate}",
                  f"got {e.gate}")

    check(record_file_id(()) is None and record_file_id((1, 2, 3)) is None,
          "record_file_id is None for null slots and non-2-wchar records")

    # a non-model container is refused before any chunk walk
    try:
        ref_lists(b"ffna\x03" + bytes(16))
        check(False, "ref_lists refuses a non-type-2 container")
    except ValueError:
        check(True, "ref_lists refuses a non-type-2 container")

    # the type-8 hop
    d0, d1 = dependency_pair(192866)
    check(type8_deps(struct.pack("<HHH", d0, d1, 0) * 2) == [192866, 192866],
          "type-8 chunk-1 entries decode count-less at 6 bytes each")
    for label, pay in [("length not a multiple of 6", bytes(8)),
                       ("nonzero terminator word",
                        struct.pack("<HHH", 1, 2, 7))]:
        try:
            type8_deps(pay)
            check(False, f"type-8 refusal: {label}")
        except Undecodable:
            check(True, f"type-8 refusal: {label}")

    # the MPEG-1 Layer III header oracle, on synthetic bytes
    check(mpeg_frame_header(b"\xFF\xFB\x90\x00")
          == {"bitrate_kbps": 128, "samplerate": 44100},
          "a valid MPEG-1 Layer III header parses (128 kbps, 44.1 kHz)")
    for label, b in [("broken sync", b"\xFE\xFB\x90\x00"),
                     ("MPEG-2 version", b"\xFF\xF3\x90\x00"),
                     ("Layer I", b"\xFF\xFF\x90\x00"),
                     ("free-form bitrate", b"\xFF\xFB\x00\x00"),
                     ("bad bitrate index", b"\xFF\xFB\xF0\x00"),
                     ("reserved sample rate", b"\xFF\xFB\x9C\x00"),
                     ("too short", b"\xFF\xFB\x90")]:
        check(mpeg_frame_header(b) is None, f"MPEG oracle refuses {label}")


def section1(check, ar, idt_raw):
    print("\n== section 1: the anchors ==")
    shell = ar.read(ar.row(idt_raw[ANCHOR_SHELL]))
    refs = ref_lists(shell)
    check(set(refs) == {SOUND_CHUNK, LINK_CHUNK},
          "116228 (hatcher shell) carries exactly FA6 and FA8 ref lists")
    fa6, fa8 = refs[SOUND_CHUNK], refs[LINK_CHUNK]
    check(len(fa6) == SHELL_FA6_N and fa6.null_slots() == 0,
          f"shell FA6: {SHELL_FA6_N} records, no null slots",
          f"got {len(fa6)}")
    check(len(fa8) == SHELL_FA8_N and fa8.file_ids()[0] == ANCHOR_LINK,
          f"shell FA8: {SHELL_FA8_N} links, first is {ANCHOR_LINK}",
          f"got {len(fa8)}, first {fa8.file_ids()[:1]}")
    check(all(f in idt_raw for f in fa6.file_ids() + fa8.file_ids()),
          "every shell reference resolves in file_id_table(raw=True) -- "
          "client addressability, not our convenience table")

    worm = ar.read(ar.row(idt_raw[ANCHOR_WORM]))
    refs = ref_lists(worm)
    check(len(refs[TEXTURE_CHUNK]) == WORM_FA5_N
          and len(refs[SOUND_CHUNK]) == WORM_FA6_N,
          f"116366 (worm): FA5 {WORM_FA5_N} + FA6 {WORM_FA6_N} records")

    body = ar.read(ar.row(idt_raw[ANCHOR_BODY]))
    refs = ref_lists(body)
    check(set(refs) == {TEXTURE_CHUNK}
          and len(refs[TEXTURE_CHUNK]) == BODY_FA5_N,
          f"116703 (the 0x0057 body): FA5 only, {BODY_FA5_N} records -- no "
          "sound cues, no links; its FA6-lessness is the composite split")

    via_load = mdlrefs.load(ANCHOR_SHELL, ar)
    check(sorted(via_load) == sorted([SOUND_CHUNK, LINK_CHUNK])
          and via_load[SOUND_CHUNK].records == fa6.records,
          "load(file_id) resolves to the same records as the container path")


def section2(check, led, ar, idt_raw, stride):
    print(f"\n== section 2: corpus, stride {stride} ==")
    t0 = time.time()
    heads = [e.index for e in ar.entries if e.flags == HEAD_FLAGS]
    if stride == 1:
        check(len(heads) == ALL_HEADS,
              f"flags={HEAD_FLAGS} head population is exactly {ALL_HEADS}",
              f"got {len(heads)}")

    sample = heads[::stride]
    per = {cid: {"chunks": 0, "recs": 0, "nulls": 0, "null_chunks": 0,
                 "odd": 0, "unresolved": 0, "rival_fail": 0,
                 "rival_null_agree": 0}
           for cid in REF_CHUNKS}
    fa6_first = 0
    fa8_ids = []
    gates = []
    non_ffna = 0
    for row in sample:
        data = ar.read(ar.row(row))
        if data[:4] != b"ffna":
            non_ffna += 1            # the known row-8316 anomaly's class
            continue
        chunk_list = list(ffna_chunks(data))
        if chunk_list and chunk_list[0][0] == SOUND_CHUNK:
            fa6_first += 1
        for cid, off, size in chunk_list:
            if cid not in REF_CHUNKS:
                continue
            pay = bytes(data[off:off + size])
            P = per[cid]
            try:
                recs = decode_records(pay)
            except Undecodable as e:
                gates.append((row, f"{cid:X}", e.gate))
                continue
            P["chunks"] += 1
            P["recs"] += len(recs)
            nulls = sum(1 for r in recs if not r)
            P["nulls"] += nulls
            P["null_chunks"] += bool(nulls)
            P["odd"] += sum(1 for r in recs if len(r) not in (0, 2))
            for r in recs:
                fid = record_file_id(r)
                if fid is not None and fid not in idt_raw:
                    P["unresolved"] += 1
                if fid is not None and cid == LINK_CHUNK:
                    fa8_ids.append(fid)
            rival_dead = rival_fixed6(pay) is None
            P["rival_fail"] += rival_dead
            P["rival_null_agree"] += (rival_dead == bool(nulls))
    n_chunks = sum(P["chunks"] for P in per.values())
    print(f"  {len(sample)} heads -> " + ", ".join(
        f"{cid:X}:{per[cid]['chunks']}" for cid in REF_CHUNKS)
        + f" ({time.time() - t0:.0f}s)")

    check(n_chunks > 0, "the sample carries reference chunks -- every "
          "aggregate below would pass vacuously otherwise",
          f"{n_chunks} chunks")
    check(not gates,
          f"closure: {n_chunks}/{n_chunks + len(gates)} reference chunks "
          "decode to the exact final byte -- OUR check, the client never "
          "compares cursor to end", f"failures: {gates[:5]}")
    check(sum(P["odd"] for P in per.values()) == 0,
          "every record is 0 or 2 wchars -- a record length the pathName "
          "rule permits but the archive never uses would show here")
    check(sum(P["unresolved"] for P in per.values()) == 0,
          "every 2-wchar record's file id resolves in "
          "file_id_table(raw=True)")
    for cid, name in ((SOUND_CHUNK, "FA6"), (LINK_CHUNK, "FA8"),
                      (0xFAD, "FAD"), (0xFAE, "FAE")):
        P = per[cid]
        if not P["chunks"]:
            led.skip(f"{name} null-slot absence",
                     "no {} chunk in this sample".format(name))
            continue
        check(P["nulls"] == 0,
              f"{name}: no null slots on {P['chunks']} chunks -- nulls are "
              "an FA5-only phenomenon in this archive")
    P5 = per[TEXTURE_CHUNK]
    if stride == 1:
        for name, got, want in (
                ("chunk censuses", {k: per[c]["chunks"] for k, c in
                 (("FA5", TEXTURE_CHUNK), ("FA6", SOUND_CHUNK),
                  ("FA8", LINK_CHUNK), ("FAD", 0xFAD), ("FAE", 0xFAE))},
                 ALL_CHUNKS),
                ("FA6-first population", fa6_first, ALL_FA6_FIRST),
                ("FA5 null-slot chunks", P5["null_chunks"],
                 ALL_FA5_NULL_CHUNKS),
                ("FA5 null slots", P5["nulls"], ALL_FA5_NULL_SLOTS),
                ("FA8 records", len(fa8_ids), ALL_FA8_RECORDS),
                ("non-ffna heads (the row-8316 anomaly)", non_ffna, 1)):
            check(got == want, f"full population: {name} = {want}",
                  f"got {got}")
    check(P5["null_chunks"] > 0,
          "the FA5 control population is non-empty in this sample -- the "
          "rival discrimination below is measured, not vacuous",
          f"{P5['null_chunks']} null-carrying FA5 chunks")
    for cid, name in ((TEXTURE_CHUNK, "FA5"), (SOUND_CHUNK, "FA6"),
                      (LINK_CHUNK, "FA8"), (0xFAD, "FAD"), (0xFAE, "FAE")):
        P = per[cid]
        if not P["chunks"]:
            led.skip(f"{name} rival discrimination",
                     f"no {name} chunk in this sample")
            continue
        # HONESTY NOTE (U3 review, F1): given the record-length law checked
        # above (every record 0 or 2 wchars), rival_dead == bool(nulls) is
        # a THEOREM -- len = 4 + 6(n-k) + 2k, and fixed-6 closes iff k == 0
        # -- so this check cannot fail independently once the length law is
        # green. It stays as a regression tripwire on the arithmetic, but
        # the INDEPENDENT discrimination of the framings is the scanner
        # disassembly (0x00908260) plus the synthetic null-slot fixture in
        # section 0, not this corpus agreement.
        check(P["rival_null_agree"] == P["chunks"],
              f"{name}: rival-vs-null agreement (entailed by the record-"
              f"length law; see comment) ({P['rival_fail']} failures / "
              f"{P['null_chunks']} null chunks of {P['chunks']})")

    # FA8 target classification -- the linked-model claims, widened
    if fa8_ids:
        distinct = sorted(set(fa8_ids))
        bad_type = with_fa0 = without_fa1 = 0
        for fid in distinct:
            t = ar.read(ar.row(idt_raw[fid]))
            if t[:4] != b"ffna" or ffna_type(t) != 2:
                bad_type += 1
                continue
            cids = {c for c, _, _ in ffna_chunks(t)}
            with_fa0 += 0xFA0 in cids
            without_fa1 += 0xFA1 not in cids
        check(bad_type == 0,
              f"all {len(distinct)} distinct FA8 targets are ffna type-2")
        check(with_fa0 == 0,
              f"no FA8 target carries geometry (0xFA0), {len(distinct)} "
              "targets -- the linked model's body arrives elsewhere")
        check(without_fa1 == 0,
              f"every FA8 target carries a skeleton (0xFA1) the loader's "
              "m_seqCount check (0x00794917) needs")
    else:
        led.skip("FA8 target classification", "no FA8 chunk in this sample")


def section3(check, ar, idt_raw):
    print("\n== section 3: the sound-chain oracle ==")
    t0 = time.time()
    type8 = []
    seen = set()
    for anchor in (ANCHOR_SHELL, ANCHOR_WORM, ANCHOR_LINK):
        refs = ref_lists(ar.read(ar.row(idt_raw[anchor])))
        for fid in refs[SOUND_CHUNK].file_ids():
            if fid in seen:
                continue
            seen.add(fid)
            t = ar.read(ar.row(idt_raw[fid]))
            type8.append((fid, t))
    check(all(t[:4] == b"ffna" and ffna_type(t) == SOUND_FFNA_TYPE
              for _, t in type8),
          f"every distinct FA6 target of the three anchors is an ffna "
          f"type-{SOUND_FFNA_TYPE} sound descriptor ({len(type8)} files)")

    mpeg = other = total = 0
    for fid, t in type8:
        for cid, off, size in ffna_chunks(t):
            if cid != TYPE8_DEP_CHUNK:
                continue
            for dep in type8_deps(bytes(t[off:off + size])):
                total += 1
                row = idt_raw.get(dep)
                head = (bytes(ar.read(ar.row(row))[:4])
                        if row is not None else b"")
                if mpeg_frame_header(head):
                    mpeg += 1
                else:
                    other += 1
    check(total == ORACLE_MPEG and mpeg == ORACLE_MPEG,
          f"the descriptors' own {ORACLE_MPEG} chunk-0x1 references ALL "
          "decode as valid MPEG-1 Layer III frame headers -- the study's "
          f"231/231, re-run through the committed module "
          f"({time.time() - t0:.0f}s)",
          f"total {total}, mpeg {mpeg}, other {other}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true",
                    help="every reference chunk on every flags=515 head row "
                         "(slow: full decompression of the head bucket)")
    args = ap.parse_args()

    # Floor from the real green default run, 2026-08-16: 52 checks executed
    # (stride 53, the study archive). The per-family corpus sections that a
    # different sample could legitimately empty declare skips (FAE and FA8
    # absence/rival checks, the 3-check FA8 classification); the mandatory
    # core is 45.
    led = checks.Ledger("model reference-list chunks (FA5/FA6/FA8/FAD/FAE)",
                        floor=45)
    check = checks.adopt(led)

    section0(check)

    dat = os.path.join(
        vaultpath.require_dir("dat_study", why="the reference-list corpus"),
        "Gw.dat")
    ar = Archive(dat)
    idt_raw = file_id_table(ar, raw=True)
    section1(check, ar, idt_raw)
    section2(check, led, ar, idt_raw, stride=1 if args.all else STRIDE)
    section3(check, ar, idt_raw)

    sys.exit(led.verdict())


if __name__ == "__main__":
    main()
